import json
from datetime import datetime, timedelta
import pytz
import uuid
from unittest import SkipTest

from sqlalchemy import and_
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.expression import exists

from unicore.comments.service.models import (
    Comment, Flag, BannedUser, StreamMetadata)
from unicore.comments.service.tests import ViewTestCase
from unicore.comments.service.tests.test_schema import (
    comment_data, flag_data, banneduser_data, streammetadata_data)
from unicore.comments.service.schema import (
    Comment as CommentSchema, Flag as FlagSchema,
    BannedUser as BannedUserSchema,
    StreamMetadata as StreamMetadataSchema)


class CRUDTests(object):
    base_url = ''
    detail_url = ''
    model_class = None
    instance_data = None
    schema = None
    autogenerate_pk_fields = True

    def without_pk_fields(self, data):
        data = data.copy()
        for column in inspect(self.model_class.__table__).primary_key:
            data.pop(column.name, None)
        return data

    def get_detail_url(self, data):
        return self.detail_url % data

    def queryExists(self, data):
        try:
            expression = self.model_class._pk_expression(data)
        except KeyError:
            expression = [self.model_class.__table__.c[k] == v
                          for k, v in data.iteritems()]
            expression = and_(*expression)

        exists_query = self.model_class.__table__ \
            .select(exists().where(expression))
        result = self.successResultOf(self.connection.execute(exists_query))
        result = self.successResultOf(result.scalar())
        return result

    def assertExists(self, data):
        self.assertTrue(self.queryExists(data))

    def assertNotExists(self, data):
        self.assertFalse(self.queryExists(data))

    def test_create(self):
        if self.autogenerate_pk_fields:
            data = self.without_pk_fields(self.instance_data)
        else:
            data = self.instance_data
        request = self.post(self.base_url, data)

        self.assertEqual(request.code, 201)
        written_data = json.loads(request.getWrittenData())
        self.assertDictContainsSubset(
            self.schema.deserialize(data),
            self.schema.deserialize(written_data))
        self.assertExists(written_data)

        request = self.post(self.base_url, {})

        self.assertEqual(request.code, 400)
        written_data = json.loads(request.getWrittenData())
        self.assertEqual(written_data.get('status'), 'error')

    def test_read(self):
        request = self.get(self.get_detail_url(self.instance_data))
        self.assertEqual(request.code, 404)

        obj = self.model_class(self.connection, self.instance_data)
        self.successResultOf(obj.insert())
        request = self.get(self.get_detail_url(self.instance_data))

        self.assertEqual(request.code, 200)
        self.assertEqual(
            self.schema.deserialize(self.instance_data),
            self.schema.deserialize(json.loads(request.getWrittenData())))

    def test_update(self):
        obj = self.model_class(self.connection, self.instance_data)
        self.successResultOf(obj.insert())

        data = self.instance_data.copy()
        data['submit_datetime'] = datetime.now(pytz.utc).isoformat()
        request = self.put(self.get_detail_url(data), data)

        self.assertEqual(request.code, 200)
        self.assertEqual(
            self.schema.deserialize(data),
            self.schema.deserialize(json.loads(request.getWrittenData())))

    def test_delete(self):
        request = self.delete(self.get_detail_url(self.instance_data))
        self.assertEqual(request.code, 404)

        obj = self.model_class(self.connection, self.instance_data)
        self.successResultOf(obj.insert())
        request = self.delete(self.get_detail_url(self.instance_data))

        self.assertEqual(request.code, 200)
        written_data = json.loads(request.getWrittenData())
        self.assertEqual(
            self.schema.deserialize(self.instance_data),
            self.schema.deserialize(written_data))
        self.assertNotExists(written_data)


