from uuid import UUID

from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound
from sqlalchemy.exc import IntegrityError

from unicore.comments.service import db, app
from unicore.comments.service.views.base import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.models import BannedUser
from unicore.comments.service.schema import BannedUser as BannedUserSchema


banneduser_schema = BannedUserSchema()


'''
Banned Users resource
'''


@app.route('/bannedusers/', methods=['POST'])
@db.in_transaction
@inlineCallbacks
def create_banneduser(request, connection):
    data = deserialize_or_raise(banneduser_schema.bind(), request)
    banneduser = BannedUser(connection, data)
    try:
        yield banneduser.insert()
    except IntegrityError:  # already exists
        request.setResponseCode(200)
    else:
        request.setResponseCode(201)

    returnValue(make_json_response(
        request, banneduser.to_dict(), schema=banneduser_schema))


@app.route('/bannedusers/<user_uuid>/<app_uuid>/', methods=['GET'])
@inlineCallbacks
def get_banneduser(request, user_uuid, app_uuid):
    try:
        user_uuid = UUID(user_uuid)
        app_uuid = UUID(app_uuid)
    except ValueError:
        raise NotFound

    try:
        connection = yield app.db_engine.connect()
        user = yield BannedUser.get_by_pk(
            connection, user_uuid=user_uuid, app_uuid=app_uuid)
    finally:
        connection.close()

    if user is None:
        raise NotFound

    returnValue(make_json_response(
        request, user.to_dict(), schema=banneduser_schema))


@app.route('/bannedusers/<user_uuid>/<app_uuid>/', methods=['DELETE'])
@db.in_transaction
@inlineCallbacks
def delete_banneduser(request, user_uuid, app_uuid, connection):
    try:
        user_uuid = UUID(user_uuid)
        app_uuid = UUID(app_uuid)
    except ValueError:
        raise NotFound

    user = BannedUser(
        connection, {'user_uuid': user_uuid, 'app_uuid': app_uuid})
    count = yield user.delete()

    if count == 0:
        raise NotFound

    returnValue(make_json_response(
        request, user.to_dict(), schema=banneduser_schema))


'''
Banned Users collection resource
'''


@app.route('/bannedusers/<user_uuid>/', methods=['DELETE'])
@db.in_transaction
@inlineCallbacks
def delete_banneduser_all_apps(request, user_uuid, connection):
    try:
        user_uuid = UUID(user_uuid)
    except ValueError:
        raise NotFound

    query = BannedUser.__table__ \
        .delete() \
        .where(BannedUser.__table__.c.user_uuid == user_uuid) \
        .returning(*BannedUser.__table__.c)
    result = yield connection.execute(query)
    result = yield result.fetchall()

    data = {
        'count': len(result),
        'objects': [banneduser_schema.serialize(row) for row in result]
    }
    returnValue(make_json_response(request, data))
