import sys
import argparse

import yaml
from klein import Klein
from twisted.internet import reactor

from unicore.comments.service import db
from unicore.comments.service.config import Config


app = Klein()
resource = app.resource


def configure_app():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', required=True)
    parser.add_argument('-p', '--port')
    args = parser.parse_args(sys.argv)

    with open(args['config']) as f:
        config = Config(yaml.load(f.read()))

    if args['port']:
        config.port = args['port']

    db_engine = db.get_engine(config, reactor)

    app.db_engine = db_engine
    app.config = config

    from unicore.comments.service.views import comments, flags  # noqa


if __name__ == '__main__':
    configure_app()
    app.run("localhost", app.config.port)
