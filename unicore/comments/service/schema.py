import colander

from unicore.comments.service import validators as vlds


class Comment(colander.MappingSchema):
    '''
    Identifiers
    '''
    uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.comment_uuid_validator,
        missing=colander.drop)
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
    content_url = colander.SchemaNode(
        colander.String(),
        validator=vlds.content_url_validator)
    locale = colander.SchemaNode(
        colander.String(),
        validator=vlds.locale_validator)
    is_removed = colander.SchemaNode(
        colander.Boolean(),
        missing=colander.drop)
    moderation_state = colander.SchemaNode(
        colander.String(),
        validator=vlds.moderation_state_validator,
        missing=colander.drop)
    '''
    Not required data
    '''
    ip_address = colander.SchemaNode(
        colander.String(),
        validator=vlds.ip_address_validator,
        missing=colander.drop,
        default='None')

    def __init__(self, *args, **kwargs):
        super(Comment, self).__init__(*args, **kwargs)

        # Add flag_count only if include_all is True.
        # Flag count should only be updated via the Flag API.
        if kwargs.get('include_all', False):
            self.add(colander.SchemaNode(
                colander.Integer(),
                name='flag_count',
                missing=colander.drop))


class Flag(colander.MappingSchema):
    comment_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.comment_uuid_validator)
    user_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    app_uuid = colander.SchemaNode(
        colander.String(),
        validator=vlds.uuid_validator)
    submit_datetime = colander.SchemaNode(
        colander.DateTime())