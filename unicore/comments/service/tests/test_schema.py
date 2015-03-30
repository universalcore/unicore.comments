from datetime import datetime
from unittest import TestCase

import colander

from unicore.comments.service.schema import Comment, Flag
from unicore.comments.service.tests.test_models import (
    comment_data as comment_model_data, flag_data as flag_model_data)


def simple_serialize(data):
    for key in data.keys():
        value = data[key]
        if isinstance(value, bool):
            if value:
                data[key] = 'true'
            else:
                data[key] = 'false'
        elif isinstance(value, int):
            data[key] = str(value)
        elif isinstance(value, datetime):
            data[key] = '%s+00:00' % value.isoformat()
        else:
            data[key] = unicode(value)


comment_data = comment_model_data.copy()
flag_data = flag_model_data.copy()
simple_serialize(comment_data)
simple_serialize(flag_data)


class CommentTestCase(TestCase):
    maxDiff = None

    def test_deserialize(self):
        schema = Comment().bind()
        clean = schema.deserialize(comment_data)

        # must remove flag_count so that it doesn't get updated directly
        self.assertNotIn('flag_count', clean)
        # check typed fields
        self.assertIsInstance(clean.pop('submit_datetime'), datetime)
        self.assertEqual(clean.pop('is_removed'), False)

        self.assertEqual(len(clean), len(comment_data) - 3)
        self.assertDictContainsSubset(clean, comment_data)

        # check that missing required fields raise an exception
        incomplete_data = comment_data.copy()
        required_fields = (
            'app_uuid', 'content_uuid', 'user_uuid', 'comment', 'user_name',
            'submit_datetime', 'content_type', 'content_title', 'content_url',
            'locale')
        for field in required_fields:
            del incomplete_data[field]

        try:
            schema.deserialize(incomplete_data)
            self.fail('Expected colander.Invalid to be raised')
        except colander.Invalid as e:
            self.assertEqual(len(e.children), len(required_fields))

        # check that missing fields with model defaults are dropped
        missing_data = comment_data.copy()
        fields_with_model_default = (
            'uuid', 'flag_count', 'is_removed', 'moderation_state',
            'ip_address')
        for field in fields_with_model_default:
            del missing_data[field]

        clean = schema.deserialize(missing_data)
        for field in fields_with_model_default:
            self.assertNotIn(field, clean)

    def test_serialize(self):
        schema = Comment(include_all=True).bind()
        clean = schema.serialize(comment_model_data)

        self.assertEqual(clean, comment_data)
        # check that flag_count got serialized
        self.assertIn('flag_count', clean)

        # check that missing fields are dropped
        missing_and_none_data = comment_model_data.copy()
        del missing_and_none_data['ip_address']
        clean = schema.serialize(missing_and_none_data)
        self.assertEqual(clean['ip_address'], 'None')
        missing_and_none_data['ip_address'] = None
        clean = schema.serialize(missing_and_none_data)
        self.assertEqual(clean['ip_address'], 'None')


class FlagTestCase(TestCase):
    pass


class ValidatorTestCase(TestCase):
    pass
