from uuid import UUID

import colander
from sqlalchemy import or_, and_
from sqlalchemy.sql import exists, select, func
from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound, Forbidden

from unicore.comments.service import db, app
from unicore.comments.service.views.base import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.views import pagination
from unicore.comments.service.models import Comment, BannedUser, StreamMetadata
from unicore.comments.service.schema import Comment as CommentSchema, UUIDType
from unicore.comments.service.views.filtering import (
    FilterSchema, ALL)
from unicore.comments.service.views.streammetadata import (
    schema as smd_schema, get_stream_primary_keys)


schema = CommentSchema()
schema_all = CommentSchema(include_all=True)
schema_metadata = smd_schema['metadata']
comment_filters = FilterSchema.from_schema(schema_all, {
    'content_uuid': ALL,
    'content_type': ALL,
    'content_title': ALL,
    'user_uuid': ALL,
    'user_name': ALL,
    'app_uuid': ALL,
    'submit_datetime': ALL,
    'is_removed': ALL,
    'moderation_state': ALL,
    'flag_count': ALL
})
extra_filters = FilterSchema(children=[
    colander.SchemaNode(UUIDType(), name='before'),
    colander.SchemaNode(UUIDType(), name='after')])


def is_banned_user(connection, user_uuid, app_uuid):
    cols = BannedUser.__table__.c
    expression = cols.user_uuid == user_uuid
    expression = and_(
        expression,
        or_(cols.app_uuid == app_uuid, cols.app_uuid.is_(None)))

    query = BannedUser.__table__.select(exists().where(expression))
    d = connection.execute(query)
    d.addCallback(lambda result: result.scalar())
    d.addCallback(lambda count: bool(count))
    return d


def get_stream_metadata(connection, request=None, app_uuid=None,
                        content_uuid=None):
    if request:
        primary_key = get_stream_primary_keys(request)
        if not primary_key or len(primary_key) > 1:
            return {}
        app_uuid, content_uuid = primary_key.pop()

    elif not (app_uuid and content_uuid):
        raise ValueError(
            'either request must be provided, or '
            'app_uuid and content_uuid must be provided')

    d = StreamMetadata.get_by_pk(
        connection, app_uuid=app_uuid, content_uuid=content_uuid)
    d.addCallback(lambda o: o.get('metadata') if o else {})
    return d


'''
Comment resource
'''


@app.route('/comments/', methods=['POST'])
@db.in_transaction
@inlineCallbacks
def create_comment(request, connection):
    data = deserialize_or_raise(schema.bind(), request)

    is_banned = yield is_banned_user(
        connection, data['user_uuid'], data['app_uuid'])
    if is_banned:
        raise Forbidden(('USER_BANNED', 'user is banned from commenting'))

    metadata = yield get_stream_metadata(
        connection, app_uuid=data['app_uuid'],
        content_uuid=data['content_uuid'])
    if metadata.get('state', 'open') != 'open':
        raise Forbidden(('STREAM_NOT_OPEN', 'comment stream is not open'))

    comment = Comment(connection, data)
    yield comment.insert()

    request.setResponseCode(201)
    returnValue(make_json_response(
        request, comment.to_dict(), schema=schema_all))


@app.route('/comments/<uuid>/', methods=['GET'])
@inlineCallbacks
def view_comment(request, uuid):
    try:
        uuid = UUID(uuid)
    except ValueError:
        raise NotFound

    try:
        connection = yield app.db_engine.connect()
        comment = yield Comment.get_by_pk(connection, uuid=uuid)
    finally:
        yield connection.close()

    if comment is None:
        raise NotFound

    returnValue(make_json_response(
        request, comment.to_dict(), schema=schema_all))


@app.route('/comments/<uuid>/', methods=['PUT'])
@db.in_transaction
@inlineCallbacks
def update_comment(request, uuid, connection):
    data = deserialize_or_raise(schema.bind(comment_uuid=uuid), request)
    comment = Comment(connection, data)
    count = yield comment.update()

    if count == 0:
        raise NotFound

    returnValue(make_json_response(
        request, comment.to_dict(), schema=schema_all))


@app.route('/comments/<uuid>/', methods=['DELETE'])
@db.in_transaction
@inlineCallbacks
def delete_comment(request, uuid, connection):
    try:
        uuid = UUID(uuid)
    except ValueError:
        raise NotFound

    comment = Comment(connection, {'uuid': uuid})
    count = yield comment.delete()

    if count == 0:
        raise NotFound

    returnValue(make_json_response(
        request, comment.to_dict(), schema=schema_all))


'''
Comment collection resource
'''


def apply_extra_filters(extra, query):
    if not extra:
        return query

    boundary_uuid = extra.get('after', extra.get('before'))
    boundary_dt = select([Comment.__table__.c.submit_datetime]) \
        .where(Comment.__table__.c.uuid == boundary_uuid) \
        .as_scalar()

    cols = query.froms[0].c
    query = query.order_by(None)

    # NOTE: orders on submit_datetime, then uuid
    # this is to ensure an absolute ordering
    if 'after' in extra:
        query = query.where(or_(
            cols.submit_datetime > boundary_dt,
            and_(
                cols.submit_datetime == boundary_dt,
                cols.uuid > boundary_uuid
            ))) \
            .order_by(cols.submit_datetime, cols.uuid)
    else:
        query = query.where(or_(
            cols.submit_datetime < boundary_dt,
            and_(
                cols.submit_datetime == boundary_dt,
                cols.uuid < boundary_uuid
            ))) \
            .order_by(cols.submit_datetime.desc(), cols.uuid.desc())

    return query


@app.route('/comments/', methods=['GET'])
@inlineCallbacks
def list_comments(request):
    columns = Comment.__table__.c
    filter_expr = comment_filters.get_filter_expression(request.args, columns)
    extra = extra_filters.convert_lists(request.args)
    extra = extra_filters.deserialize(extra)

    query_all = Comment.__table__ \
        .select() \
        .where(filter_expr)
    query = query_all \
        .column(func.row_number()
                .over(order_by=(
                    columns.submit_datetime.desc(),
                    columns.uuid.desc()))
                .label('row_number')) \
        .alias() \
        .select() \
        .order_by('row_number')
    query = apply_extra_filters(extra, query)
    query, limit, offset = pagination.paginate(request.args, query)

    try:
        connection = yield app.db_engine.connect()
        result = yield connection.execute(query)
        result = yield result.fetchall()
        total = yield connection.execute(query_all.alias().count())
        total = yield total.scalar()
        metadata = yield get_stream_metadata(connection, request=request)

    finally:
        yield connection.close()

    data = {
        'total': total,
        'count': len(result),
        'objects': [schema_all.serialize(row) for row in
                    sorted(result, key=lambda r: r['row_number'])],
        'metadata': schema_metadata.serialize(metadata),
        'start': result[0]['row_number'] if result else None,
        'end': result[-1]['row_number'] if result else None
    }
    returnValue(make_json_response(request, data))