class ListTests(object):

    def test_pagination(self):
        data = self.get_json(self.base_url)
        self.assertEqual(data['limit'], 50)
        self.assertEqual(data['offset'], 0)
        self.assertEqual(data['count'], 10)
        self.assertEqual(len(data['objects']), 10)

        data = self.get_json('%s?limit=10&offset=3' % self.base_url)
        self.assertEqual(data['limit'], 10)
        self.assertEqual(data['offset'], 3)
        self.assertEqual(data['count'], 7)
        self.assertEqual(len(data['objects']), 7)

        data = self.get_json('%s?limit=5&offset=2' % self.base_url)
        self.assertEqual(data['limit'], 5)
        self.assertEqual(data['offset'], 2)
        self.assertEqual(data['count'], 5)
        self.assertEqual(len(data['objects']), 5)

    def test_ordering(self):
        sorted_by_date = sorted(
            self.objects, key=lambda o: o.get('submit_datetime'),
            reverse=True)
        data = self.get_json(self.base_url)
        self.assertEqual(
            map(lambda o: o['submit_datetime'], data['objects']),
            map(lambda o: o.get('submit_datetime').isoformat(), sorted_by_date)
        )


class CommentCRUDTestCase(ViewTestCase, CRUDTests):
    base_url = '/comments/'
    detail_url = '/comments/%(uuid)s/'
    model_class = Comment
    instance_data = comment_data
    schema = CommentSchema().bind()

    def test_create(self):
        super(CommentCRUDTestCase, self).test_create()

        comment_data = self.without_pk_fields(self.instance_data)

        # check that banned user comment is rejected
        user_data = {
            'user_uuid': comment_data['user_uuid'],
            'app_uuid': comment_data['app_uuid']
        }
        user = BannedUser(self.connection, user_data)
        self.successResultOf(user.insert())

        request = self.post(self.base_url, comment_data)
        self.assertEqual(request.code, 403)

        user.set('app_uuid', None)
        self.successResultOf(user.update())

        request = self.post(self.base_url, comment_data)
        self.assertEqual(request.code, 403)


class FlagCRUDTestCase(ViewTestCase, CRUDTests):
    base_url = '/flags/'
    detail_url = '/flags/%(comment_uuid)s/%(user_uuid)s/'
    model_class = Flag
    instance_data = flag_data
    schema = FlagSchema().bind()
    autogenerate_pk_fields = False

    def setUp(self):
        super(FlagCRUDTestCase, self).setUp()
        self.comment = Comment(self.connection, comment_data)
        self.successResultOf(self.comment.insert())

    def test_create(self):
        super(FlagCRUDTestCase, self).test_create()

        # check that flag count has been incremented
        comment = self.successResultOf(Comment.get_by_pk(
            self.connection, uuid=self.comment.get('uuid')))
        self.assertEqual(comment.get('flag_count'), 1)

        # check that inserting duplicate fails
        request = self.post(self.base_url, self.instance_data)
        comment = self.successResultOf(Comment.get_by_pk(
            self.connection, uuid=self.comment.get('uuid')))
        self.assertEqual(request.code, 200)
        self.assertEqual(comment.get('flag_count'), 1)

        # check that inserting flag without existing comment fails
        data = self.instance_data.copy()
        data['comment_uuid'] = uuid.uuid4().hex  # non-existent comment uuid
        request = self.post(self.base_url, data)
        self.assertEqual(request.code, 400)

    def test_delete(self):
        super(FlagCRUDTestCase, self).test_delete()

        # check that flag count has been decremented
        comment = self.successResultOf(Comment.get_by_pk(
            self.connection, uuid=self.comment.get('uuid')))
        self.assertEqual(comment.get('flag_count'), -1)


class BannedUserCRUDTestCase(ViewTestCase, CRUDTests):
    base_url = '/bannedusers/'
    detail_url = '/bannedusers/%(user_uuid)s/%(app_uuid)s/'
    model_class = BannedUser
    instance_data = banneduser_data
    schema = BannedUserSchema().bind()
    autogenerate_pk_fields = False

    def test_update(self):
        raise SkipTest('No update endpoint implemented')


