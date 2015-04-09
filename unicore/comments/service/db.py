import functools

from alchimia import TWISTED_STRATEGY
from sqlalchemy import create_engine
from twisted.internet.defer import inlineCallbacks, returnValue

from unicore.comments.service import app


def get_engine(config, reactor):
    return create_engine(
        config.database_url, reactor=reactor, strategy=TWISTED_STRATEGY)


def in_transaction(func):

    @functools.wraps(func)
    @inlineCallbacks
    def wrapper(*args, **kwargs):
        connection = yield app.db_engine.connect()
        transaction = yield connection.begin()

        try:
            returnVal = yield func(*args, connection=connection, **kwargs)
        except Exception as e:
            yield transaction.rollback()
            raise e
        else:
            yield transaction.commit()
        finally:
            yield connection.close()

        returnValue(returnVal)

    return wrapper
