import json

from klein import Klein

import colander

from unicore.comments.service.schema import Comment as CommentSchema


app = Klein()


'''
The views
'''


def make_json_response(request, data):
    request.setHeader('Content-Type', 'application/json')
    return json.dumps(data)


@app.route('/comments/', methods=['POST'])
def create_comment(request):
    data = deserialize_or_raise(CommentSchema(), request)
    # TODO: save the comment
    return make_json_response(request, data)


@app.route('/comments/', methods=['GET'])
def list_comments(request):
    # TODO - filter by all the things & offset
    pass


@app.route('/comments/<uuid>/flag/', methods=['PUT'])
def flag_comment(request, uuid):
    # TODO: increment the flag
    return make_json_response(request, {'uuid': uuid})


'''
Error handling stuff
'''


class InvalidJSONError(Exception):
    pass


def deserialize_or_raise(schema, req):
    try:
        if req.getHeader('Content-Type') != 'application/json':
            raise ValueError
        data = json.loads(req.content.read())
        return schema.deserialize(data)

    except (TypeError, ValueError):
        raise InvalidJSONError('Not valid JSON')


@app.handle_errors(colander.Invalid)
def bad_fields(request, failure):
    request.setResponseCode(400)
    return make_json_response(request, {
        'status': 'error',
        'error_dict': failure.value.asdict()})


@app.handle_errors(InvalidJSONError)
def bad_json(request, failure):
    request.setResponseCode(400)
    return make_json_response(request, {
        'status': 'error',
        'error_message': unicode(failure.value)})


'''
Config and run server
'''


resource = app.resource


if __name__ == '__main__':
    app.run("localhost", 8081)
