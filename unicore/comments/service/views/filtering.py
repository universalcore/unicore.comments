import colander

from sqlalchemy import and_

from unicore.comments.service.schema import UUIDType, Comment, Flag


VALID_FILTER_TYPES = {
    UUIDType: {'exact_match', 'in'},
    colander.String: {'exact_match', 'in', 'like'},
    colander.DateTime: {'exact_match', 'in', 'range'},
    colander.Boolean: {'exact_match'},
    colander.Integer: {'exact_match', 'in', 'range'}
}
ALL = object()


class DelimitedSequenceSchema(colander.SequenceSchema):

    def __init__(self, delimiter=',', *args, **kwargs):
        super(DelimitedSequenceSchema, self).__init__(*args, **kwargs)
        self.delimiter = delimiter

    def deserialize(self, cstruct):
        if isinstance(cstruct, basestring):
            cstruct = cstruct.split(self.delimiter)
        return super(DelimitedSequenceSchema, self).deserialize(cstruct)


class FilterSchema(colander.MappingSchema):

    def __init__(self, *args, **kwargs):
        super(FilterSchema, self).__init__(*args, **kwargs)

        filter_spec = kwargs.get('filter_spec', {})
        new_nodes = []
        old_nodes = []

        for node in self:
            self.set_default_node_attributes(node)

        for name, filters in filter_spec.iteritems():
            node = self.get(name)
            valid_filters = VALID_FILTER_TYPES[node.typ.__class__]
            if filters is ALL:
                filters = valid_filters

            for f in set(filters) - {'exact_match'}:
                if f not in valid_filters:
                    raise ValueError(
                        '%f is not a valid filter for %s' % node.typ)
                method = getattr(self, 'get_%s_nodes' % f)
                new_nodes.extend(method(node))

            if 'exact_match' not in filters:
                old_nodes.append(node)

        for node in new_nodes:
            self.add(node)

        for node in old_nodes:
            del self[node.name]

    @classmethod
    def from_schema(self, schema, filter_spec):
        children = map(
            lambda c: c.clone(),
            filter(lambda c: c.name in filter_spec, schema.children))
        return FilterSchema(children=children, filter_spec=filter_spec)

    def get_range_nodes(self, node):
        if not isinstance(node.typ, (colander.Integer, colander.DateTime)):
            return []

        range_nodes = []
        for range_suffix in ('_gt', '_gte', '_lt', '_lte'):
            range_node = node.clone()
            range_node.name = '%s%s' % (range_node.name, range_suffix)
            range_node.filter_type = 'range'
            range_nodes.append(range_node)
        return range_nodes

    def get_in_nodes(self, node):
        if isinstance(node.typ, colander.Boolean):
            return []

        in_node = DelimitedSequenceSchema(
            name='%s_in' % node.name,
            children=[node.clone()],
            filter_type='in',
            missing=colander.drop,
            delimiter=',')
        return [in_node]

    def get_like_nodes(self, node):
        if not isinstance(node.typ, colander.String):
            return []

        like_node = node.clone()
        # validator for exact_match node cannot
        # generally be applied to like node
        like_node.validator = None
        like_node.name = '%s_like' % node.name
        like_node.filter_type = 'like'
        return [like_node]

    def set_default_node_attributes(self, node):
        # filters aren't required
        node.missing = colander.drop
        if hasattr(node, 'filter_type'):
            return
        node.filter_type = 'exact_match'

    def convert_lists(self, cstruct):

        def convert_list(maybe_list):
            if isinstance(maybe_list, (tuple, list)):
                if len(maybe_list) > 0:
                    return maybe_list[0]
                else:
                    return ''
            return maybe_list

        return dict((k, convert_list(v)) for k, v in cstruct.iteritems())

    def get_filter_expression(self, cstruct, cols):
        cstruct = self.convert_lists(cstruct)
        data = self.deserialize(cstruct)
        expressions = [
            self.get_expression_for_node(self.get(key), cols, value)
            for key, value in data.iteritems()]
        return and_(*expressions)

    def get_expression_for_node(self, node, cols, value):
        expr = None

        if node.filter_type == 'exact_match':
            column = cols.get(node.name)
            expr = column == value

        elif node.filter_type == 'in':
            column = cols.get(node.name[:-3])
            expr = column.in_(value)

        elif node.filter_type == 'like':
            column = cols.get(node.name[:-5])
            expr = column.ilike('%' + value + '%')

        elif node.filter_type == 'range':
            name, suffix = node.name.rsplit('_', 1)
            column = cols.get(name)
            if suffix == 'gt':
                expr = column > value
            elif suffix == 'gte':
                expr = column >= value
            elif suffix == 'lt':
                expr = column < value
            elif suffix == 'lte':
                expr = column <= value

        return expr


comment_filters = FilterSchema.from_schema(Comment(include_all=True), {
    'content_uuid': ALL,
    'content_type': ALL,
    'content_title': ALL,
    'user_uuid': ALL,
    'user_name': ALL,
    'app_uuid': ALL,
    'submit_datetime': ALL,
    'is_removed': ALL,
    'moderation_state': ALL,
    'flag_count': ALL
})
flag_filters = FilterSchema.from_schema(Flag(), {
    'comment_uuid': ALL,
    'user_uuid': ALL,
    'app_uuid': ALL,
    'submit_datetime': ALL
})
