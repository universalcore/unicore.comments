from uuid import UUID

from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound

from unicore.comments.service import db, app
from unicore.comments.service.views import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.models import Comment
from unicore.comments.service.schema import Comment as CommentSchema


schema = CommentSchema()
schema_all = CommentSchema(include_all=True)


'''
Comment resource
'''


@app.route('/comments/', methods=['POST'])
@db.in_transaction
@inlineCallbacks
def create_comment(request, connection):
    data = deserialize_or_raise(schema.bind(), request)
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

    connection = yield app.db_engine.connect()
    comment = yield Comment.get_by_pk(connection, uuid=uuid)
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
TODO: Comment collection resource
'''
