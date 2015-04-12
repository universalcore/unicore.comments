from uuid import UUID

import colander
from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from unicore.comments.service import db, app
from unicore.comments.service.views.base import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.views import pagination
from unicore.comments.service.models import Flag, Comment
from unicore.comments.service.schema import Flag as FlagSchema
from unicore.comments.service.views.filtering import FilterSchema, ALL


schema = FlagSchema()
flag_filters = FilterSchema.from_schema(schema, {
    'comment_uuid': ALL,
    'user_uuid': ALL,
    'app_uuid': ALL,
    'submit_datetime': ALL
})


'''
Flag resource
'''


@app.route('/flags/', methods=['POST'])
@db.in_transaction
@inlineCallbacks
def create_flag(request, connection):
    data = deserialize_or_raise(schema.bind(), request)

    # increment flag count
    query = Comment.__table__ \
        .update() \
        .values(flag_count=Comment.__table__.c.flag_count + 1) \
        .where(Comment.__table__.c.uuid == data['comment_uuid'])
    result = yield connection.execute(query)

    if result.rowcount == 0:
        raise colander.Invalid(
            schema.get('comment_uuid'),
            'Comment with uuid %r does not exist' %
            data['comment_uuid'].hex)

    flag = Flag(connection, data)
    try:
        yield flag.insert()
    except IntegrityError:  # already exists
        # NOTE: IntegrityError rolls back transaction
        request.setResponseCode(200)
    else:
        request.setResponseCode(201)

    returnValue(make_json_response(request, flag.to_dict(), schema=schema))


@app.route('/flags/<comment_uuid>/<user_uuid>/', methods=['GET'])
@inlineCallbacks
def view_flag(request, comment_uuid, user_uuid):
    try:
        comment_uuid = UUID(comment_uuid)
        user_uuid = UUID(user_uuid)
    except ValueError:
        raise NotFound

    try:
        connection = yield app.db_engine.connect()
        flag = yield Flag.get_by_pk(
            connection, comment_uuid=comment_uuid, user_uuid=user_uuid)
    finally:
        yield connection.close()

    if flag is None:
        raise NotFound

    returnValue(make_json_response(request, flag.to_dict(), schema=schema))


@app.route('/flags/<comment_uuid>/<user_uuid>/', methods=['PUT'])
@db.in_transaction
@inlineCallbacks
def update_flag(request, comment_uuid, user_uuid, connection):
    data = deserialize_or_raise(
        schema.bind(comment_uuid=comment_uuid, user_uuid=user_uuid), request)
    flag = Flag(connection, data)
    count = yield flag.update()

    if count == 0:
        raise NotFound

    returnValue(make_json_response(request, flag.to_dict(), schema=schema))


@app.route('/flags/<comment_uuid>/<user_uuid>/', methods=['DELETE'])
@db.in_transaction
@inlineCallbacks
def delete_flag(request, comment_uuid, user_uuid, connection):
    try:
        comment_uuid = UUID(comment_uuid)
        user_uuid = UUID(user_uuid)
    except ValueError:
        raise NotFound

    flag = Flag(
        connection, {'comment_uuid': comment_uuid, 'user_uuid': user_uuid})
    count = yield flag.delete()

    if count == 0:
        raise NotFound

    # decrement flag count
    query = Comment.__table__ \
        .update() \
        .values(flag_count=Comment.__table__.c.flag_count - 1) \
        .where(Comment.__table__.c.uuid == comment_uuid)
    yield connection.execute(query)

    returnValue(make_json_response(request, flag.to_dict(), schema=schema))


'''
Flag collection resource
'''


@app.route('/flags/', methods=['GET'])
@inlineCallbacks
def list_flags(request):
    columns = Flag.__table__.c
    filter_expr = flag_filters.get_filter_expression(request.args, columns)

    query = Flag.__table__ \
        .select() \
        .where(filter_expr) \
        .order_by(columns.submit_datetime.desc())
    query, limit, offset = pagination.paginate(request.args, query)

    try:
        connection = yield app.db_engine.connect()
        result = yield connection.execute(query)
        result = yield result.fetchall()
    finally:
        yield connection.close()

    data = {
        'offset': offset,
        'limit': limit,
        'count': len(result),
        'objects': [schema.serialize(row) for row in result]
    }
    returnValue(make_json_response(request, data))
