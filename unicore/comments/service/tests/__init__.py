import os
from urlparse import urlparse, parse_qs

from alembic.config import Config as AlembicConfig
from sqlalchemy.schema import CreateTable, DropTable
from twisted.trial.unittest import TestCase
from aludel.tests.doubles import FakeReactorThreads
from klein.test.test_resource import requestMock as baseRequestMock, _render

from unicore.comments.service.config import Config
from unicore.comments.service import db
from unicore.comments.service.models import Comment, Flag


test_dir = os.path.dirname(__file__)


def requestMock(path, method="GET", body=None, headers=None):
    request = baseRequestMock(path, method, body=body, headers=headers)
    request.args = parse_qs(urlparse(request.uri).query)
    return request


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

    def setUp(self):
        self.config = mk_config()
        self.engine = db.get_engine(self.config, FakeReactorThreads())
        self.connection = self.successResultOf(self.engine.connect())

        for model in (Comment, Flag):
            self.successResultOf(
                self.connection.execute(CreateTable(model.__table__)))

    def tearDown(self):
        for model in (Flag, Comment):
            self.successResultOf(
                self.connection.execute(DropTable(model.__table__)))

        self.successResultOf(self.connection.close())


__all__ = [
    '_render',
    'requestMock',
    'mk_config',
    'mk_alembic_config',
    'BaseTestCase'
]
