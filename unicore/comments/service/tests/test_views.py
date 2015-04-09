import json
from datetime import datetime
import pytz
import uuid

from sqlalchemy.inspection import inspect
from sqlalchemy.sql.expression import exists
from klein.test.test_resource import requestMock, _render

from unicore.comments.service import app, resource
from unicore.comments.service.tests import BaseTestCase
from unicore.comments.service.models import Comment, Flag
from unicore.comments.service.tests.test_schema import comment_data, flag_data
from unicore.comments.service.schema import (
    Comment as CommentSchema, Flag as FlagSchema)
from unicore.comments.service.views import comments, flags  # noqa


class ViewTestCase(BaseTestCase):

    def setUp(self):
        super(ViewTestCase, self).setUp()
        app.db_engine = self.engine
        app.config = self.config

    def request(self, method, path, body=None, headers=None):
        if headers is None:
            headers = {}
        for name in headers.keys():
            if not isinstance(headers[name], (tuple, list)):
                headers[name] = [headers[name]]

        if isinstance(body, dict):
            body = json.dumps(body)
            headers['Content-Type'] = ['application/json']

        request = requestMock(path, method, body=body, headers=headers)
        self.successResultOf(_render(resource, request))
        return request

    def get(self, path, headers=None):
        return self.request('GET', path, headers=headers)

    def post(self, path, body=None, headers=None):
        return self.request('POST', path, body=body, headers=headers)

    def put(self, path, body=None, headers=None):
        return self.request('PUT', path, body=body, headers=headers)

    def delete(self, path, headers=None):
        return self.request('DELETE', path, headers=headers)

    def tearDown(self):
        super(ViewTestCase, self).tearDown()
        del app.db_engine
        del app.config


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
        exists_query = self.model_class.__table__ \
            .select(
                exists().where(self.model_class._pk_expression(data))
            )
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


class CommentCRUDTestCase(ViewTestCase, CRUDTests):
    base_url = '/comments/'
    detail_url = '/comments/%(uuid)s/'
    model_class = Comment
    instance_data = comment_data
    schema = CommentSchema().bind()


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
        self.assertEqual(request.code, 400)

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
