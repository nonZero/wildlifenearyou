from django import forms
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponseForbidden, \
    Http404, HttpResponse
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django.utils import simplejson

from models import Photo, SuggestedSpecies
from zoo.shortcuts import render
from zoo.trips.models import Trip, Sighting
from zoo.places.models import Place
from zoo.animals.forms import SpeciesField
from zoo.animals.models import Species
from zoo.flickr.models import FlickrSet

import datetime

@login_required
def upload(request, place=None, redirect_to=None):
    raise Http404, 'Photo upload is disabled'
    if request.method == 'POST':
        # Process uploaded photo
        form = UploadPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit = False)
            if place:
                obj.place = place
            # If user has account 7 days or older, or is staff
            # go live straight away
            if request.user.get_profile().is_not_brand_new_account() or \
                request.user.is_staff:
                obj.is_visible = True
            obj.save()
            return HttpResponseRedirect(redirect_to or (
                reverse('accounts-profile', args=(request.user,))
            ))
    else:
        form = UploadPhotoForm()

    return render(request, 'photos/upload.html', {
        'form': form,
        'attach_to': place,
        'limit': settings.FILE_UPLOAD_SIZE_LIMIT,
    })

class UploadPhotoForm(forms.ModelForm):
    class Meta:
        fields = ('title', 'photo')
        model = Photo

@login_required
def upload_trip(request, username, trip_id):
    raise Http404, 'Photo upload is disabled'
    user = get_object_or_404(User, username=username)
    trip = get_object_or_404(Trip, id=trip_id, created_by=user)
    # The user should have got here via a file upload PUSH. If so, we 
    # create the photo straight away and redirect them straight to the edit
    # page.
    if request.method == 'POST':
        form = PhotoOnlyForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit = False)
            photo.trip = trip
            # Set the title to the filename, if provided
            photo.title = form.cleaned_data['photo'].name
            # If user has account 7 days or older, or is staff
            # go live straight away
            if request.user.get_profile().is_not_brand_new_account() or \
                request.user.is_staff:
                photo.is_visible = True
            photo.save()
            # Redirect them straight to the edit page for that photo
            return HttpResponseRedirect(photo.get_absolute_url() + 'edit/')

    form = PhotoOnlyForm()
    return render(request, 'photos/single_upload.html', {
        'form': form,
        'action': request.path,
        'limit': settings.FILE_UPLOAD_SIZE_LIMIT,
    })

class PhotoOnlyForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ('photo')

@login_required
def edit_photo(request, username, photo_id):
    """
    We force people to assign a photo to a place before they can add any 
    animals. This is so animals in the photo can be represented using 
    sightings attached to that trip. That way we can offer people the list of
    species from the trip for that photo, and if they add a different 
    """
    if username != request.user.username:
        return HttpResponseForbidden('Not your photo')
    photo = get_object_or_404(Photo, id=photo_id, created_by=request.user)
    if request.method == 'POST':
        form = PhotoEditForm(request.user, request.POST)
        if form.is_valid():
            trip_has_changed = (photo.trip != form.cleaned_data['trip'])
            old_trip = photo.trip
            
            photo.title = form.cleaned_data['title']
            
            if trip_has_changed:
                photo.trip = form.cleaned_data['trip']
                photo.flickr_needs_geotagging = True
            
            photo.save()
            
            # If the user changed the trip AND that photo has sightings 
            # associated with it, we need to create new sightings for those 
            # animals attached to the new trip and re-target the photo 
            # relationships to point at those new sightings instead. We'll 
            # leave the old sightings where they are - the user can delete 
            # them later if they want to.
            if trip_has_changed:
                sightings = list(photo.sightings.all())
                # Clear out those relationships (does not delete sightings)
                photo.sightings.clear()
                for sighting in sightings:
                    # Ensure a sighting for that species exists for new trip
                    kwargs = {'trip': photo.trip}
                    if sighting.species:
                        kwargs['species'] = sighting.species
                    else:
                        kwargs['species_inexact'] = sighting.species_inexact
                    matching_sightings = Sighting.objects.filter(**kwargs)
                    if matching_sightings:
                        # Attach the photo to the first of those matches
                        photo.sightings.add(matching_sightings[0])
                    else:
                        # Create a new sighting for that species on that place
                        del kwargs['trip'] # re-using kwargs from earlier
                        kwargs['place'] = photo.trip.place
                        photo.sightings.create(**kwargs)
                photo.flickr_needs_tagging = True
                photo.flickr_needs_geotagging = True
                photo.save()
            
            return HttpResponseRedirect(photo.get_absolute_url())
    else:
        form = PhotoEditForm(request.user, instance=photo)
    return render(request, 'photos/edit.html', {
        'form': form,
        'photo': photo,
    })

