import mock

from unicore.comments.service.tests import BaseTestCase
from unicore.comments.service import db


class DBTestCase(BaseTestCase):

    def test_in_transaction(self):
        func = mock.Mock(return_value='foobar')
        transaction = mock.Mock(
            rollback=mock.Mock(), commit=mock.Mock())
        connection = mock.Mock(
            begin=mock.Mock(return_value=transaction),
            close=mock.Mock())

        patch_connect = mock.patch.object(
            self.engine, 'connect', new=mock.Mock(return_value=connection))
        patch_connect.start()

        result = self.successResultOf(
            db.in_transaction(self.engine, func, 'foo', bar='bar'))
        self.assertEqual(result, 'foobar')
        func.assert_called_with(connection, 'foo', bar='bar')
        connection.begin.assert_called()
        transaction.commit.assert_called()
        transaction.rollback.assert_not_called()
        connection.close.assert_called()

        func.side_effect = KeyError
        transaction.reset_mock()
        connection.reset_mock()

        self.failureResultOf(
            db.in_transaction(self.engine, func, 'foo', bar='bar'))
        transaction.commit.assert_not_called()
        transaction.rollback.assert_called()
        connection.close.assert_called()

        patch_connect.stop()
