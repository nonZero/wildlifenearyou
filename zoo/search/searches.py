from django.conf import settings
from djape.client import Client, Query

class NotFound(Exception):
    pass

def doc_from_result_item(item):
    """Make a document from a result item.

    """
    doc = {u'search_id': item['id']}
    for key, value in item['data'].items():
        value = value[0]
        if key in latlon_fields:
            value = map(float, value.split(' '))
        doc[key] = value
    return doc

def make_lookup(dbname, latlon_fields=[]):
    client = Client(settings.XAPIAN_BASE_URL, dbname)
    def lookup(id):
        result = client.get(id)
        if len(result['items']) == 1:
            item = result['items'][0]
            return doc_from_result_item(item)
        else:
            raise NotFound, id
    return lookup

def make_searcher(dbname, latlon_fields=[]):
    client = Client(settings.XAPIAN_BASE_URL, dbname)
    def search(q, num=0):
        results = client.search(Query(q), end_rank=num)
        for item in results['items']:
            yield doc_from_result_item(item)
    return search

search_locations = make_searcher(
    settings.XAPIAN_LOCATION_DB, latlon_fields = ['latlon']
)
lookup_location = make_lookup(
    settings.XAPIAN_LOCATION_DB, latlon_fields = ['latlon']
)

search_species = make_searcher(settings.XAPIAN_SPECIES_DB)
lookup_species = make_lookup(settings.XAPIAN_SPECIES_DB)
