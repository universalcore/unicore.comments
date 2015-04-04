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
@inlineCallbacks
def create_comment(request):
    data = deserialize_or_raise(schema.bind(), request)

    @inlineCallbacks
    def func(connection):
        comment = Comment(connection, data)
        yield comment.insert()
        returnValue(make_json_response(
            request, comment.to_dict(), schema=schema_all))

    resp = yield db.in_transaction(app.db_engine, func)
    request.setResponseCode(201)
    returnValue(resp)


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
@inlineCallbacks
def update_comment(request, uuid):
    data = deserialize_or_raise(schema.bind(comment_uuid=uuid), request)

    @inlineCallbacks
    def func(connection):
        comment = Comment(connection, data)
        count = yield comment.update()

        if count == 0:
            raise NotFound

        returnValue(make_json_response(
            request, comment.to_dict(), schema=schema_all))

    resp = yield db.in_transaction(app.db_engine, func)
    returnValue(resp)


@app.route('/comments/<uuid>/', methods=['DELETE'])
@inlineCallbacks
def delete_comment(request, uuid):
    try:
        uuid = UUID(uuid)
    except ValueError:
        raise NotFound

    @inlineCallbacks
    def func(connection):
        comment = Comment(connection, {'uuid': uuid})
        count = yield comment.delete()

        if count == 0:
            raise NotFound

        returnValue(make_json_response(
            request, comment.to_dict(), schema=schema_all))

    resp = yield db.in_transaction(app.db_engine, func)
    returnValue(resp)


'''
TODO: Comment collection resource
'''
