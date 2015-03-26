import json

import falcon

import colander
from wsgiref import simple_server

from unicore.comments.service.schema import Comment as CommentSchema


app = falcon.API()


'''
The views
'''


class Comments(object):

    def on_get(self, request, response):
        # TODO - filter by all the things & offset
        pass

    def on_post(self, request, response):
        data = deserialize_or_raise(CommentSchema(), request)
        # TODO: save the comment
        response.status = 201
        response.body = json.dumps(data)


class Flags(object):

    def on_put(self, request, response, uuid):
        # TODO: increment the flag
        response.body = json.dumps({'uuid': uuid})


app.add_route('/comments/', Comments())
app.add_route('/comments/{uuid}/flag/', Flags())


'''
Error handling stuff
'''


class InvalidJSONError(Exception):
    pass


def deserialize_or_raise(schema, req):
    try:
        if req.get_header('Content-Type') != 'application/json':
            raise ValueError
        data = json.loads(req.stream.read().decode('utf-8'))
        return schema.deserialize(data)

    except (TypeError, ValueError):
        raise InvalidJSONError('Not valid JSON')


def bad_fields(exc, request, response, params):
    raise falcon.HTTPBadRequest('Invalid fields', exc.asdict())


def bad_json(exc, request, response, params):
    raise falcon.HTTPBadRequest('Invalid JSON', unicode(exc))


app.add_error_handler(colander.Invalid, bad_fields)
app.add_error_handler(InvalidJSONError, bad_json)


'''
Config and run server
'''


if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    httpd.serve_forever()
