import uuid
from datetime import datetime
from unittest import TestCase

import pytz
import colander

from unicore.comments.service.models import (
    COMMENT_MAX_LENGTH, COMMENT_CONTENT_TYPES, COMMENT_MODERATION_STATES)
from unicore.comments.service.schema import (
    Comment, Flag, BannedUser, StreamMetadata)
from unicore.comments.service.tests.test_models import (
    comment_data as comment_model_data,
    flag_data as flag_model_data,
    banneduser_data as banneduser_model_data,
    streammetadata_data as streammetadata_model_data)


def simple_serialize(data):
    for key in data.keys():
        value = data[key]
        if isinstance(value, bool):
            data[key] = 'true' if value else 'false'
        elif isinstance(value, int):
            data[key] = str(value)
        elif isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, uuid.UUID):
            data[key] = value.hex
        elif isinstance(value, dict):
            data[key] = value.copy()
        else:
            data[key] = unicode(value)


comment_data = comment_model_data.copy()
flag_data = flag_model_data.copy()
banneduser_data = banneduser_model_data.copy()
streammetadata_data = streammetadata_model_data.copy()

for data in (comment_data, flag_data, banneduser_data, streammetadata_data):
    simple_serialize(data)


class CommentTestCase(TestCase):

    def test_deserialize(self):
        schema = Comment().bind()
        clean = schema.deserialize(comment_data)

        # must remove flag_count so that it doesn't get updated directly
        self.assertNotIn('flag_count', clean)
        # check typed fields
        self.assertIsInstance(clean.pop('submit_datetime'), datetime)
        self.assertEqual(clean.pop('is_removed'), False)

        self.assertEqual(len(clean), len(comment_model_data) - 3)
        self.assertDictContainsSubset(clean, comment_model_data)

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

        # check that missing/None fields are 'None'
        missing_and_none_data = comment_model_data.copy()
        del missing_and_none_data['ip_address']
        clean = schema.serialize(missing_and_none_data)
        self.assertEqual(clean['ip_address'], 'None')
        missing_and_none_data['ip_address'] = None
        clean = schema.serialize(missing_and_none_data)
        self.assertEqual(clean['ip_address'], 'None')


class FlagTestCase(TestCase):

    def test_deserialize(self):
        schema = Flag().bind()
        clean = schema.deserialize(flag_data)

        self.assertEqual(
            clean.pop('submit_datetime'),
            flag_model_data['submit_datetime'].replace(tzinfo=pytz.UTC))
        self.assertEqual(len(clean), len(flag_model_data) - 1)
        self.assertDictContainsSubset(clean, flag_model_data)

        # check that missing required fields raise an exception
        # all flag fields are required
        incomplete_data = {}
        try:
            schema.deserialize(incomplete_data)
            self.fail('Expected colander.Invalid to be raised')
        except colander.Invalid as e:
            self.assertEqual(len(e.children), len(flag_data))

    def test_serialize(self):
        schema = Flag().bind()
        clean = schema.serialize(flag_model_data)
        self.assertEqual(clean, flag_data)


class BannedUserTestCase(TestCase):

    def test_deserialize(self):
        schema = BannedUser().bind()
        clean = schema.deserialize(banneduser_data)

        self.assertEqual(
            clean.pop('created'),
            banneduser_model_data['created'].replace(tzinfo=pytz.UTC))
        self.assertEqual(len(clean), len(banneduser_model_data) - 1)
        self.assertDictContainsSubset(clean, banneduser_model_data)

        copy = banneduser_data.copy()
        del copy['created']
        clean = schema.deserialize(copy)
        self.assertNotIn('created', clean)

    def test_serialize(self):
        schema = BannedUser().bind()
        clean = schema.serialize(banneduser_model_data)
        self.assertEqual(clean, banneduser_data)


class StreamMetadataTestCase(TestCase):

    def test_deserialize(self):
        schema = StreamMetadata().bind()
        clean = schema.deserialize(streammetadata_data)
        self.assertEqual(clean, streammetadata_model_data)

        copy = streammetadata_data.copy()
        del copy['metadata']
        clean = schema.deserialize(copy)
        self.assertEqual(clean.get('metadata', None), {})

    def test_serialize(self):
        schema = StreamMetadata().bind()
        clean = schema.serialize(streammetadata_model_data)
        self.assertEqual(clean, streammetadata_data)


class ValidatorTestCase(TestCase):
    schema_flag = Flag().bind()
    schema_comment = Comment().bind()

    def setUp(self):
        self.data_flag = flag_data.copy()
        self.data_comment = comment_data.copy()

    def test_uuid_validator(self):
        self.data_flag['app_uuid'] = 'notauuid'
        self.assertRaisesRegexp(
            colander.Invalid, "'app_uuid'",
            self.schema_flag.deserialize, self.data_flag)

    def test_comment_uuid_validator(self):
        comment_uuid = self.data_flag['comment_uuid']
        schema = Flag().bind(comment_uuid=comment_uuid)
        self.assertEqual(
            schema.deserialize(self.data_flag)['comment_uuid'],
            uuid.UUID(comment_uuid))

        other_uuid = uuid.uuid4().hex
        schema = Flag().bind(comment_uuid=other_uuid)
        self.assertRaisesRegexp(
            colander.Invalid, "is not one of %s" % uuid.UUID(other_uuid),
            schema.deserialize, self.data_flag)

    def test_ip_address_validator(self):
        self.data_comment['ip_address'] = 'notanipaddress'
        self.assertRaisesRegexp(
            colander.Invalid, "'ip_address'",
            self.schema_comment.deserialize, self.data_comment)

    def test_locale_validator(self):
        self.data_comment['locale'] = 'notalocale'
        self.assertRaisesRegexp(
            colander.Invalid, "'locale'",
            self.schema_comment.deserialize, self.data_comment)

    def test_comment_validator(self):
        for val in ('', 'a' * (COMMENT_MAX_LENGTH + 1)):
            self.data_comment['comment'] = val
            self.assertRaisesRegexp(
                colander.Invalid, "'comment'",
                self.schema_comment.deserialize, self.data_comment)

    def test_content_type_validator(self):
        self.data_comment['content_type'] = 'notacontenttype'
        types = ', '.join(COMMENT_CONTENT_TYPES)
        self.assertRaisesRegexp(
            colander.Invalid, 'is not one of %s' % types,
            self.schema_comment.deserialize, self.data_comment)

    def test_content_url_validator(self):
        self.data_comment['content_url'] = 'notacontenturl'
        self.assertRaisesRegexp(
            colander.Invalid, "'content_url'",
            self.schema_comment.deserialize, self.data_comment)

    def test_moderation_state_validator(self):
        self.data_comment['moderation_state'] = 'notamoderationstate'
        states = ', '.join(map(lambda t: t[0], COMMENT_MODERATION_STATES))
        self.assertRaisesRegexp(
            colander.Invalid, 'is not one of %s' % states,
            self.schema_comment.deserialize, self.data_comment)
