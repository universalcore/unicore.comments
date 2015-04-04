import json
from datetime import datetime
import pytz

from sqlalchemy.inspection import inspect
from sqlalchemy.sql.expression import exists
from klein.test.test_resource import requestMock, _render

from unicore.comments.service import app, resource
from unicore.comments.service.tests import BaseTestCase
from unicore.comments.service.models import Comment
from unicore.comments.service.tests.test_schema import comment_data
from unicore.comments.service.schema import Comment as CommentSchema
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

    def without_pk_fields(self, data):
        data = data.copy()
        for column in inspect(self.model_class.__table__).primary_key:
            data.pop(column.name, None)
        return data

    def get_detail_url(self, data):
        return self.detail_url % data

    def _assertExists(self, data, does_exist=True):
        exists_query = self.model_class.__table__ \
            .select(
                exists().where(self.model_class._pk_expression(data))
            )
        result = yield self.connection.execute(exists_query)
        result = yield result.scalar()
        if does_exist:
            self.assertTrue(result)
        else:
            self.assertFalse(result)

    def assertExists(self, data):
        self._assertExists(data)

    def assertNotExists(self, data):
        self._assertExists(data, does_exist=False)

    def test_create(self):
        data = self.without_pk_fields(self.instance_data)
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

        request = self.post(self.base_url, self.instance_data)
        self.assertEqual(request.code, 201)
        request = self.get(self.get_detail_url(self.instance_data))

        self.assertEqual(request.code, 200)
        self.assertEqual(
            self.schema.deserialize(self.instance_data),
            self.schema.deserialize(json.loads(request.getWrittenData())))

    def test_update(self):
        request = self.post(self.base_url, self.instance_data)
        self.assertEqual(request.code, 201)

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

        request = self.post(self.base_url, self.instance_data)
        self.assertEqual(request.code, 201)
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
