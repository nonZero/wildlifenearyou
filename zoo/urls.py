from django.conf.urls.defaults import *
from django.conf import settings

import os

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^zoo/', include('zoo.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': os.path.join(settings.OUR_ROOT, 'static')
    }),
    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
)