class StreamMetadataCRUDTestCase(ViewTestCase, CRUDTests):
    base_url = '/streammetadata/'
    detail_url = '/streammetadata/%(app_uuid)s/%(content_uuid)s/'
    model_class = StreamMetadata
    instance_data = streammetadata_data
    schema = StreamMetadataSchema().bind()

    def test_create(self):
        raise SkipTest('No create endpoint implemented')

    def test_delete(self):
        raise SkipTest('No delete endpoint implemented')

    def test_read(self):
        request = self.get(self.get_detail_url(self.instance_data))
        self.assertEqual(request.code, 200)
        self.assertEqual(json.loads(request.getWrittenData())['metadata'], {})

        obj = self.model_class(self.connection, self.instance_data)
        self.successResultOf(obj.insert())
        request = self.get(self.get_detail_url(self.instance_data))

        self.assertEqual(request.code, 200)
        self.assertEqual(
            self.schema.deserialize(self.instance_data),
            self.schema.deserialize(json.loads(request.getWrittenData())))

    def test_update(self):
        data = self.instance_data.copy()
        request = self.put(self.get_detail_url(data), data)

        self.assertEqual(request.code, 200)
        self.assertEqual(
            self.schema.deserialize(data),
            self.schema.deserialize(json.loads(request.getWrittenData())))

        data['metadata'] = {'something': 'else'}
        request = self.put(self.get_detail_url(data), data)

        self.assertEqual(request.code, 200)
        self.assertEqual(
            self.schema.deserialize(data),
            self.schema.deserialize(json.loads(request.getWrittenData())))


class CommentListTestCase(ViewTestCase, ListTests):
    base_url = '/comments/'

    def setUp(self):
        super(CommentListTestCase, self).setUp()
        data = comment_data.copy()
        del data['uuid']
        self.objects = []
        for i in range(10):
            data['submit_datetime'] = (
                datetime.now(pytz.utc) + timedelta(hours=i))
            obj = Comment(self.connection, data)
            self.successResultOf(obj.insert())
            self.objects.append(obj)

    def test_after(self):
        objects_sorted = sorted(self.objects, key=lambda o: o.get('uuid').hex)
        dt = datetime.now(pytz.utc)
        # fix submit_datetime
        for obj in self.objects:
            obj.set('submit_datetime', dt)
            self.successResultOf(obj.update())
        after_obj = objects_sorted[3]
        data = self.get_json('/comments/?after=%s' % after_obj.get('uuid'))

        self.assertEqual(
            [o['uuid'] for o in data['objects']],
            [o.get('uuid').hex for o in objects_sorted[4:]])

    def test_metadata(self):
        app_uuid = self.objects[0].get('app_uuid').hex
        content_uuid = self.objects[0].get('content_uuid').hex

        for url in ('/comments/',
                    '/comments/?app_uuid=%s&content_uuid=%s' % (
                        app_uuid, content_uuid),
                    '/comments/?app_uuid=%s&content_uuid_in=%s,%s' % (
                        app_uuid, content_uuid, uuid.uuid4().hex)):
            data = self.get_json(url)
            self.assertIn('metadata', data)
            self.assertEqual(data['metadata'], {})

        metadata = StreamMetadata(self.connection, streammetadata_data)
        self.successResultOf(metadata.insert())

        data = self.get_json('/comments/?app_uuid=%s&content_uuid=%s' % (
            app_uuid, content_uuid))
        self.assertIn('metadata', data)
        self.assertEqual(data['metadata'], metadata.get('metadata'))


class FlagListTestCase(ViewTestCase, ListTests):
    base_url = '/flags/'

    def setUp(self):
        super(FlagListTestCase, self).setUp()
        self.comment = Comment(self.connection, comment_data)
        self.successResultOf(self.comment.insert())

        data = flag_data.copy()
        data['comment_uuid'] = self.comment.get('uuid')
        self.objects = []
        for i in range(10):
            data['submit_datetime'] = (
                datetime.now(pytz.utc) + timedelta(hours=i))
            data['user_uuid'] = uuid.uuid4().hex
            obj = Flag(self.connection, data)
            self.successResultOf(obj.insert())
            self.objects.append(obj)


class BannedUserListTestCase(ViewTestCase):

    def setUp(self):
        super(BannedUserListTestCase, self).setUp()

        data = banneduser_data.copy()
        self.objects = []
        for i in range(10):
            data['app_uuid'] = uuid.uuid4().hex if i != 0 else None
            user = BannedUser(self.connection, data)
            self.successResultOf(user.insert())
            self.objects.append(user)

    def test_delete_for_all_apps(self):
        # insert a user that won't be deleted
        data = banneduser_data.copy()
        data['user_uuid'] = uuid.uuid4().hex
        user = BannedUser(self.connection, data)
        self.successResultOf(user.insert())

        schema = BannedUserSchema()
        serialized_data = {
            'count': 10,
            'objects': [schema.serialize(o.to_dict()) for o in self.objects]
        }

        request = self.delete(
            '/bannedusers/%(user_uuid)s/' % banneduser_data)
        response_data = json.loads(request.getWrittenData())
        count = self.successResultOf(
            self.connection.execute(BannedUser.__table__.count()))
        count = self.successResultOf(count.scalar())

        self.assertEqual(response_data, serialized_data)
        self.assertEqual(count, 1)


