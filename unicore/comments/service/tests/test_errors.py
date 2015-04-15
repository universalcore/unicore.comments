from mock import Mock
import colander
from werkzeug.exceptions import Forbidden, NotFound

from unicore.comments.service import app
from unicore.comments.service.tests import ViewTestCase


class ErrorResponseTestCase(ViewTestCase):

    def setUp(self):
        super(ErrorResponseTestCase, self).setUp()
        self.view_func = Mock(__name__='foo')
        app.route('/error/', methods=['GET'])(self.view_func)

    def test_werkzeug_exception(self):
        # error with code and message
        self.view_func.side_effect = Forbidden(('USER_BANNED', 'foo'))
        error_data = self.get_json('/error/')

        self.assertEqual(error_data, {
            'status': 'error',
            'error_code': 'USER_BANNED',
            'error_message': 'foo',
            'error_dict': None})

        # default error
        self.view_func.side_effect = NotFound
        error_data = self.get_json('/error/')

        self.assertDictContainsSubset({
            'status': 'error',
            'error_code': 'NOT_FOUND',
            'error_dict': None}, error_data)

    def test_colander_invalid(self):
        self.view_func.side_effect = colander.Invalid(
            colander.SchemaNode(colander.String(), name='foo'), 'bar')
        error_data = self.get_json('/error/')

        self.assertEqual(error_data, {
            'status': 'error',
            'error_code': 'BAD_FIELDS',
            'error_message': None,
            'error_dict': {'foo': 'bar'}})
