import json

import colander
from werkzeug.exceptions import NotFound, BadRequest, Forbidden

from unicore.comments.service import app


def deserialize_or_raise(schema, req):
    try:
        if req.getHeader('Content-Type') != 'application/json':
            raise ValueError
        data = json.loads(req.content.read())
        return schema.deserialize(data)

    except (TypeError, ValueError):
        raise BadRequest(
            ('NOT_JSON', 'Not valid JSON. Is Content-Type '
             'set to application/json?'))


def make_json_response(request, data, schema=None):
    request.setHeader('Content-Type', 'application/json')
    if schema:
        data = schema.serialize(data)
    return json.dumps(data)


def make_error_response(request, status_code, error_code,
                        error_dict=None, error_message=None):
    request.setResponseCode(status_code)
    return make_json_response(request, {
        'status': 'error',
        'error_code': error_code,
        'error_dict': error_dict,
        'error_message': error_message,
    })


@app.handle_errors(colander.Invalid)
def bad_fields(request, failure):
    return make_error_response(
        request, 400, 'BAD_FIELDS', error_dict=failure.value.asdict())


@app.handle_errors(NotFound, BadRequest, Forbidden)
def werkzeug_exception(request, failure):
    e = failure.value
    if isinstance(e.description, (list, tuple)):
        error_code, error_message = e.description
    else:
        error_code = e.name.upper().replace(' ', '_')
        error_message = e.description

    return make_error_response(
        request, e.code, error_code, error_message=error_message)
