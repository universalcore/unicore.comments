import os
from uuid import UUID, uuid4

from sqlalchemy import (Column, Unicode, DateTime, ForeignKey, Integer,
                        Index, create_engine)
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import UUIDType

from unicore.comments.service.validators import COMMENT_MAX_LENGTH


Base = declarative_base()
engine = create_engine(os.environ.get('DATABASE_URL'))
Session = sessionmaker(bind=engine)


class DictMixin(object):

    @classmethod
    def from_dict(cls, session, data):
        obj = cls()
        for key, value in data.iteritems():
            setattr(obj, key, value)

        session.add(obj)
        session.flush()
        return obj

    def to_dict(self):
        return dict((c.name, getattr(self, c.name))
                    for c in self.__table__.columns)


class UUIDMixin(object):
    _uuid = Column(
        UUIDType(binary=False), name='uuid', default=uuid4,
        primary_key=True)

    @property
    def uuid(self):
        return self._uuid.hex

    @uuid.setter
    def uuid(self, value):
        if isinstance(value, UUID):
            self._uuid = value
        else:
            self._uuid = UUID(hex=value)


class Comment(Base, UUIDMixin, DictMixin):
    __tablename__ = 'comments'
    __table_args__ = (
        Index('comment_app_content_index', 'app_uuid', 'content_uuid'),
        Index('comment_user_index', 'user_uuid'),
        Index('comment_submit_datetime_index', 'submit_datetime'))

    '''
    Identifiers
    '''
    user_uuid = Column(UUIDType(binary=False), nullable=False)
    content_uuid = Column(UUIDType(binary=False), nullable=False)
    app_uuid = Column(UUIDType(binary=False), nullable=False)
    '''
    Other required data
    '''
    comment = Column(Unicode(COMMENT_MAX_LENGTH), nullable=False)
    user_name = Column(Unicode(255), nullable=False)
    submit_datetime = Column(DateTime, nullable=False)
    content_type = Column(Unicode(255), nullable=False)
    content_title = Column(Unicode(255), nullable=False)
    locale = Column(Unicode(6), nullable=False)
    '''
    Not required data
    '''
    ip_address = Column(Unicode(15))
    flag_count = Column(Integer, default=0)

    flags = relationship('Flag', backref='comment', lazy='dynamic')


class Flag(Base, DictMixin):
    __tablename__ = 'flags'
    __table_args__ = (Index('flag_submit_datetime_index', 'submit_datetime'),
                      Index('flag_app_index', 'app_uuid'))

    comment_uuid = Column(
        UUIDType(binary=False), ForeignKey('comments.uuid'), primary_key=True)
    user_uuid = Column(
        UUIDType(binary=False), primary_key=True)
    # same as Comment.app_uuid (for partitioning)
    app_uuid = Column(UUIDType(binary=False), nullable=False)
    submit_datetime = Column(DateTime, nullable=False)

    @classmethod
    def from_dict(cls, session, data):
        obj = super(Flag, cls).from_dict(session, data)
        obj.app_uuid = obj.comment.app_uuid
        return obj


Base.metadata.create_all(engine)
