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


def is_bounded(request):
    return (('app_uuid' in request.args or
             'app_uuid_in' in request.args) and
            ('content_uuid' in request.args or
             'content_uuid_in' in request.args))


def get_stream_primary_keys(request):
    filter_data = streammetadata_filters.convert_lists(request.args)
    filter_data = streammetadata_filters.deserialize(filter_data)

    app_uuids = set(filter_data.get('app_uuid_in', []))
    if 'app_uuid' in filter_data:
        app_uuids.add(filter_data['app_uuid'])
    content_uuids = set(filter_data.get('content_uuid_in', []))
    if 'content_uuid' in filter_data:
        content_uuids.add(filter_data['content_uuid'])

    return set((a, c) for a in app_uuids for c in content_uuids)


@inlineCallbacks
def unbounded_list_streammetadata(request, query):
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
    returnValue(data)


@inlineCallbacks
def bounded_list_streammetadata(request, query):
    try:
        connection = yield app.db_engine.connect()
        result = yield connection.execute(query)
        result = yield result.fetchall()
    finally:
        connection.close()

    existing_pks_set = set((d['app_uuid'], d['content_uuid']) for d in result)
    primary_keys = get_stream_primary_keys(request)
    non_db_objects = [dict(zip(('app_uuid', 'content_uuid'), pk))
                      for pk in primary_keys - existing_pks_set]

    data = {
        'count': len(primary_keys),
        'objects': [schema.serialize(row)
                    for row in chain(result, non_db_objects)]
    }
    returnValue(data)


@app.route('/streammetadata/', methods=['GET'])
@inlineCallbacks
def list_streammetadata(request):
    ''' If the set of streams specified by filters is bounded, i.e.
    UUIDs for both app_uuid and content_uuid are specified, this endpoint
    will return an object for each stream. If it is unbounded, i.e.
    only one or neither of app_uuid and content_uuid is specified, it will
    return only objects that are present in the database.
    '''

    columns = StreamMetadata.__table__.c
    filter_expr = streammetadata_filters.get_filter_expression(
        request.args, columns)

    query = StreamMetadata.__table__ \
        .select() \
        .where(filter_expr)

    view_func = (bounded_list_streammetadata if is_bounded(request)
                 else unbounded_list_streammetadata)
    data = yield view_func(request, query)
    returnValue(make_json_response(request, data))


@inlineCallbacks
def unbounded_update_streammetadata(request, query, data, connection):
    result = yield connection.execute(query)
    data = {
        'updated': result.rowcount,
        'count': 1,
        'objects': [schema_no_uuids.serialize(data)]
    }
    returnValue(data)


@inlineCallbacks
def bounded_update_streammetadata(request, query, data, connection):
    # update and retrieve existing rows
    query = query.returning(StreamMetadata.__table__.c.app_uuid,
                            StreamMetadata.__table__.c.content_uuid)
    result = yield connection.execute(query)
    result = yield result.fetchall()

    existing_pks_set = set((d['app_uuid'], d['content_uuid']) for d in result)
    primary_keys = get_stream_primary_keys(request)
    non_db_objects = [dict(
        chain(zip(('app_uuid', 'content_uuid'), pk), data.iteritems()))
        for pk in primary_keys - existing_pks_set]

    # insert new rows
    if non_db_objects:
        query = StreamMetadata.__table__ \
            .insert() \
            .values(non_db_objects)
        yield connection.execute(query)

    data = {
        'updated': len(primary_keys),
        'count': 1,
        'objects': [schema_no_uuids.serialize(data)]
    }
    returnValue(data)


@app.route('/streammetadata/', methods=['PUT'])
@db.in_transaction
@inlineCallbacks
def update_list_streammetadata(request, connection):
    ''' If the set of streams specified by filters is bounded, i.e.
    UUIDs for both app_uuid and content_uuid are specified, this endpoint
    will update objects present in the database and insert new objects
    as necessary. If it is unbounded, i.e. only one or neither of app_uuid
    and content_uuid is specified, it will update only objects that are
    present in the database.
    '''

    data = deserialize_or_raise(schema_no_uuids.bind(), request)
    columns = StreamMetadata.__table__.c
    filter_expr = streammetadata_filters.get_filter_expression(
        request.args, columns)

    query = StreamMetadata.__table__ \
        .update() \
        .where(filter_expr) \
        .values(**data)

    view_func = (bounded_update_streammetadata if is_bounded(request)
                 else unbounded_update_streammetadata)
    data = yield view_func(request, query, data, connection)
    returnValue(make_json_response(request, data))
