from alchimia import TWISTED_STRATEGY
from sqlalchemy import create_engine


def get_engine(config, reactor):
    return create_engine(
        config.database_url, reactor=reactor, strategy=TWISTED_STRATEGY)
