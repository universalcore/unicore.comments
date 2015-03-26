from bottle import Bottle, run, request, HTTPError

import colander

from unicore.comment.service.schema import Comment as CommentSchema


app = Bottle()


'''
The views
'''


@app.post('/comments/')
def create_comment():
    data = deserialize_or_raise(CommentSchema, request)
    # TODO: save the comment
    return data


@app.get('/comments/')
def list_comments():
    # TODO - filter by all the things & offset
    pass


@app.put('/comments/<uuid:re:[a-z0-9]{32}>/flag/')
def flag_comment(uuid):
    # TODO: increment the flag
    # Bottle automatically converts this to JSON
    return {'uuid': uuid}


'''
Error handling stuff
'''


def deserialize_or_raise(schema, req):
    try:
        data = request.json
        if request.json is None:
            raise ValueError
        return schema.deserialize(data)

    except colander.Invalid as e:
        raise HTTPError(exception=e)

    except (TypeError, ValueError):
        raise HTTPError(exception='Not valid JSON')


@app.error(400)
def bad_request(error):
    exc = error.exception
    error_dict = {'status': 'error'}

    if isinstance(exc, colander.Invalid):
        error_dict['error_dict'] = exc.asdict()
    else:
        error_dict['error_message'] = unicode(exc)
    # Bottle automatically converts this to JSON
    return error_dict


'''
Config and run server
'''


if __name__ == '__main__':
    run(app, host='localhost', port=8080, debug=True)
