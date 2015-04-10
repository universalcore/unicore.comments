import sys
import argparse

import yaml
from twisted.internet import reactor

from unicore.comments.service import db, app, views  # noqa
from unicore.comments.service.config import Config


def configure_app():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', required=True)
    parser.add_argument('-p', '--port')
    args = parser.parse_args(sys.argv[1:])

    with open(args.config) as f:
        config = Config(yaml.load(f.read()))

    if args.port:
        config.port = args.port

    db_engine = db.get_engine(config, reactor)

    app.db_engine = db_engine
    app.config = config


if __name__ == '__main__':
    configure_app()
    app.run("localhost", app.config.port)
