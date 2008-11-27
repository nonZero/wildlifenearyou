from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect as Redirect
from django.contrib.auth.decorators import login_required

from zoo.shortcuts import render
from zoo.trips.models import Trip
from zoo.accounts.models import Profile
from zoo.animals.forms import SpeciesField

from zoo.search import NotFound, lookup_species, search_species
from django import forms

@login_required
def tripbook_default(request):
    return Redirect(reverse('tripbook', args=(request.user,)))

def tripbook(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'trips/tripbook.html', {
        'tripbook': user.created_trip_set.all(),
        'profile': user.get_profile(),
    })

def trip_edit(request, username):
    pass

@login_required
def trip_add(request, username):
    user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        form = AddTripForm(request.POST)
        if form.is_valid():
            trip = form.save()
            return Redirect(reverse('trip-view', args=(trip.id,)))
    else:
        form = AddTripForm()
    
    return render(request, 'trips/add_trip.html', {
        'profile': user.get_profile(),
        'form': form,
    })
    
def trip_view(request, username, trip_id):
    user = get_object_or_404(User, username=username)
    trip = get_object_or_404(Trip, id=trip_id)
    return render(request, 'trips/trip.html', {
        'profile': user.get_profile(),
        'trip': trip,
    })

    
from django import forms

class AddTripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ('name', 'description', 'start', 'end')

    def save(self):
        trip = super(AddTripForm, self).save(commit=False)
        trip.save()
        Trips.objects.create(trip=trip)
        return trip

from zoo.places.models import Place, Country
from zoo.animals.models import Species

import re
saw_key_re = re.compile('^saw_\d+$')
saw_id_key_re = re.compile('^saw_id_\d+$')
saw_selection_key_re = re.compile('^saw_selection_\d+$')


@login_required
def add_sightings(request, country_code, slug):
    country = get_object_or_404(Country, country_code=country_code)
    place = get_object_or_404(Place, slug=slug, country=country)
    # request.POST will contain:
    #   saw_1, saw_2, ... = text strings the user said they saw
    #   saw_id_1, saw_id_2, ... = IDs of things we have resolved
    #   saw_selection_1, ... = IDs of things they have picked from our UI
    # 
    # Our aim is to change all of the saw_%s in to saw_id_%s
    # 
    # Every round-trip to the server that results in a saw_section will remove
    # an item from the saw_% list and add an item to the saw_id_% list
    # 
    # Just keep on looping around until they've got them all right, or 
    # they've given up on some of the ones that don't have any matches.
    # 
    # The IDs in saw_selection_% come in two forms - s% and x%
    #   s% means "this is a Species object ID (in our local db table)"
    #   x% means "this is a Xapian ID" (in our Xapian index)
    # 
    # When we finally submit, any x% ids will result in an insert in to our 
    # species table since they will represent animals that we don't officially
    # know anything about yet.
    
    # The collection of verified sighted species IDs
    saw_id_set = set(
        value for key, value in request.POST.items()
        if saw_id_key_re.match(key)
    )
    
    # Text items we haven't resolved yet
    saw_dict = dict([
        (int(key.replace('saw_', '')), value)
        for key, value in request.POST.items()
        if saw_key_re.match(key) and value.strip()
    ])
    
    # Selections for those (IDs should match IDs in the saw dict above)
    saw_selection_dict = dict([
        (int(key.replace('saw_selection_', '')), value)
        for key, value in request.POST.items()
        if saw_selection_key_re.match(key)
    ])
    
    # Now remove animals from saw_dict if we have flagged them as 
    # "maybe I didn't see X" by putting an empty value in saw_selection_dict
    for key, value in saw_selection_dict.items():
        if not value:
            del saw_dict[key]
    
    # If we just have saw_ids, we can get right on with adding the sightings
    if saw_id_set and not saw_dict:
        return Redirect(
            request.path + ('-'.join(saw_id_set)) + '/'
        )
        #return finish_add_sightings(request, place, saw_id_set)
    
    # If there's a saw_dict and they've picked an option for everything on it 
    # as represented in saw_selection_dict, we should sanity check each of 
    # their selections and then add the sightings
    #
    # We track which ones have been successfully looked up by removing them 
    # from saw_dict and adding them to the saw_id_set. If saw_dict is 
    # empty at the end then we've got them all!
    if saw_dict and saw_selection_dict:
        # They've picked some things
        
        # We'll iterate over IDs that are present in both dictionaries
        keys = [key for key in saw_dict if key in saw_selection_dict]
        
        for key in keys:
            string = saw_dict[key]
            selected_id = saw_selection_dict[key]
            
            # Look up selected_id
            if selected_id.startswith('x'):
                x_id = selected_id[1:]
                # Look it up in Xapian
                try:
                    doc = lookup_species(x_id)
                    saw_id_set.add(selected_id)
                    del saw_dict[key] # remove from saw_list
                except NotFound:
                    # This will only happen if a Xapian re-index occurs in 
                    # between the user loading and submitting the form - 
                    # so just ignore that key for the moment
                    del saw_selection_dict[key]
                    continue
            elif selected_id.startswith('s'):
                dj_id = selected_id.replace[1:]
                try:
                    species = Species.object.get(pk = dj_id)
                except Species.DoesNotExist:
                    found_them_all = False
                    continue
                saw_id_set.add(selected_id)
                del saw_dict[key] # remove from saw_list
            else:
                # Someone has been messing around with form vars - ignore
                continue
        if not saw_dict:
            return Redirect(
                request.path + ('-'.join(saw_id_set)) + '/'
            )

    
    # If we get here, there are at least some "saw" text entries that need to 
    # be disambiguated. Show a form.
    form = forms.Form()
    for key, string in saw_dict.items():
        if not string.strip():
            continue
        results = search_species(string)
        if not results:
            continue
        form.fields['saw_selection_%s' % key] = forms.ChoiceField(
            choices = [((
                    r.get('django_id') and 's%s' % r['django_id'] 
                    or ('x%s' % r['search_id'])
                ), u'%s (%s)' % (r['common_name'], r['scientific_name']))
                for r in results
            ] + [('', "Actually I didn't see a \"%s\"" % string)],
            widget = forms.RadioSelect
        )
    
    # Assemble the hidden variables
    hiddens = [
        {'name': 'saw_%s' % key, 'value': value}
        for key, value in saw_dict.items()
    ]
    # Add existing saw_ids in as more hidden form fields
    for i, saw_id in enumerate(saw_id_set):
        hiddens.append(
            {'name': 'saw_%s' % i, 'value': saw_id}
        )
    
    return render(request, 'trips/which-did-you-mean.html', {
        'form': form,
        'hiddens': hiddens,
        'saw_id_set': repr(saw_id_set),
        'saw_selection_dict': repr(saw_selection_dict),
        'saw_dict': repr(saw_dict),
    })

