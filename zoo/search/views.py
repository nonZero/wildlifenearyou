from django.conf import settings
from django.http import HttpResponseRedirect as Redirect, HttpResponse, Http404
import re
from pprint import pformat
from djape.client import Query, Client

from zoo.shortcuts import render
from zoo.search import search_places, search_known_species, search_near, \
    search_locations, SEARCH_ALL, search_species, search_users
from zoo.trips.models import Sighting
from zoo.utils import location_from_request

def search_split(request, what, near):
    # First, let us look up the location
    locations = search_locations(near)
    locations = list(locations)
    if locations:
        location_used = locations.pop(0)
        lat, lon = location_used['latlon']
    else:
        location_used = None
        c = Client(settings.XAPIAN_BASE_URL, settings.XAPIAN_PERSONAL_PREFIX)
        result = c.parse_latlong(near)
        if result['ok']:
            lat, lon = result['latitude'], result['longitude']
        else:
            return search_single(
                request, '%s near %s' % (what, near), bypass=True
            )
    
    results, results_info, results_corrected_q = search_places(
        what or SEARCH_ALL, details=True, latlon=(lat, lon), num=20
    )
    species_results, species_results_info, species_results_corrected_q = \
        search_known_species(
            what, details=True, default_op=Query.OP_OR,
    )
    users_results, users_results_info, users_results_corrected_q = \
        search_users(
            what, details=True, default_op=Query.OP_OR,
    )

    for result in results:
        result.species_list = result.get_species()
        for species in result.species_list:
            if species in species_results:
                species.matches_search = True
        # If we got back a distance, bung that on there too
        try:
            result.distance = ([
                d for d in results_info['items'] 
                if d['id'] == 'places.Place:%s' % result.id
            ][0]['geo_distance']['latlon'] / 1609.344)
        except (KeyError, IndexError):
            pass
    
    return render(request, 'search/search_split.html', {
        'what': what,
        'near': near,
        'locations': locations,
        'location_used': location_used,
        'results': results,
        'results_info': pformat(results_info),
        'results_corrected_q': results_corrected_q,
        'species_results': species_results[:5],
        'species_results_info': pformat(species_results_info),
        'species_results_corrected_q': species_results_corrected_q,
        'species_results_more': len(species_results)>5,
        'users_results': users_results,
        'users_results_info': pformat(users_results_info),
        'users_results_corrected_q': users_results_corrected_q,
    })

def search_species(request):
    q = request.GET.get('q', '')

    species_results = None
    species_results_info = None
    species_results_corrected_q = None
    
    if q:
        species_results, species_results_info, species_results_corrected_q = \
            search_known_species(q, details=True, default_op=Query.OP_OR)
            
    return render(request, 'search/search_species.html', {
        'q': q,
        'species_results': species_results,
        'species_results_info': pformat(species_results_info),
        'species_results_corrected_q': species_results_corrected_q,
    })

def search_single(request, q, bypass=False):
    m = re.match('(.*?)\s*(?:near|in)\s+(.*)$', q)
    if m and not bypass:
        return search_split(request, *m.groups())

    results = None
    results_info = None
    results_corrected_q = None
    species_results = None
    species_results_info = None
    species_results_corrected_q = None
    users_results = None
    users_results_info = None
    users_results_corrected_q = None
    location_results = None
    
    if q:
        results, results_info, results_corrected_q = \
            search_places(q, details=True, num=20)
        species_results, species_results_info, species_results_corrected_q = \
            search_known_species(q, details=True, default_op=Query.OP_OR)
        users_results, users_results_info, users_results_corrected_q = \
            search_users(q, details=True, default_op=Query.OP_OR)

        #near_results = search_near('', q)
        location_results = search_locations(q, 3)
        # Annotate results with a special species list that has a flag on 
        # any species which came up in the species results as well
        for result in results:
            result.species_list = result.get_species()
            for species in result.species_list:
                if species in species_results:
                    species.matches_search = True
            # If we got back a distance, bung that on there too
            try:
                result.distance = ([
                    d for d in results_info['items'] 
                    if d['id'] == 'places.Place:%s' % result.id
                ][0]['geo_distance']['latlon'] / 1609.344)
            except (KeyError, IndexError):
                pass
        
    return render(request, 'search/search.html', {
        'q': q,
        'results': results,
        'results_info': pformat(results_info),
        'results_corrected_q': results_corrected_q,
        'species_results': species_results[:5],
        'species_results_info': pformat(species_results_info),
        'species_results_corrected_q': species_results_corrected_q,
        'species_results_more': len(species_results)>5,
        'users_results': users_results,
        'users_results_info': pformat(users_results_info),
        'users_results_corrected_q': users_results_corrected_q,
        'location_results': location_results,
    })

def search(request):
    q = request.GET.get('q', '')
    what = request.GET.get('what', '')
    if what.lower() == 'everything':
        what = ''
    near = request.GET.get('near', '')
    if near.lower() == 'me':
        (current_location, (lat, lon)) = location_from_request(request)
        if current_location:
            near = current_location
    if what and near:
        return search_split(request, what, near)
    elif what:
        return search_single(request, what)
    elif near:
        return search_split(request, '', near)
    else:
        return search_single(request, q)

from zoo.shortcuts import render_json
from zoo.search import search_locations
def location_complete(request):
    q = request.GET.get('q', '')
    results = search_locations(q)
    return render_json(request, list(results))

def place_complete(request):
    q = request.GET.get('q', '')
    return render_json(request, [{
        'id': place.id,
        'name': place.known_as,
        'url': place.urls.absolute,
    } for place in search_places(q)])
