from alchimia import TWISTED_STRATEGY
from sqlalchemy import create_engine


def get_engine(config, reactor=None):
    if reactor is None:
        return create_engine(config.database_url)

    return create_engine(
        config.database_url, reactor=reactor, strategy=TWISTED_STRATEGY)
