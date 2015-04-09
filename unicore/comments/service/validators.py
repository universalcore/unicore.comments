import re
import uuid

import colander

from unicore.comments.service.models import (
    COMMENT_MAX_LENGTH,
    COMMENT_CONTENT_TYPES,
    COMMENT_MODERATION_STATES)


# ISO 639 3-letter code + ISO 3166-1 alpha-2
LOCALE_CODE_RE = re.compile(r'^[a-z]{3}_[A-Z]{2}$')


def known_uuid_validator(name):

    @colander.deferred
    def validator(node, kw):
        # ensure the provided uuid matches the uuid in the data
        named_uuid = kw.get(name, None)
        if named_uuid is None:
            return None
        return colander.OneOf([uuid.UUID(named_uuid)])

    return validator


def ip_address_validator(node, value):
    try:
        assert len(value) <= 15

        parts = value.split('.')
        assert len(parts) == 4

        for part in parts:
            try:
                num = int(part)
                assert 0 <= num <= 255
            except ValueError:
                raise AssertionError

    except AssertionError:
        raise colander.Invalid(
            node, '%r is not a valid IP address' % (value, ))


def locale_validator(node, value):
    if not LOCALE_CODE_RE.match(value):
        raise colander.Invalid(
            node, '%r is not a valid locale' % (value, ))


comment_validator = colander.Length(min=1, max=COMMENT_MAX_LENGTH)
content_type_validator = colander.OneOf(COMMENT_CONTENT_TYPES)
content_url_validator = colander.url
moderation_state_validator = colander.OneOf(
    map(lambda t: t[0], COMMENT_MODERATION_STATES))