class StreamMetadataListTestCase(ViewTestCase, ListTests):
    base_url = '/streammetadata/'

    def setUp(self):
        super(StreamMetadataListTestCase, self).setUp()

        data = streammetadata_data
        self.objects = []
        for i in range(5):
            data['content_uuid'] = uuid.uuid4().hex
            metadata = StreamMetadata(self.connection, data)
            self.successResultOf(metadata.insert())
            self.objects.append(metadata)

        for i in range(5):
            data['app_uuid'] = uuid.uuid4().hex
            metadata = StreamMetadata(self.connection, data)
            self.successResultOf(metadata.insert())
            self.objects.append(metadata)

    def test_ordering(self):
        raise SkipTest('No ordering')

    def test_view_bounded_list(self):
        content_uuid_known = self.objects[0].get('content_uuid').hex
        content_uuid_unknown = uuid.uuid4().hex
        app_uuid_known = self.objects[0].get('app_uuid').hex
        schema = StreamMetadataSchema()

        # only objects in db
        data = self.get_json('%s?content_uuid=%s&app_uuid=%s' % (
            self.base_url, content_uuid_known, app_uuid_known))
        self.assertEqual(data, {
            'count': 1,
            'objects': [schema.serialize(self.objects[0].to_dict())]})

        # only objects not in db
        data = self.get_json('%s?content_uuid=%s&app_uuid=%s' % (
            self.base_url, content_uuid_unknown, app_uuid_known))
        self.assertEqual(data, {
            'count': 1,
            'objects': [{
                'app_uuid': app_uuid_known,
                'content_uuid': content_uuid_unknown,
                'metadata': {}}]})

        # one in db, one not in db
        data = self.get_json('%s?content_uuid_in=%s,%s&app_uuid=%s' % (
            self.base_url, content_uuid_known, content_uuid_unknown,
            app_uuid_known))
        self.assertEqual(data, {
            'count': 2,
            'objects': [schema.serialize(self.objects[0].to_dict()), {
                'app_uuid': app_uuid_known,
                'content_uuid': content_uuid_unknown,
                'metadata': {}}]
            })

    def test_update_bounded_list(self):
        content_uuid_known = self.objects[0].get('content_uuid').hex
        content_uuid_unknown = uuid.uuid4().hex
        app_uuid_known = self.objects[0].get('app_uuid').hex
        new_metadata = {'metadata': {'X-new': 'data'}}

        # only objects in db
        request = self.put('%s?content_uuid=%s&app_uuid=%s' % (
            self.base_url, content_uuid_known, app_uuid_known), new_metadata)
        self.assertEqual(json.loads(request.getWrittenData()), {
            'updated': 1,
            'count': 1,
            'objects': [new_metadata]})

        # only objects not in db
        request = self.put('%s?content_uuid=%s&app_uuid=%s' % (
            self.base_url, content_uuid_unknown, app_uuid_known), new_metadata)
        self.assertEqual(json.loads(request.getWrittenData()), {
            'updated': 1,
            'count': 1,
            'objects': [new_metadata]})

        # one in db, one not in db
        request = self.put('%s?content_uuid_in=%s,%s&app_uuid=%s' % (
            self.base_url, content_uuid_known, content_uuid_unknown,
            app_uuid_known), new_metadata)
        self.assertEqual(json.loads(request.getWrittenData()), {
            'updated': 2,
            'count': 1,
            'objects': [new_metadata]})

    def test_update_unbounded_list(self):
        new_metadata = {'metadata': {'X-new': 'data'}}
        request = self.put(self.base_url, new_metadata)
        self.assertEqual(json.loads(request.getWrittenData()), {
            'updated': 10,
            'count': 1,
            'objects': [new_metadata]})
