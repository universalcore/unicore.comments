import json

from bottle import Bottle, run, request, HTTPError, response

import colander

from unicore.comments.service.schema import Comment as CommentSchema


app = Bottle()


'''
The views
'''


@app.post('/comments/')
def create_comment():
    data = deserialize_or_raise(CommentSchema(), request)
    # TODO: save the comment
    response.status = 201
    return data


@app.get('/comments/')
def list_comments():
    # TODO - filter by all the things & offset
    pass


# NOTE: bottle doesn't have a patch method
@app.post('/comments/<uuid:re:[a-z0-9]{32}>/flag/')
def flag_comment(uuid):
    # TODO: increment the flag
    # Bottle automatically converts this to JSON
    return {'uuid': uuid}


'''
Error handling stuff
'''


def deserialize_or_raise(schema, req):
    try:
        data = req.json
        if req.json is None:
            raise ValueError
        return schema.deserialize(data)

    except colander.Invalid as e:
        raise HTTPError(status=400, exception=e)

    except (TypeError, ValueError):
        raise HTTPError(status=400, exception='Not valid JSON')


@app.error(400)
def bad_request(error):
    exc = error.exception
    error_dict = {'status': 'error'}

    if isinstance(exc, colander.Invalid):
        error_dict['error_dict'] = exc.asdict()
    else:
        error_dict['error_message'] = unicode(exc)

    response.content_type = 'application/json'
    return json.dumps(error_dict)


'''
Config and run server
'''


if __name__ == '__main__':
    run(app, host='localhost', port=8080, debug=True)
