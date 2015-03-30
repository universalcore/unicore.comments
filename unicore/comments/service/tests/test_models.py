from datetime import datetime, timedelta

from sqlalchemy.sql.expression import exists
from sqlalchemy.inspection import inspect

from unicore.comments.service.tests import BaseTestCase
from unicore.comments.service.models import Comment, Flag


comment_data = {
    'uuid': 'd269f09c4672400da4250342d9d7e1e4',
    'user_uuid': '2923280ee1904478bfcf7a46f26f443b',
    'content_uuid': 'f587b74816bb425ab043f1cf30de7abe',
    'app_uuid': 'bbc0035128b34ed48bdacab1799087c5',
    'comment': 'this is a comment',
    'user_name': 'foo',
    'submit_datetime': datetime.utcnow(),
    'content_type': 'page',
    'content_title': 'I Am A Page',
    'content_url': 'http://example.com/page/',
    'locale': 'eng_ZA',
    'flag_count': 0,
    'is_removed': False,
    'moderation_state': u'visible',
    'ip_address': '192.168.1.1'
}
flag_data = {
    'comment_uuid': 'd269f09c4672400da4250342d9d7e1e4',
    'user_uuid': '63f058d5de5143ecb455382bf654100c',
    'app_uuid': 'bbc0035128b34ed48bdacab1799087c5',
    'submit_datetime': datetime.utcnow()
}


class ModelTests(object):
    model_class = None
    instance_data = None

    def test_insert(self):
        data_no_defaults = self.instance_data.copy()
        columns_with_defaults = []
        for column in self.model_class.__table__.c:
            if column.default:
                del data_no_defaults[column.name]
                columns_with_defaults.append(column)

        obj = self.model_class(self.connection, data_no_defaults)
        result = obj.insert()

        # check for existence in database
        self.assertEqual(result, 1)
        exists_query = self.model_class.__table__ \
            .select(
                exists().where(obj.pk_expression)
            )
        self.assertTrue(self.connection.execute(exists_query).scalar())

        # check that default values are assigned
        for column in columns_with_defaults:
            self.assertNotEqual(obj.get(column.name), None)

    def test_update(self):
        obj = self.model_class(self.connection, self.instance_data)
        obj.insert()

        new_data = self.instance_data.copy()
        for key in new_data.keys():
            if key.endswith('uuid'):
                del new_data[key]
            elif isinstance(new_data[key], basestring):
                new_data[key] = 'new'
            elif isinstance(new_data[key], datetime):
                new_data[key] = datetime.utcnow() + timedelta(hours=1)

        for key, value in new_data.iteritems():
            obj.set(key, value)
        result = obj.update()

        # check that both obj and database contain new data
        self.assertEqual(result, 1)
        obj_from_db = self.model_class.get_by_pk(
            self.connection, pk_expression=obj.pk_expression)
        for instance in (obj, obj_from_db):
            for key, value in new_data.iteritems():
                self.assertEqual(instance.get(key), value)

    def test_get_by_pk(self):
        obj = self.model_class(self.connection, self.instance_data)
        obj.insert()

        # check that primary key lookup returns a result
        pk_fields = dict(
            (c.name, obj.get(c.name))
            for c in inspect(self.model_class.__table__).primary_key)
        obj_from_db = self.model_class.get_by_pk(self.connection, **pk_fields)
        self.assertTrue(obj_from_db)

        # check that error is raised if a primary key is missing
        del pk_fields[pk_fields.keys()[0]]
        with self.assertRaisesRegexp(KeyError, 'keys need to be provided'):
            self.model_class.get_by_pk(self.connection, **pk_fields)

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

    @classmethod
    def setUpClass(cls):
        super(FlagTestCase, cls).setUpClass()
        cls.comment = Comment(cls.connection, comment_data)
        cls.comment.insert()
