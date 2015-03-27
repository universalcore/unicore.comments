from uuid import uuid4

from sqlalchemy import (Column, Integer, Unicode, MetaData, Table, Index,
                        DateTime, ForeignKey)
from sqlalchemy_utils import UUIDType


COMMENT_MAX_LENGTH = 3000
COMMENT_TABLE_NAME = 'comments'
FLAG_TABLE_NAME = 'flags'


metadata = MetaData()


comments = Table(
    COMMENT_TABLE_NAME, metadata,
    # Identifiers
    Column('uuid', UUIDType(binary=False), default=uuid4, primary_key=True),
    Column('user_uuid', UUIDType(binary=False), nullable=False),
    Column('content_uuid', UUIDType(binary=False), nullable=False),
    Column('app_uuid', UUIDType(binary=False), nullable=False),
    # Other required data
    Column('comment', Unicode(COMMENT_MAX_LENGTH), nullable=False),
    Column('user_name', Unicode(255), nullable=False),
    Column('submit_datetime', DateTime, nullable=False),
    Column('content_type', Unicode(255), nullable=False),
    Column('content_title', Unicode(255), nullable=False),
    Column('locale', Unicode(6), nullable=False),
    # Not required data
    Column('ip_address', Unicode(15)),
    Column('flag_count', Integer, default=0),
    # Indexes
    Index('comment_app_content_index', 'app_uuid', 'content_uuid'),
    Index('comment_user_index', 'user_uuid'),
    Index('comment_submit_datetime_index', 'submit_datetime')
)


flags = Table(
    FLAG_TABLE_NAME, metadata,
    # Identifiers
    Column(
        'comment_uuid', UUIDType(binary=False), ForeignKey('comments.uuid'),
        primary_key=True),
    Column('user_uuid', UUIDType(binary=False), primary_key=True),
    # Other required data
    Column('app_uuid', UUIDType(binary=False), nullable=False),
    Column('submit_datetime', DateTime, nullable=False),
    # Indexes
    Index('flag_submit_datetime_index', 'submit_datetime'),
    Index('flag_app_index', 'app_uuid')
)
