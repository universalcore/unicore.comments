from uuid import uuid4

from sqlalchemy import (Column, Integer, Unicode, MetaData, Table, Index,
                        DateTime, ForeignKey, Boolean, and_)
from sqlalchemy.inspection import inspect
from sqlalchemy_utils import UUIDType, URLType


COMMENT_MAX_LENGTH = 3000
COMMENT_TABLE_NAME = 'comments'
COMMENT_MODERATION_STATES = (
    (u'visible', u'Visible'),
    (u'removed_by_moderator', u'Removed by moderator'),
    (u'removed_by_community', u'Removed by community'),
    (u'removed_for_profanity', u'Removed for profanity'))

FLAG_TABLE_NAME = 'flags'


metadata = MetaData()


class RowObjectMixin(object):
    ''' This class simplifies dealing with individual table rows.
    An instance can be constructed using any dictionary-like object,
    including a SQLAlchemy RowProxy object.

    The methods `insert`, `update` and `get_by_pk` are provided to insert
    a new row, update an existing row or select a row by primary key.

    The `get` and `set` methods update the underlying row data. Altered
    data can be saved by calling `update`.

    TODO: use deferreds'''

    def __init__(self, connection, row):
        self.connection = connection
        self.row_dict = dict((k, v) for k, v in row.items())

    @classmethod
    def _pk_expression(cls, data):
        expressions = [
            (c == data[c.name])
            for c in inspect(cls.__table__).primary_key]
        return and_(*expressions)

    @property
    def pk_expression(self):
        return self.__class__._pk_expression(self.row_dict)

    def to_dict(self):
        return dict(
            (c.name, self.row_dict[c.name]) for c in self.__table__.c)

    def get(self, attr):
        if attr not in self.__table__.c:
            raise KeyError('%r is not a column name' % attr)

        return self.row_dict.get(attr, None)

    def set(self, attr, value):
        if attr not in self.__table__.c:
            raise KeyError('%r is not a column name' % attr)

        self.row_dict[attr] = value

    def insert(self):
        query = self.__table__ \
            .insert() \
            .values(self.row_dict)
        result = self.connection.execute(query)
        # update data with auto-generated defaults
        if result.rowcount:
            self.row_dict = result.last_inserted_params().copy()
        return result.rowcount

    def update(self):
        data_without_pk = self.row_dict.copy()
        for c in inspect(self.__table__).primary_key:
            del data_without_pk[c.name]

        query = self.__table__ \
            .update() \
            .values(**data_without_pk) \
            .where(self.pk_expression)
        result = self.connection.execute(query)
        return result.rowcount

    @classmethod
    def get_by_pk(cls, connection, pk_expression=None, **pk_fields):
        try:
            if pk_expression is None:
                pk_expression = cls._pk_expression(pk_fields)
        except KeyError:
            raise KeyError('All primary keys need to be provided')

        query = cls.__table__ \
            .select() \
            .where(pk_expression)
        result = connection.execute(query).first()
        if result is not None:
            result = cls(connection, result)
        return result


class Comment(RowObjectMixin):
    comments = Table(
        COMMENT_TABLE_NAME, metadata,
        # Identifiers
        Column(
            'uuid', UUIDType(binary=False), default=uuid4, primary_key=True),
        Column('user_uuid', UUIDType(binary=False), nullable=False),
        Column('content_uuid', UUIDType(binary=False), nullable=False),
        Column('app_uuid', UUIDType(binary=False), nullable=False),
        # Other required data
        Column('comment', Unicode(COMMENT_MAX_LENGTH), nullable=False),
        Column('user_name', Unicode(255), nullable=False),
        Column('submit_datetime', DateTime, nullable=False),
        Column('content_type', Unicode(255), nullable=False),
        Column('content_title', Unicode(255), nullable=False),
        Column('content_url', URLType(), nullable=False),
        Column('locale', Unicode(6), nullable=False),
        Column('flag_count', Integer, default=0, nullable=False),
        Column('is_removed', Boolean, default=False, nullable=False),
        Column(
            'moderation_state', Unicode(255), default=u'visible',
            nullable=False),
        # Not required data
        Column('ip_address', Unicode(15)),
        # Indexes
        Index('comment_app_content_index', 'app_uuid', 'content_uuid'),
        Index('comment_user_index', 'user_uuid'),
        Index('comment_submit_datetime_index', 'submit_datetime')
    )
    __table__ = comments


class Flag(RowObjectMixin):
    flags = Table(
        FLAG_TABLE_NAME, metadata,
        # Identifiers
        Column(
            'comment_uuid', UUIDType(binary=False),
            ForeignKey('comments.uuid'), primary_key=True),
        Column('user_uuid', UUIDType(binary=False), primary_key=True),
        # Other required data
        Column('app_uuid', UUIDType(binary=False), nullable=False),
        Column('submit_datetime', DateTime, nullable=False),
        # Indexes
        Index('flag_submit_datetime_index', 'submit_datetime'),
        Index('flag_app_index', 'app_uuid')
    )
    __table__ = flags