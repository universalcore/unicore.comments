import colander

from unicore.comments.service import validators as vlds


class Comment(colander.MappingSchema):
    '''
    Identifiers
    '''
    app_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    content_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    user_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    '''
    Other required data
    '''
    comment = colander.SchemaNode(
        colander.String(),
        validator=vlds.comment_validator)
    user_name = colander.SchemaNode(
        colander.String())
    submit_datetime = colander.SchemaNode(
        colander.DateTime())
    content_type = colander.SchemaNode(
        colander.String(),
        validator=vlds.content_type_validator)
    content_title = colander.SchemaNode(
        colander.String())
    locale = colander.SchemaNode(
        colander.String(),
        validator=vlds.locale_validator)
    '''
    Not required data
    '''
    ip_address = colander.SchemaNode(
        colander.String(),
        validator=vlds.ip_address_validator,
        missing=None)


class Flag(colander.MappingSchema):
    comment_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    user_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    submit_datetime = colander.SchemaNode(
        colander.DateTime())
