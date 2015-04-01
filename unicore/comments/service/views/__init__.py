import json

import colander

from unicore.comments.service import app


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


def make_json_response(request, data, schema=None):
    request.setHeader('Content-Type', 'application/json')
    if schema:
        data = schema.serialize(data)
    return json.dumps(data)


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
