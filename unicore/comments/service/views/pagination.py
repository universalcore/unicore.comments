MAX_LIMIT = 100
DEFAULT_LIMIT = 50


def paginate(args, query):
    limit = args.get('limit', [DEFAULT_LIMIT])[0]
    limit = min(int(limit), MAX_LIMIT)
    offset = args.get('offset', [0])[0]
    offset = int(offset)
    print limit, offset

    query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    return query, limit, offset
