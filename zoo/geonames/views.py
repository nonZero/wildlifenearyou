from zoo.shortcuts import render, Redirect, render_json
from utils import search_location

def set_location(request):
    response = Redirect('/')
    location = request.POST.get('location', '')
    if location:
        results = search_location(location)
        if results:
            response.set_cookie(
                'current_location',
                results[0].summary(),
                path = '/',
            )
    return response

def autocomplete(request):
    q = request.GET.get('q')
    results = search_location(q)
    return render_json(request, {
        'results': [{
            'id': r.id,
            'name': r.place_name
        } for r in results]
    })