@login_required
def delete_photo(request, username, photo_id):
    user = get_object_or_404(User, username=username)
    photo = get_object_or_404(Photo, id=photo_id, created_by=user)
    assert request.user.id == user.id, "You can only delete your own trips!"
    if request.POST.get('confirm_delete'):
        # Delete the photo
        trip = photo.trip
        photo.delete()
        if trip:
            trip.save() # Re-index to update denormalised stuff
        
        return HttpResponseRedirect(
            reverse('accounts-profile', args=(username,))
        )
    
    return render(request, 'photos/delete.html', {
        'photo': photo,
    })


@login_required
def set_species(request, username, photo_id):
    from zoo.trips.models import Sighting
    if username != request.user.username:
        return HttpResponseForbidden()
    # Should be POSTed to with a list of 'saw' values
    photo = get_object_or_404(Photo, id=photo_id, created_by=request.user)
    assert photo.trip, \
        "A photo should have a trip if you're trying to add sightings to it"
    
    photo_needs_tagging = False
    # The sightings should already exist on that trip, just hook up the photo
    for id in request.POST.getlist('saw'):
        #print "Processing species ID %s" % id
        # Silently discard IDs that do not correspond with sightings
        try:
            sighting = photo.trip.sightings.filter(pk = id)[0]
            #print "  Found sighting %s" % sighting
        except IndexError:
            #print "  Could not find matching sighting"
            continue
        assert request.user == sighting.created_by
        photo.sightings.add(sighting)
        photo_needs_tagging = True
    
    if photo_needs_tagging:
        photo.flickr_needs_tagging = True
        photo.save()
    
    return HttpResponseRedirect(photo.get_absolute_url())

@login_required
def set_has_no_species(request, username, photo_id):
    from zoo.trips.models import Sighting
    if username != request.user.username:
        return HttpResponseForbidden()
    photo = get_object_or_404(
        Photo, created_by__username=username, pk=photo_id
    )
    if 'set_has_no_species' in request.POST:
        photo.has_no_species = True
        photo.save()
    if 'unset_has_no_species' in request.POST:
        photo.has_no_species = False
        photo.save()
    return HttpResponseRedirect(photo.get_absolute_url())

from trips.add_trip import species_for_freebase_details
from trips import add_trip_utils

@login_required
def add_species(request, username, photo_id):
    from zoo.trips.models import Sighting
    photo = get_object_or_404(
        Photo, created_by__username=username, pk=photo_id
    )
    
    if photo.created_by != request.user:
        return HttpResponseForbidden()
    
    if not photo.trip:
        return HttpResponse(
            'Photo must be assigned to a trip before you can add any species'
        )
    
    guid = request.POST.get('guid', None)
    if guid:
        # Create species page for that animal
        selected_details = add_trip_utils.bulk_lookup(
            [guid.replace('#', '/guid/')]
        )
        if len(selected_details) == 1:
            # Now save the selected and unknown sightings
            species = species_for_freebase_details(selected_details[0])
            sighting, created = photo.trip.sightings.get_or_create(
                species = species,
                defaults = {
                    'place': photo.trip.place,
                    'note': ''
                }
            )
            photo.sightings.add(sighting)
            photo.flickr_needs_tagging = True
            photo.save()
            return HttpResponseRedirect(photo.get_absolute_url())
    
    add_unknown_text = request.POST.get('add_unknown_text', '').strip()
    if add_unknown_text:
        sighting, created = photo.trip.sightings.get_or_create(
            species_inexact = add_unknown_text,
            defaults = {
                'place': photo.trip.place,
                'note': ''
            }
        )
        photo.sightings.add(sighting)
        photo.flickr_needs_tagging = True
        photo.save()
        return HttpResponseRedirect(photo.get_absolute_url())
    
    # If we get here, we need to show search results for the 'species' string
    # normally this means the user doesn't have JavaScript enabled
    species_q = request.REQUEST.get('species', '')
    results = []
    if species_q:
        results = add_trip_utils.search(
            species_q, limit=10, place=photo.trip.place
        )[:5]
    
    return render(request, 'photos/add_species.html', {
        'photo': photo,
        'species_q': species_q,
        'results': results,
    })