def finish_add_sightings(request, country_code, slug, ids):
    """
    At this point, the user has told us exactly what they saw. We're going to
    add those as sightings, but first, let's see if we can get them to add 
    a full trip (which has a date or a title or both, and a optional 
    description for their tripbook).
    """
    country = get_object_or_404(Country, country_code=country_code)
    place = get_object_or_404(Place, slug=slug, country=country)
    saw_id_set = ids.split('-')
    hiddens = []
    for i, saw_id in enumerate(saw_id_set):
        hiddens.append(
            {'name': 'saw_%s' % i, 'value': saw_id}
        )
    
    if request.method == 'POST':
        if request.POST.get('just-sightings'):
            assert False, "Just save the sightings from saw_%"
        
        
        form = FinishAddSightingsForm(request.POST)
        if form.is_valid():
            trip = Trip(
                name = form.cleaned_data['name'],
                start = form.cleaned_data['start'],
                start_accuracy = 'day', # TODO: figure this out properly
                description = form.cleaned_data['description']
            )
            trip.save()
            # created_by should happen automatically
            
            # Now we finally add the sightings!
            for id in saw_id_set:
                # Look up the id
                species = lookup_xapian_or_django_id(id)
                if species: # None if it was somehow invalid
                    trip.sightings.create(
                        species = species,
                        place = place,
                    )
                
                # TODO: Shouldn't allow a trip to be added if no valid 
                # sightings
            
            return Redirect(trip.get_absolute_url())
        
    else:
        # We pre-populate the name
        if not request.user.first_name:
            whos_trip = 'My'
        else:
            whos_trip = request.user.first_name
            if whos_trip.endswith('s'):
                whos_trip += "'"
            else:
                whos_trip += "'s"
        whos_trip += ' trip to %s' % place
        form = FinishAddSightingsForm(initial = {'name': whos_trip})
    
    return render(request, 'trips/why-not-add-to-you-tripbook.html', {
        'hiddens': hiddens,
        'place': place,
        'form': form,
    })

class FinishAddSightingsForm(forms.Form):
    name = forms.CharField(max_length=100, label='Trip title')
    start = forms.DateField(required = False, label='Trip date')
    description = forms.CharField(required = False, widget=forms.Textarea,
        label='Notes'
    )

def lookup_xapian_or_django_id(id):
    if id.startswith('s'):
        id = id[1:]
        try:
            return Species.object.get(pk = id)
        except Species.DoesNotExist:
            return None
    elif id.startswith('x'):
        id = id[1:]
        # Look it up in Xapian
        try:
            details = lookup_species(id)
        except NotFound:
            return None
        # If it's a Django object already, return that
        django_id = details.get('django_id')
        if django_id:
            return Species.objects.get(pk = django_id)
        else:
            # Save it to the database
            obj, created = Species.objects.get_or_create(
                slug = details['common_name'].replace(' ', '-').lower(),
                common_name = details['common_name'],
                latin_name = details['scientific_name'],
            )
            # TODO IMPORTANT: Update Xapian with ID of our new model object
            # put it in the django_id field for that search record
            return obj
    else:
        return None
    