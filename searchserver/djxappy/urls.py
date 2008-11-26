from django.conf.urls.defaults import *
from django.conf import settings
import os

urlpatterns = patterns('',
    # Example:
    # (r'^djxappy/', include('djxappy.apps.foo.urls.foo')),

    # Uncomment this for admin:
#     (r'^admin/', include('django.contrib.admin.urls')),

    # Searching
    ('^' + settings.BASEURL + r'search/(?P<db_name>\w+)', "search.search"),
    ('^' + settings.BASEURL + r'get/(?P<db_name>\w+)', "search.get"),

    # Database admin stuff
    ('^' + settings.BASEURL + r'listdbs', "search.listdbs"),
    ('^' + settings.BASEURL + r'newdb', "search.newdb"),
    ('^' + settings.BASEURL + r'deldb', "search.deldb"),

    # Adding documents
    ('^' + settings.BASEURL + r'add/(?P<db_name>\w+)', "search.add"),
    ('^' + settings.BASEURL + r'bulkadd/(?P<db_name>\w+)', "search.bulkadd"),
    
    # API explorer
    ('^' + settings.BASEURL + r'api-explorer/(?P<path>.*)$', 
        'django.views.static.serve', {
            'document_root': os.path.join(
                os.path.dirname(__file__), 'api-explorer'
            )
        },
    ),
)
