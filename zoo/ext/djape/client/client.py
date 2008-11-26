
from django.utils import simplejson

import document
import errors
import field
import query
import urllib
import urllib2

class Client(object):
    """A client for the Xappy webservice.

    """

    Document = document.Document
    SearchClientError = errors.SearchClientError 
    Field = field.Field 
    Query = query.Query
    QueryPart = query.QueryPart
    FreeTextQuery = query.FreeTextQuery
    GeoDistanceQuery = query.GeoDistanceQuery

    def __init__(self, base_url, default_db_name=None):
        """Create a client.
        
        Doesn't make a connection to anything until it's used.

         - `base_url`: the base URL to connect to the service on.  Should end
           with a /.
         - `default_db_name`: the default database name to use.  (This is
           merely a convenience - this may be used instead of supplying the
           name to every call.)

        The time taken for the last call made is available in the
        `last_elapsed_time` member (this is set to None if not available).

        """
        self.base_url = base_url
        self.default_db_name = default_db_name

        self.last_elapsed_time = None

    def _doreq(self, path, qs=None, data=None):
        """Perform a request to path.

        If qs is supplied, format as a querystring, and append to the path
        used.  qs should be a dictionary of parameters.  parameter values may
        be strings, or lists (in which latter case, multiple instances will be
        sent).

        If data is supplied it is a dictionary of fields which are sent as a POST request.

        """
        if qs is not None:
            args = []
            for field, vals in qs.iteritems():
                if vals is None:
                    continue
                if not hasattr(vals, '__iter__'):
                    vals = [vals]
                vals = filter(None, vals)
                args.append((field, vals))
            path += '?' + urllib.urlencode(args, doseq=1)

        if data is None:
            fd = urllib2.urlopen(self.base_url + path)
        else:
            data = urllib.urlencode(data, doseq=1)
            fd = urllib2.urlopen(self.base_url + path, data)
        res = fd.read()
        fd.close()

        res = simplejson.loads(res)
        if 'elapsed' in res:
            self.last_elapsed_time = res['elapsed']
        else:
            self.last_elapsed_time = None
        if 'error' in res:
            raise errors.SearchClientError(res['error'], res.get('type', 'Search error'))
            
        return res

    def search(self, query, start_rank=None, end_rank=None, db_name=None):
        """Perform a search.

         - `query`: A Query object, containing the query to perform.
         - `start_rank`: The start rank; defaults to the server default (usually 0).
         - `end_rank`: The end rank; defaults to the server default (usually 10).

        FIXME: document return type - perhaps wrap in an object

        """
        if db_name is None:
            db_name = self.default_db_name
        if db_name is None:
            raise Invalid('Missing db_name')

        req = {
            'q': simplejson.dumps(query.to_params()),
            'start_rank': start_rank,
            'end_rank': end_rank,
        }

        return self._doreq('search/' + db_name, qs=req)

    def listdbs(self):
        """Get a list of the available databases.

        Returns a list of strings, representing the database names.

        """
        res = self._doreq('listdbs')
        return res['db_names']

    def newdb(self, fields, db_name=None):
        """Create a new database.
        
        Returns an error if the database already exists.

         - `fields` is a list of parameters for the database configuration.
           Each item in the list is a dictionary containing details about the
           configuration for that field in xappy.  The field_name specified in
           each dictionary must be unique (ie, can't appear in multiple entries
           in the list).

        The dictionaries contain the following:

        {
            'field_name': # field name (required)
            'type':  # One of 'text', 'date', 'geo', 'float' (default=text)
            'store': # boolean (default=False), whether to store in document data (for 'display')
            'spelling_word_source': # boolean (default=False), whether to use for building the spelling dictionary
            'collapsible': # boolean (default=False), whether to use for collapsing
            'sortable': # boolean (default=False), whether to allow sorting on the field
            'range_searchable': # boolean (default=False), whether to allow range searches on the field
            'is_document_weight': # boolean (default=False), whether the field value can be used for document weighting

            'noindex': # boolean (default=False), if True, don't index, but still support above options.

            'freetext': {
                # If present (even if empty), or if field type is 'text' and no other text indexing option (eg, 'exacttext' or 'noindex') is specified, field is indexed for free text searching
                'language': # string (2 letter ISO lang code) (default None) - if missing, use database default.  If None no language specific stuff is done.  (FIXME - for the moment, the database default is to use no language specific processing).
                'term_frequency_multiplier': # int (default 1) - must be positive or zero - multiplier for term frequency, increases term frequency by the given multipler to increase its weighting
                'enable_phrase_search': # boolean (default True) - whether to allow phrase searches on this field
                'index_groups': [
                    # Index groupings to index this field.  Defaults to containing '_FIELD_INDEX' and '_GENERAL_INDEX'
                    '_FIELD_INDEX': magic value to say to include in a index grouping specific to just this field
                    '_GENERAL_INDEX': index in the general index (used for non-field specific searches by default)
                    # Note - currently (Nov 2008) no other index groups are supported
                ]
            },

            'exacttext': {
                # If present (even if empty), search is indexed for exact text searching
                'index_groups': [
                    # Index groupings to index this field.  Defaults to containing '_FIELD_INDEX'
                    '_FIELD_INDEX': magic value to say to include in a index grouping specific to just this field
                    # Note - currently (Nov 2008) no other index groups are supported
                ]
            },

            # Note - only one of "freetext" and "exact" may be supplied

            'geo': {
                # If present (even if empty), coordinates are stored such that
                # searches can be ordered by distance from a point.
                'enable_bounding_box_search': # boolean (default True) - if True, index such that searches for all items within a bounding box can be retrieved.
                'enable_range_search': # boolean (default True) - if True, index such that searches can be restricted to all items within a range (ie, great circle distance) of a point.
            }
        }

        """
        if db_name is None:
            db_name = self.default_db_name
        if db_name is None:
            raise errors.SearchClientError('Missing db_name')

        req = {
            'db_name': db_name,
            'fields': simplejson.dumps(list(fields)),
        }

        return self._doreq('newdb', data=req)

    def deldb(self, db_name=None):
        """Delete the database.

        """
        if db_name is None:
            db_name = self.default_db_name
        if db_name is None:
            raise errors.SearchClientError('Missing db_name')

        req = {
            'db_name': db_name,
        }

        return self._doreq('deldb', data=req)

    def add(self, doc, db_name=None):
        """Add a document to the database.

        `doc` the document (as a Document object).

        """
        if db_name is None:
            db_name = self.default_db_name
        if db_name is None:
            raise errors.SearchClientError('Missing db_name')

        return self._doreq('add/' + db_name, data={'doc': [doc.as_json()]})

    def bulkadd(self, docs, db_name=None):
        """Add a load of documents tothe database.

        `doc` the document (as a Document object).

        """
        if db_name is None:
            db_name = self.default_db_name
        if db_name is None:
            raise errors.SearchClientError('Missing db_name')

        return self._doreq('add/' + db_name, data={'doc': [doc.as_json() for doc in docs]})
