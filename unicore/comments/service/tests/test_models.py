from uuid import UUID
from datetime import datetime, timedelta
from unittest import TestCase
import pytz

from alembic import command as alembic_command
from sqlalchemy.sql.expression import exists
from sqlalchemy.inspection import inspect

from unicore.comments.service.tests import (BaseTestCase, mk_alembic_config,
                                            mk_config)
from unicore.comments.service.models import Comment, Flag, BannedUser


comment_data = {
    'uuid': UUID('d269f09c4672400da4250342d9d7e1e4'),
    'user_uuid': UUID('2923280ee1904478bfcf7a46f26f443b'),
    'content_uuid': UUID('f587b74816bb425ab043f1cf30de7abe'),
    'app_uuid': UUID('bbc0035128b34ed48bdacab1799087c5'),
    'comment': u'this is a comment',
    'user_name': u'foo',
    'submit_datetime': datetime.now(pytz.utc),
    'content_type': u'page',
    'content_title': u'I Am A Page',
    'content_url': u'http://example.com/page/',
    'locale': u'eng_ZA',
    'flag_count': 0,
    'is_removed': False,
    'moderation_state': u'visible',
    'ip_address': u'192.168.1.1'
}
flag_data = {
    'comment_uuid': UUID('d269f09c4672400da4250342d9d7e1e4'),
    'user_uuid': UUID('63f058d5de5143ecb455382bf654100c'),
    'app_uuid': UUID('bbc0035128b34ed48bdacab1799087c5'),
    'submit_datetime': datetime.now(pytz.utc)
}
banneduser_data = {
    'user_uuid': UUID('63f058d5de5143ecb455382bf654100c'),
    'app_uuid': UUID('bbc0035128b34ed48bdacab1799087c5'),
    'created': datetime.now(pytz.utc),
}


class MigrationTestCase(TestCase):

    def test_migrations(self):
        alembic_config = mk_alembic_config(mk_config())
        alembic_command.upgrade(alembic_config, 'head')
        alembic_command.downgrade(alembic_config, 'base')


class ModelTests(object):
    model_class = None
    instance_data = None

    def test_insert(self):
        data_no_defaults = self.instance_data.copy()
        columns_with_defaults = []
        for column in self.model_class.__table__.c:
            if column.default or column.server_default:
                del data_no_defaults[column.name]
                columns_with_defaults.append(column)

        obj = self.model_class(self.connection, data_no_defaults)
        result = self.successResultOf(obj.insert())

        # check for existence in database
        self.assertEqual(result, 1)
        exists_query = self.model_class.__table__ \
            .select(
                exists().where(obj.pk_expression)
            )
        result = self.successResultOf(self.connection.execute(exists_query))
        result = self.successResultOf(result.scalar())
        self.assertTrue(result)

        # check that default values are assigned
        for column in columns_with_defaults:
            self.assertNotEqual(obj.get(column.name), None)

    def test_update(self):
        obj = self.model_class(self.connection, self.instance_data)
        self.successResultOf(obj.insert())

        new_data = self.instance_data.copy()
        for key in new_data.keys():
            if key.endswith('uuid'):
                del new_data[key]
            elif isinstance(new_data[key], basestring):
                new_data[key] = u'new'
            elif isinstance(new_data[key], datetime):
                new_data[key] = datetime.now(pytz.utc) + timedelta(hours=1)

        for key, value in new_data.iteritems():
            obj.set(key, value)
        result = self.successResultOf(obj.update())

        # check that both obj and database contain new data
        self.assertEqual(result, 1)
        obj_from_db = self.successResultOf(self.model_class.get_by_pk(
            self.connection, pk_expression=obj.pk_expression))
        for instance in (obj, obj_from_db):
            for key, value in new_data.iteritems():
                self.assertEqual(instance.get(key), value)

    def test_delete(self):
        obj = self.model_class(self.connection, self.instance_data)
        self.successResultOf(obj.insert())

        # check that we can delete with only primary keys
        pk_fields = dict(
            (c.name, obj.get(c.name))
            for c in inspect(self.model_class.__table__).primary_key)
        obj_deleted = self.model_class(self.connection, pk_fields)
        result = self.successResultOf(obj_deleted.delete())

        self.assertEqual(result, 1)
        exists_query = self.model_class.__table__ \
            .select(
                exists().where(obj.pk_expression)
            )
        result = self.successResultOf(self.connection.execute(exists_query))
        result = self.successResultOf(result.scalar())
        self.assertFalse(result)

        # check that object is updated with row data that was deleted
        self.assertEqual(obj.row_dict, obj_deleted.row_dict)

    def test_get_by_pk(self):
        obj = self.model_class(self.connection, self.instance_data)
        self.successResultOf(obj.insert())

        # check that primary key lookup returns a result
        pk_fields = dict(
            (c.name, obj.get(c.name))
            for c in inspect(self.model_class.__table__).primary_key)
        obj_from_db = self.successResultOf(
            self.model_class.get_by_pk(self.connection, **pk_fields))
        self.assertTrue(obj_from_db)

        # check that error is raised if a primary key is missing
        del pk_fields[pk_fields.keys()[0]]
        failure = self.failureResultOf(
            self.model_class.get_by_pk(self.connection, **pk_fields))
        with self.assertRaisesRegexp(KeyError, 'keys need to be provided'):
            failure.raiseException()

    def test_get_set(self):
        obj = self.model_class(self.connection, {})

        for key, value in self.instance_data.iteritems():
            obj.set(key, value)
            self.assertEqual(obj.get(key), value)
        self.assertEqual(obj.row_dict, self.instance_data)

        with self.assertRaisesRegexp(KeyError, 'not a column name'):
            obj.set('doesnotexist', 'value')
        with self.assertRaisesRegexp(KeyError, 'not a column name'):
            obj.get('doesnotexist')

    def test_to_dict(self):
        obj = self.model_class(self.connection, self.instance_data)
        self.assertEqual(self.instance_data, obj.to_dict())


class CommentTestCase(BaseTestCase, ModelTests):
    model_class = Comment
    instance_data = comment_data


class FlagTestCase(BaseTestCase, ModelTests):
    model_class = Flag
    instance_data = flag_data

    def setUp(self):
        super(FlagTestCase, self).setUp()
        self.comment = Comment(self.connection, comment_data)
        self.successResultOf(self.comment.insert())


class BannerUserTestCase(BaseTestCase, ModelTests):
    model_class = BannedUser
    instance_data = banneduser_data

    def test_insert_without_app_uuid(self):
        data_no_app_uuid = self.instance_data.copy()
        del data_no_app_uuid['app_uuid']
        obj = self.model_class(self.connection, data_no_app_uuid)
        result = self.successResultOf(obj.insert())
        self.assertEqual(result, 1)

    def test_to_dict(self):
        data = self.instance_data.copy()
        data['id'] = 1
        obj = self.model_class(self.connection, data)
        self.assertEqual(data, obj.to_dict())
