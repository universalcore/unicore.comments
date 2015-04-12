from uuid import UUID

import colander
from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound

from unicore.comments.service import db, app
from unicore.comments.service.views.base import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.views import pagination
from unicore.comments.service.models import StreamMetadata
from unicore.comments.service.schema import (
    StreamMetadata as StreamMetadataSchema)
from unicore.comments.service.views.filtering import FilterSchema, ALL


schema = StreamMetadataSchema()


'''
Stream Metadata resource
'''


@app.route('/streammetadata/<app_uuid>/<content_uuid>/', methods=['GET'])
@inlineCallbacks
def view_streammetadata(request, app_uuid, content_uuid):
    try:
        app_uuid = UUID(app_uuid)
        content_uuid = UUID(content_uuid)
    except ValueError:
        raise NotFound

    try:
        connection = yield app.db_engine.connect()
        metadata = yield StreamMetadata.get_by_pk(
            connection, app_uuid=app_uuid, content_uuid=content_uuid)
    finally:
        yield connection.close()

    if metadata is None:
        data = {
            'app_uuid': app_uuid,
            'content_uuid': content_uuid}
    else:
        data = metadata.to_dict()

    returnValue(make_json_response(request, data, schema=schema))


@app.route('/streammetadata/<app_uuid>/<content_uuid>/', methods=['PUT'])
@db.in_transaction
@inlineCallbacks
def update_streammetadata(request, app_uuid, content_uuid, connection):
    ''' There is only an update endpoint for stream metadata because,
    conceptually, metadata always exists for a stream, even if empty.
    '''
    data = deserialize_or_raise(
        schema.bind(app_uuid=app_uuid, content_uuid=content_uuid), request)
    metadata = yield StreamMetadata.get_by_pk(
        connection, app_uuid=app_uuid, content_uuid=content_uuid)

    if metadata is None:
        metadata = StreamMetadata(connection, data)
        yield metadata.insert()
    else:
        metadata.set('metadata', data['metadata'])
        yield metadata.update()

    returnValue(make_json_response(request, metadata.to_dict(), schema=schema))


'''
Stream Metadata collection resource
'''
