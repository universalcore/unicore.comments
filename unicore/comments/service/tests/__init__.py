import os
from unittest import TestCase

from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command

from unicore.comments.service.config import Config
from unicore.comments.service import db


test_dir = os.path.dirname(__file__)


def mk_config(**overrides):
    defaults = {
        'database_url':
            'postgresql://postgres@localhost/unicore_comments_test'
    }
    defaults.update(overrides)
    return Config(defaults)


def mk_alembic_config(app_config):
    config = AlembicConfig(os.path.join(test_dir, '../../../../alembic.ini'))
    config.set_main_option(
        'script_location',
        os.path.join(test_dir, '../alembic'))
    config.set_main_option('sqlalchemy.url', app_config.database_url)
    return config


class BaseTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = mk_config()
        cls.alembic_config = mk_alembic_config(cls.config)
        # migrate the database
        alembic_command.upgrade(cls.alembic_config, 'head')

        cls.engine = db.get_engine(cls.config)
        cls.connection = cls.engine.connect()

    @classmethod
    def tearDownClass(cls):
        alembic_command.downgrade(cls.alembic_config, 'base')
        cls.connection.close()

    def setUp(self):
        self.transaction = self.__class__.connection.begin()

    def tearDown(self):
        self.transaction.rollback()
