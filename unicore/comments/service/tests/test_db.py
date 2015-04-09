import mock

from unicore.comments.service.tests import BaseTestCase
from unicore.comments.service import db, app


class DBTestCase(BaseTestCase):

    def setUp(self):
        super(DBTestCase, self).setUp()
        app.db_engine = self.engine
        app.config = self.config

    def tearDown(self):
        super(DBTestCase, self).tearDown()
        del app.db_engine
        del app.config

    def test_in_transaction(self):
        func = mock.Mock(return_value='foobar', __name__='func')
        wrapped_func = db.in_transaction(func)
        transaction = mock.Mock(
            rollback=mock.Mock(), commit=mock.Mock())
        connection = mock.Mock(
            begin=mock.Mock(return_value=transaction),
            close=mock.Mock())

        patch_connect = mock.patch.object(
            self.engine, 'connect', new=mock.Mock(return_value=connection))
        patch_connect.start()

        result = self.successResultOf(wrapped_func('foo', bar='bar'))
        self.assertEqual(result, 'foobar')
        func.assert_called_with('foo', bar='bar', connection=connection)
        connection.begin.assert_called()
        transaction.commit.assert_called()
        transaction.rollback.assert_not_called()
        connection.close.assert_called()

        func.side_effect = KeyError
        transaction.reset_mock()
        connection.reset_mock()

        self.failureResultOf(wrapped_func('foo', bar='bar'))
        transaction.commit.assert_not_called()
        transaction.rollback.assert_called()
        connection.close.assert_called()

        patch_connect.stop()
