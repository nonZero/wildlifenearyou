from zoo.configs.common_settings import *

# Debug settings - turn OFF before launch
DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Database settings
DATABASE_NAME = 'zoo_alpha'
DATABASE_USER = 'zoo_alpha'

CACHE_BACKEND = "memcached://127.0.0.1:11211/?timeout=900000"

# Xapian settings
SEARCH_ENABLED = True
XAPIAN_BASE_URL = 'http://localhost:9876/search/'
XAPIAN_PERSONAL_PREFIX = 'zoo_alpha'
XAPIAN_LOCATION_DB = '%s_locations' % XAPIAN_PERSONAL_PREFIX
XAPIAN_SPECIES_DB = '%s_species' % XAPIAN_PERSONAL_PREFIX

MEDIA_ROOT = '/srv/django-apps/staging.wildlifenearyou.com/media_root'

# SMTP settings
DEFAULT_FROM_EMAIL = 'simon@simonwillison.net'
EMAIL_FROM = DEFAULT_FROM_EMAIL
EMAIL_HOST = 'mail.authsmtp.com'
EMAIL_HOST_USER = 'ac35086'
EMAIL_HOST_PASSWORD = 'xzaf8gbxm'

# Prelaunch middleware
#PRELAUNCH_PASSWORD = 'tigers'
#if PRELAUNCH_PASSWORD:
#    MIDDLEWARE_CLASSES += [
#        'zoo.common.prelaunch_middleware.PreLaunchMiddleware',
#    ]

# API Keys
GOOGLE_MAPS_API_KEY = "ABQIAAAAyYu8a7AdbfUctK3zwwu_2hTeEhs7wu9zhsOzHk9LZpRUpK5uYhQyDGy2GVb-GNB0915UX7cG33kJSw"
FLICKR_API_KEY = '9b42140530b4e1d535adc4b5992bd879'
FLICKR_API_SECRET = '19db0ec3fb0c4e69'

# Dev status bar HTML
DEV_STATUS_HTML = ''
#DEV_STATUS_HTML = """
#<div class="dev-status alpha">
# <p>This is still an <strong>alpha</strong> site - please don't link to or Twitter this yet, we're fixing up some loose ends</p>
#</div>
#"""

GOOGLE_ANALYTICS_CODE = """
<script type="text/javascript">
var _gaq = _gaq || [];
_gaq.push(['_setAccount', 'UA-12396673-1']);
_gaq.push(['_trackPageview']);
_gaq.push(['t2._setAccount', 'UA-6697903-1']); // James
_gaq.push(['t2._trackPageview']);
(function() {
var ga = document.createElement('script');
ga.src = ('https:' == document.location.protocol ?
    'https://ssl' : 'http://www') +
    '.google-analytics.com/ga.js';
ga.setAttribute('async', 'true');
document.documentElement.firstChild.appendChild(ga);
})();</script>
"""

HTTP_PORT = 80
