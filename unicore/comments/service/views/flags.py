from uuid import UUID

import colander
from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from unicore.comments.service import db, app
from unicore.comments.service.views import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.models import Flag, Comment
from unicore.comments.service.schema import Flag as FlagSchema


schema = FlagSchema()


'''
Flag resource
'''


@app.route('/flags/', methods=['POST'])
@inlineCallbacks
def create_flag(request):
    data = deserialize_or_raise(schema.bind(), request)

    @inlineCallbacks
    def func(connection):
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
        except IntegrityError:
            raise colander.Invalid(
                schema.get('user_uuid'),
                'Flag for comment %r and user %r already exists' %
                (data['comment_uuid'].hex, data['user_uuid'].hex))

        returnValue(make_json_response(
            request, flag.to_dict(), schema=schema))

    resp = yield db.in_transaction(app.db_engine, func)
    request.setResponseCode(201)
    returnValue(resp)


@app.route('/flags/<comment_uuid>/<user_uuid>/', methods=['GET'])
@inlineCallbacks
def view_flag(request, comment_uuid, user_uuid):
    try:
        comment_uuid = UUID(comment_uuid)
        user_uuid = UUID(user_uuid)
    except ValueError:
        raise NotFound

    connection = yield app.db_engine.connect()
    flag = yield Flag.get_by_pk(
        connection, comment_uuid=comment_uuid, user_uuid=user_uuid)
    yield connection.close()

    if flag is None:
        raise NotFound

    returnValue(make_json_response(request, flag.to_dict(), schema=schema))


@app.route('/flags/<comment_uuid>/<user_uuid>/', methods=['PUT'])
@inlineCallbacks
def update_flag(request, comment_uuid, user_uuid):
    data = deserialize_or_raise(
        schema.bind(comment_uuid=comment_uuid, user_uuid=user_uuid), request)

    @inlineCallbacks
    def func(connection):
        flag = Flag(connection, data)
        count = yield flag.update()

        if count == 0:
            raise NotFound

        returnValue(make_json_response(request, flag.to_dict(), schema=schema))

    resp = yield db.in_transaction(app.db_engine, func)
    returnValue(resp)


@app.route('/flags/<comment_uuid>/<user_uuid>/', methods=['DELETE'])
@inlineCallbacks
def delete_flag(request, comment_uuid, user_uuid):
    try:
        comment_uuid = UUID(comment_uuid)
        user_uuid = UUID(user_uuid)
    except ValueError:
        raise NotFound

    @inlineCallbacks
    def func(connection):
        flag = Flag(
            connection, {'comment_uuid': comment_uuid, 'user_uuid': user_uuid})
        count = yield flag.delete()

        if count == 0:
            raise NotFound

        returnValue(make_json_response(request, flag.to_dict(), schema=schema))

    resp = yield db.in_transaction(app.db_engine, func)
    returnValue(resp)


'''
TODO: Flag collection resource
'''
