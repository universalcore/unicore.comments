from uuid import uuid4, UUID
from datetime import datetime, timedelta
import pytz
from unittest import TestCase
from urllib import urlencode

import colander
import mock

from unicore.comments.service.tests import requestMock
from unicore.comments.service.views.filtering import (
    FilterSchema, ALL, DelimitedSequenceSchema, comment_filters)
from unicore.comments.service.schema import UUIDType
from unicore.comments.service.models import Comment


mock_validator_string = mock.Mock(wraps=colander.OneOf(['foo', 'bar']))
mock_validator_integer = mock.Mock(wraps=colander.OneOf([1, 2, 3]))


class TestFilters(FilterSchema):
    string = colander.SchemaNode(
        colander.String(),
        validator=mock_validator_string)
    integer = colander.SchemaNode(
        colander.Integer(),
        validator=mock_validator_integer)
    datetime = colander.SchemaNode(colander.DateTime())
    uuid = colander.SchemaNode(UUIDType())
    boolean = colander.SchemaNode(colander.Boolean())


default_spec = {
    'string': ALL,
    'integer': ALL,
    'datetime': ALL,
    'uuid': ALL,
    'boolean': ALL
}


class FilterTestCase(TestCase):

    def test_filter_generation(self):
        filters = TestFilters(filter_spec=default_spec)
        all_filters = {
            'string', 'string_like', 'string_in',
            'integer', 'integer_in', 'integer_gt', 'integer_gte',
            'integer_lt', 'integer_lte',
            'datetime', 'datetime_in', 'datetime_gt', 'datetime_gte',
            'datetime_lt', 'datetime_lte',
            'uuid', 'uuid_in',
            'boolean'}

        self.assertEqual(all_filters, set(n.name for n in filters))
        for node in filters:
            self.assertEqual(node.missing, colander.drop)
            self.assertTrue(getattr(node, 'filter_type', None))
            if node.filter_type == 'in':
                self.assertIsInstance(node, DelimitedSequenceSchema)
            else:
                self.assertNotIsInstance(node, DelimitedSequenceSchema)
        self.assertEqual(
            getattr(filters.get('string_in').children[0], 'validator', None),
            mock_validator_string)

        no_exact_match = {
            'string': {'like', 'in'},
            'integer': {'in', 'range'},
            'datetime': {'in', 'range'},
            'uuid': {'in'},
            'boolean': {},
        }
        filters = TestFilters(filter_spec=no_exact_match)

        self.assertEqual(
            all_filters - {'string', 'integer', 'datetime', 'uuid', 'boolean'},
            set(n.name for n in filters))

    def test_deserializing(self):
        filters = TestFilters(filter_spec=default_spec)
        uuid_hex = uuid4().hex
        dt = datetime.now(pytz.utc)
        query = {
            'integer_in': '1,2,3',
            'string_like': 'foo',
            'uuid': uuid_hex,
            'datetime_lte': dt.isoformat(),
            'boolean': 'false'
        }
        request = requestMock('/?%s' % urlencode(query), 'GET')

        no_lists_query = filters.convert_lists(request.args)
        self.assertEqual(no_lists_query, query)
        self.assertEqual(
            filters.deserialize(no_lists_query), {
                'integer_in': [1, 2, 3],
                'string_like': 'foo',
                'uuid': UUID(uuid_hex),
                'datetime_lte': dt,
                'boolean': False
            })

        no_lists_query['integer_in'] = '4'
        no_lists_query['string'] = 'foobar'
        try:
            filters.deserialize(no_lists_query)
            self.fail('Expected colander.Invalid to be raised')
        except colander.Invalid as e:
            err_dict = e.asdict()
            self.assertEqual(len(err_dict), 2)
            self.assertIn('integer_in.0', err_dict)
            self.assertIn('string', err_dict)
            self.assertIn('one of 1, 2, 3', err_dict['integer_in.0'])

    def test_filter_expressions(self):
        dt = datetime.now(pytz.utc) - timedelta(days=7)
        query = {
            'app_uuid': uuid4().hex,
            'content_title_like': 'foo',
            'content_type_in': 'page,category',
            'flag_count_gt': '0',
            'submit_datetime_gte': dt.isoformat(),
            'is_removed': 'false'
        }
        expression = comment_filters.get_filter_expression(
            query, Comment.__table__.c)
        self.assertEqual(len(expression.clauses), 6)
