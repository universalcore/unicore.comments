from alchimia import TWISTED_STRATEGY
from sqlalchemy import create_engine, sessionmaker, scoped_session


Session = None


def get_engine(db_url, reactor):
    return create_engine(db_url, reactor=reactor, strategy=TWISTED_STRATEGY)


def setup_db(db_url, reactor):
    engine = get_engine(db_url, reactor)
    global Session
    Session = scoped_session(sessionmaker(bind=engine))
