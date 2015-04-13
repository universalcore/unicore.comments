from uuid import UUID
from itertools import chain

from twisted.internet.defer import inlineCallbacks, returnValue
from werkzeug.exceptions import NotFound
from sqlalchemy.sql import or_

from unicore.comments.service import db, app
from unicore.comments.service.views.base import (
    make_json_response, deserialize_or_raise)
from unicore.comments.service.views import pagination
from unicore.comments.service.models import StreamMetadata
from unicore.comments.service.schema import (
    StreamMetadata as StreamMetadataSchema)
from unicore.comments.service.views.filtering import FilterSchema, ALL


schema = StreamMetadataSchema()
schema_no_uuids = schema.clone()
del schema_no_uuids['app_uuid']
del schema_no_uuids['content_uuid']
streammetadata_filters = FilterSchema.from_schema(schema, {
    'app_uuid': ALL,
    'content_uuid': ALL
})


'''
Stream Metadata resource
'''


@app.route('/streammetadata/<app_uuid>/<content_uuid>/', methods=['GET'])
@inlineCallbacks
def view_streammetadata(request, app_uuid, content_uuid):
    ''' Returns empty metadata if the stream is not in the database.
    '''

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


def get_stream_primary_keys(request):
    filter_data = streammetadata_filters.convert_lists(request.args)
    filter_data = streammetadata_filters.deserialize(filter_data)

    app_uuids = set(filter_data.get('app_uuid_in', []))
    if 'app_uuid' in filter_data:
        app_uuids.add(filter_data['app_uuid'])
    content_uuids = set(filter_data.get('content_uuid_in', []))
    if 'content_uuid' in filter_data:
        content_uuids.add(filter_data['content_uuid'])

    # unbounded set
    if not app_uuids or not content_uuids:
        return None

    # bounded set
    pks = [{'app_uuid': a, 'content_uuid': c}
           for a in app_uuids for c in content_uuids]
    return pks


@inlineCallbacks
def unbounded_list_streammetadata(request):
    columns = StreamMetadata.__table__.c
    filter_expr = streammetadata_filters.get_filter_expression(
        request.args, columns)

    query = StreamMetadata.__table__ \
        .select() \
        .where(filter_expr)
    query, limit, offset = pagination.paginate(request.args, query)

    try:
        connection = yield app.db_engine.connect()
        result = yield connection.execute(query)
        result = yield result.fetchall()
    finally:
        yield connection.close()

    data = {
        'offset': offset,
        'limit': limit,
        'count': len(result),
        'objects': [schema.serialize(row) for row in result]
    }
    returnValue(make_json_response(request, data))


@inlineCallbacks
def bounded_list_streammetadata(request, primary_keys):
    filter_expr = [StreamMetadata._pk_expression(pk) for pk in primary_keys]
    filter_expr = or_(*filter_expr)

    query = StreamMetadata.__table__ \
        .select() \
        .where(filter_expr)

    try:
        connection = yield app.db_engine.connect()
        result = yield connection.execute(query)
        result = yield result.fetchall()
    finally:
        connection.close()

    all_pks_set = set(
        [(pk['app_uuid'], pk['content_uuid']) for pk in primary_keys])
    existing_pks_set = set(
        [(d['app_uuid'], d['content_uuid']) for d in result])
    non_db_objects = []
    for pk in all_pks_set - existing_pks_set:
        non_db_objects.append({
            'app_uuid': pk[0],
            'content_uuid': pk[1]})

    data = {
        'count': len(all_pks_set),
        'objects': [schema.serialize(row)
                    for row in chain(result, non_db_objects)]
    }
    returnValue(make_json_response(request, data))


@app.route('/streammetadata/', methods=['GET'])
@inlineCallbacks
def list_streammetadata(request):
    primary_keys = get_stream_primary_keys(request)
    if primary_keys is None:
        resp = yield unbounded_list_streammetadata(request)
    else:
        resp = yield bounded_list_streammetadata(request, primary_keys)
    returnValue(resp)


'''@app.route('/streammetadata/', methods=['PUT'])
@db.in_transaction
@inlineCallbacks
def update_list_streammetadata(request, connection):
    data = deserialize_or_raise(schema_no_uuids.bind(), request)
    columns = StreamMetadata.__table__.c
    filter_expr = streammetadata_filters.get_filter_expression(
        request.args, columns)

    query = StreamMetadata.__table__ \
        .update() \
        .where(filter_expr) \
        .values(**data)

    result = yield connection.execute(query)
    if result.rowcount > 0:
        pass'''
