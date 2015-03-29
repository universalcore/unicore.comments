from uuid import uuid4

from sqlalchemy import (Column, Integer, Unicode, MetaData, Table, Index,
                        DateTime, ForeignKey, Boolean)
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
    Column('content_url', URLType(), nullable=False),
    Column('locale', Unicode(6), nullable=False),
    Column('flag_count', Integer, default=0, nullable=False),
    Column('is_removed', Boolean, default=False, nullable=False),
    Column(
        'moderation_state', Unicode(255), default='visible', nullable=False),
    # Not required data
    Column('ip_address', Unicode(15)),
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