@login_required
def suggest_species(request, username, photo_id):
    from zoo.trips.models import Sighting
    photo = get_object_or_404(
        Photo, created_by__username=username, pk=photo_id
    )
    
    note = request.POST.get('note', '').strip()
    
    guid = request.POST.get('guid', None)
    
    if not guid:
        # Do we have an add_species_%s style guid?
        for key in request.POST:
            if key.startswith('add_selected_'):
                guid = key.replace('add_selected_', '').split('.')[0]
                break
    
    if guid:
        # Create species page for that animal
        selected_details = add_trip_utils.bulk_lookup(
            [guid.replace('#', '/guid/')]
        )
        if len(selected_details) == 1:
            # Now save the selected and unknown sightings
            species = species_for_freebase_details(selected_details[0])
            photo.suggestions.create(
                species = species,
                suggested_by = request.user,
                suggested_at = datetime.datetime.now(),
                denorm_suggestion_for = photo.created_by,
                note = note,
            )
            return HttpResponseRedirect(photo.get_absolute_url())

    add_unknown_text = request.POST.get('add_unknown_text', '').strip()
    if 'add_unknown.x' in request.POST and add_unknown_text:
        photo.suggestions.create(
            species_inexact = add_unknown_text,
            suggested_by = request.user,
            suggested_at = datetime.datetime.now(),
            denorm_suggestion_for = photo.created_by,
            note = note,
        )
        return HttpResponseRedirect(photo.get_absolute_url())

    # If we get here, we need to show search results for the 'species' string
    # normally this means the user doesn't have JavaScript enabled
    species_q = request.REQUEST.get('species', '')
    results = []
    if species_q:
        kwargs = {
            'limit': 10,
        }
        if photo.trip:
            kwargs['place'] = photo.trip.place
        results = add_trip_utils.search(species_q, **kwargs)[:5]

    return render(request, 'photos/suggest_species.html', {
        'photo': photo,
        'species_q': species_q,
        'note': note,
        'results': results,
    })

@login_required
def remove_species(request, username, photo_id, sighting_id):
    from zoo.trips.models import Sighting
    photo = get_object_or_404(
        Photo, created_by__username=username, pk=photo_id
    )
    if photo.created_by != request.user:
        return HttpResponseForbidden()
    sighting = get_object_or_404(
        Sighting, created_by = request.user, trip = photo.trip,
        pk = sighting_id
    )
    if request.method == 'POST':
        photo.sightings.remove(sighting)
        return HttpResponseRedirect(photo.get_absolute_url())
    
    return render(request, 'photos/remove_species.html', {
        'photo': photo,
        'sighting': sighting,
        'request_path': request.path,
    })

@login_required
def suggestions(request, username):
    if username != request.user.username:
        return HttpResponseForbidden()
    return render(request, 'photos/suggestions.html', {
        'suggestions': SuggestedSpecies.objects.filter(
            denorm_suggestion_for = request.user,
            status = 'new'
        ).select_related('photo').order_by('-suggested_at'),
        'username': username,
    })

@login_required
def process_suggestion(request, username, suggestion_id):
    if username != request.user.username:
        return HttpResponseForbidden()
    suggestion = get_object_or_404(SuggestedSpecies,
        denorm_suggestion_for__username = username,
        pk = suggestion_id
    )
    if 'approve' in request.POST:
        suggestion.approve()
    elif 'reject' in request.POST:
        suggestion.reject()
    
    next = request.POST.get('next', '')
    
    if next and next.startswith('/'):
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect('/%s/photos/suggestions/' % username)

