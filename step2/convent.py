def convent(j):
    new_json = {
        'id': j['aid'],
        'title': j['title'],
        'url': j['link'],
        'publish_date': j['create_time_str'],
        'digest': j['digest'],
        'content': j['content']['content'],
    }
    return new_json