from confmodel import Config as ConfigBase
from confmodel.fields import ConfigText, ConfigInt


class Config(ConfigBase):
    database_url = ConfigText(
        'The URL specifying the database to use',
        required=True)
    port = ConfigInt(
        'The port to listen on',
        default=8080)