class PhotoEditForm(forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super(PhotoEditForm, self).__init__(*args, **kwargs)
        self.fields['trip'].queryset = Trip.objects.filter(created_by=user)

    class Meta:
        model = Photo
        fields = ('title', 'trip')

def photo(request, username, photo_id):
    photo = get_object_or_404(
        Photo, created_by__username=username, pk=photo_id
    )
    
    def conv(items):
        return dict([(item.replace('/guid/', '#'), 1) for item in items])
    
    seen_at_this_place = []
    seen_on_trip = []
    if photo.trip:
        seen_on_trip = conv(photo.trip.species.values_list(
            'freebase_id', flat=True
        ))
        seen_at_this_place = conv(Species.objects.filter(
            sightings__place = photo.trip.place
        ).values_list('freebase_id', flat = True).distinct())
    
    # What species are in this photo? Use them to calculate awards
    awards = []
    for species in Species.objects.filter(sightings__photos=photo).distinct():
        top_3 = species.top_3_photo_ids()[:3]
        for i, id in enumerate(top_3):
            if id == photo.pk:
                description, icon = {
                    0: ('best', 'gold'),
                    1: ('2nd best', 'silver'),
                    2: ('3rd best', 'bronze'),
                }.get(i)
                awards.append({
                    'description': description,
                    'icon': icon,
                    'species': species,
                })
    
    return render(request, 'photos/photo.html', {
        'photo': photo,
        'favourited': photo.is_favourited_by(request.user),
        'seen_at_this_place': simplejson.dumps(seen_at_this_place),
        'seen_on_trip': simplejson.dumps(seen_on_trip),
        'current_user_is_not_page_owner': request.user != photo.created_by,
        'sightings': photo.sightings.all(),
        'awards': awards,
    })

def photo_fans(request, username, photo_id):
    photo = get_object_or_404(
        Photo, created_by__username=username, pk=photo_id
    )
    return render(request, 'photos/fans.html', {
        'photo': photo,
        'fans': User.objects.filter(
            favourite_photos__photo = photo
        )
    })

def all(request):
    return render(request, 'photos/all.html', {
        'photos': Photo.objects.all().order_by('created_at'),
    })

def user_photos(request, username):
    user = get_object_or_404(User, username = username)
    return render(request, 'photos/user_photos.html', {
        'profile': user.get_profile(),
        'photos': filter_visible_photos(user.photos, request.user),
    })

def user_favourite_photos(request, username):
    user = get_object_or_404(User, username = username)
    return render(request, 'photos/user_favourite_photos.html', {
        'profile': user.get_profile(),
        'faves': user.favourite_photos.all(),
    })

def user_photos_by_trip(request, username):
    user = get_object_or_404(User, username = username)
    trips = []
    photos_to_display_per_trip = 5
    for trip in Trip.objects.filter(
            created_by = user, photos__isnull = False
        ).distinct().order_by('-start'):
        photos = filter_visible_photos(
            trip.photos, request.user
        )
        photo_count = photos.count()
        trips.append({
            'trip': trip,
            'visible_photos': photos[:photos_to_display_per_trip],
            'more_photos': max(photo_count - photos_to_display_per_trip, 0),
        })
    
    return render(request, 'photos/user_photos_by_trip.html', {
        'profile': user.get_profile(),
        'trips': trips,
    })

def user_photos_unassigned(request, username):
    user = get_object_or_404(User, username = username)
    if request.user == user:
        return user_photos_bulk_assign(request, user)
    
    return render(request, 'photos/user_photos_unassigned.html', {
        'profile': user.get_profile(),
        'photos': filter_visible_photos(
            photos = Photo.objects.filter(
                created_by = user, trip__isnull=True
            ).order_by('created_at').distinct(),
            user = request.user
        )
    })

def user_photos_unassigned_flickr_sets(request, username):
    user = get_object_or_404(User, username = username)
    # Need FlickrSets containing photos that have not yet been assigned a trip
    sets = FlickrSet.objects.filter(
        user = request.user,
        photos__trip__isnull = True
    ).distinct()
    for set in sets:
        set.num_unassigned = set.photos.filter(trip__isnull = True).count()
    
    return render(request, 'photos/user_photos_unassigned_flickr_sets.html', {
        'profile': user.get_profile(),
        'sets': sets,
    })

def user_photos_unassigned_by_flickr_set(request, username, set_id):
    flickr_set = get_object_or_404(FlickrSet,
        user__username = username,
        flickr_id = set_id
    )
    return user_photos_bulk_assign(request, flickr_set.user, flickr_set)

def user_photos_nospecies(request, username):
    user = get_object_or_404(User, username = username)
    return render(request, 'photos/user_photos_nospecies.html', {
        'profile': user.get_profile(),
        'photos': filter_visible_photos(
            photos = Photo.objects.filter(
                created_by = user,
                sightings__isnull = True
            ).exclude(has_no_species = True).order_by('created_at'),
            user = request.user
        )
    })

@login_required
def user_photos_bulk_assign(request, user, flickr_set=None):
    assert user == request.user
    if flickr_set:
        photos = flickr_set.photos.filter(trip__isnull = True)
    else:
        photos = Photo.objects.filter(
            created_by = user, trip__isnull=True
        ).order_by('created_at').distinct()
    
    if 'ids' in request.GET:
        photos = photos.filter(pk__in = request.GET.get('ids', '').split(','))
    
    they_forgot_to_select_some_photos = False
    they_forgot_to_select_a_trip = False
    
    if request.method == 'POST':
        photo_ids = request.POST.getlist('selected_photos')
        trip_id = request.POST.get('trip')
        if not photo_ids or not trip_id:
            if not photo_ids:
                they_forgot_to_select_some_photos = True
            elif not trip_id:
                they_forgot_to_select_a_trip = True
        else:
            
            photos = Photo.objects.filter(id__in = photo_ids).filter(
                created_by = request.user
            )
            trip = get_object_or_404(
                Trip, pk=trip_id, created_by=request.user
            )
            # Assign the photos to that trip
            for p in photos:
                p.trip = trip
                p.flickr_needs_geotagging = True
                p.save()
            # Force a re-index of trip
            trip.save()
            # Redirect to that trip's page (TODO: trip's photo page instead)
            return HttpResponseRedirect(trip.get_absolute_url())
    
    return render(request, 'photos/user_photos_bulk_assign.html', {
        'profile': user.get_profile(),
        'photos': photos,
        'flickr_set': flickr_set,
        'trip_count': Trip.objects.filter(created_by=user).count(),
        'they_forgot_to_select_some_photos': they_forgot_to_select_some_photos,
        'they_forgot_to_select_a_trip': they_forgot_to_select_a_trip,
        'form': TripSelectForm(user)
    })

class TripSelectForm(forms.Form):
    trip = forms.ModelChoiceField(Trip)
    def __init__(self, user, *args, **kwargs):
        super(TripSelectForm, self).__init__(*args, **kwargs)
        self.fields['trip'].queryset = Trip.objects.filter(created_by=user)

@login_required
def moderate(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()
        
    if request.method == 'POST':
        for k in request.POST.keys():            
            if k[:6]=='photo-':
                v = request.POST[k]
                if v=='0':
                    continue
                ppk = int(k[6:])
                photo = Photo.objects.get(pk=ppk)
                photo.moderated_by = request.user
                photo.moderated_at = datetime.datetime.now()
                if v=='2':
                    photo.is_visible = True
                photo.save()
        return HttpResponseRedirect(reverse('moderate-photos'))
    else:
        photos = Photo.objects.filter(
            is_visible=False).filter(moderated_by=None
        )
        return render(request, 'photos/moderate.html', {
            'photos': photos[:10],
            'total': photos.count()
        })

def filter_visible_photos(photos, user):
    "photos is a QuerySet of photos, user is the user who wants to view them"
    if not user.is_anonymous:
        return photos.filter(
            Q(is_visible = True) | Q(created_by = user)
        ).distinct()
    else:
        return photos.filter(is_visible = True)
