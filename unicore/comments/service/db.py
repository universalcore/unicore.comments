from alchimia import TWISTED_STRATEGY
from sqlalchemy import create_engine
from twisted.internet.defer import inlineCallbacks, returnValue


def get_engine(config, reactor):
    return create_engine(
        config.database_url, reactor=reactor, strategy=TWISTED_STRATEGY)


@inlineCallbacks
def in_transaction(db_engine, func, *func_args, **func_kwargs):
    connection = yield db_engine.connect()
    transaction = yield connection.begin()

    try:
        returnVal = yield func(connection, *func_args, **func_kwargs)
    except Exception as e:
        yield transaction.rollback()
        raise e
    else:
        yield transaction.commit()
    finally:
        yield connection.close()

    returnValue(returnVal)
