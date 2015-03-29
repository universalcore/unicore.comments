import yaml

from confmodel import Config as ConfigBase
from confmodel.fields import ConfigText


class Config(ConfigBase):
    database_url = ConfigText(
        'The URL specifying the database to use',
        required=True)


with open('config.yaml') as f:
    config = Config(yaml.load(f))
