import colander

from unicore.comments.service import validators as vlds


class Comment(colander.MappingSchema):
    user_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    user_name = colander.SchemaNode(
        colander.String(),
        missing=None)
    comment = colander.SchemaNode(
        colander.String(),
        validator=vlds.comment_validator)
    submit_datetime = colander.SchemaNode(
        colander.DateTime())
    ip_address = colander.SchemaNode(
        colander.String(),
        validator=vlds.ip_address_validator,
        missing=None)
