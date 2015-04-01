from twisted.internet.defer import inlineCallbacks, returnValue

from unicore.comments.service import db, app
from unicore.comments.service.views import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.models import Comment
from unicore.comments.service.schema import Comment as CommentSchema


schema = CommentSchema()
schema_all = CommentSchema(include_all=True)


@app.route('/comments/', methods=['POST'])
@inlineCallbacks
def create_comment(request):
    data = deserialize_or_raise(schema.bind(), request)

    @inlineCallbacks
    def func(connection):
        comment = Comment(connection, data)
        yield comment.insert()
        resp = make_json_response(
            request, comment.to_dict(), schema=schema_all)
        returnValue(resp)

    resp = yield db.in_transaction(app.db_engine, func)
    request.setResponseCode(201)
    returnValue(resp)


@app.route('/comments/', methods=['GET'])
def view_comment(request):
    return 'hello world'


@app.route('/comments/', methods=['PUT'])
@inlineCallbacks
def update_comment(request):
    pass


@app.route('/comments/', methods=['DELETE'])
@inlineCallbacks
def delete_comment(request):
    pass
