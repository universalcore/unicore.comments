from uuid import UUID

from sqlalchemy import or_, and_
from sqlalchemy.sql import exists
from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound, BadRequest, Forbidden

from unicore.comments.service import db, app
from unicore.comments.service.views.base import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.views import pagination
from unicore.comments.service.models import Comment, BannedUser
from unicore.comments.service.schema import Comment as CommentSchema
from unicore.comments.service.views.filtering import FilterSchema, ALL


schema = CommentSchema()
schema_all = CommentSchema(include_all=True)
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


@inlineCallbacks
def is_banned_user(connection, user_uuid, app_uuid):
    cols = BannedUser.__table__.c
    expression = cols.user_uuid == user_uuid
    expression = and_(
        expression,
        or_(cols.app_uuid == app_uuid, cols.app_uuid.is_(None)))

    query = BannedUser.__table__.select(exists().where(expression))
    result = yield connection.execute(query)
    result = yield result.scalar()
    returnValue(bool(result))


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
        raise Forbidden('user is banned from commenting')

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


@app.route('/comments/', methods=['GET'])
@inlineCallbacks
def list_comments(request):
    columns = Comment.__table__.c
    filter_expr = comment_filters.get_filter_expression(request.args, columns)

    # NOTE: orders on submit_datetime, then uuid
    # this is to ensure an absolute ordering
    query = Comment.__table__ \
        .select() \
        .where(filter_expr) \
        .order_by(columns.submit_datetime.desc(),
                  columns.uuid)
    query, limit, offset = pagination.paginate(request.args, query)

    try:
        after_uuid = request.args.get('after', [None])[0]
        after_uuid = UUID(after_uuid) if after_uuid else None
    except ValueError:
        raise BadRequest('after is not a valid hexadecimal UUID')

    try:
        connection = yield app.db_engine.connect()

        if after_uuid:
            last = yield Comment.get_by_pk(connection, uuid=after_uuid)
            if last is not None:
                query = query.where(or_(
                    columns.submit_datetime > last.get('submit_datetime'),
                    and_(
                        columns.submit_datetime == last.get('submit_datetime'),
                        columns.uuid > last.get('uuid'))
                    ))

        result = yield connection.execute(query)
        result = yield result.fetchall()
    finally:
        yield connection.close()

    data = {
        'offset': offset,
        'limit': limit,
        'after': after_uuid.hex if after_uuid else None,
        'count': len(result),
        'objects': [schema_all.serialize(row) for row in result]
    }
    returnValue(make_json_response(request, data))
