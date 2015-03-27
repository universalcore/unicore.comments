from cqlengine import columns
from cqlengine.models import Model
from cqlengine.management import create_keyspace, sync_table
from cqlengine.connection import setup

from unicore.comments.service.validators import COMMENT_MAX_LENGTH


setup(hosts=['localhost'], default_keyspace='unicore_comments')


class DictMixin(object):

    @classmethod
    def from_dict(cls, session, data):
        obj = cls()
        obj.update(data)
        return obj

    def to_dict(self):
        return dict((name, getattr(self, name))
                    for name in self._defined_columns.keys())


class Comment(Model, DictMixin):
    __table_name__ = 'comments'
    __keyspace__ = 'unicore_comments'

    '''
    Identifiers
    '''
    app_uuid = columns.UUID(primary_key=True)  # parition key
    content_uuid = columns.UUID(primary_key=True)  # clustering key
    # clustering key
    uuid = columns.TimeUUID(primary_key=True, clustering_order='DESC')
    user_uuid = columns.UUID(primary_key=True)  # clustering key
    '''
    Other required data
    '''
    comment = columns.Text(max_length=COMMENT_MAX_LENGTH, required=True)
    user_name = columns.Text(max_length=255, required=True)
    submit_datetime = columns.DateTime(required=True)
    content_type = columns.Text(max_length=255, required=True)
    content_title = columns.Text(max_length=255, required=True)
    locale = columns.Text(max_length=6, required=True)
    '''
    Not required data
    '''
    ip_address = columns.Text(max_length=15)
    flag_count = columns.Integer(default=0)


class Flag(Model, DictMixin):
    __table_name__ = 'flags'
    __keyspace__ = 'unicore_comments'

    app_uuid = columns.UUID(primary_key=True)  # parition key
    comment_uuid = columns.UUID(primary_key=True)  # clustering key
    user_uuid = columns.UUID(primary_key=True)  # clustering key
    submit_datetime = columns.DateTime(required=True)


create_keyspace('unicore_comments', 'SimpleStrategy', 1)
sync_table(Comment)
sync_table(Flag)
