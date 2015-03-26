import uuid

import colander


COMMENT_MAX_LENGTH = 3000


def uuid_validator(node, value):
    try:
        uuid.UUID(value)
    except ValueError:
        raise colander.Invalid(
            '%r is not a valid hexadecimal UUID' % (value, ))


def ip_address_validator(node, value):
    err_msg = '%r is not a valid IP address' % (value, )

    if len(value) > 15:
        raise colander.Invalid(err_msg)

    parts = value.split('.')
    if len(parts) != 4:
        raise colander.Invalid(err_msg)

    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                raise colander.Invalid(err_msg)
        except ValueError:
            raise colander.Invalid(err_msg)


comment_validator = colander.Length(min=1, max=COMMENT_MAX_LENGTH)
