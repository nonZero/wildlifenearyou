import datetime

from django.db import models
from django.template.defaultfilters import pluralize

from zoo.animals.models import Animal
from zoo.utils import attrproperty

class Country(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)
    country_code = models.CharField(max_length=2, null=False, blank=False, unique=True)
    
    class Meta:
        verbose_name_plural = 'countries'
    
    def __unicode__(self):
        return '%s (%s)' % (self.name, self.country_code,)

class Place(models.Model):
    legal_name = models.CharField(max_length=500, null=False, blank=False)
    known_as = models.CharField(max_length=500, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False,    
        unique=True
    )
    country = models.ForeignKey(Country, null=False, blank=False)

    created_at = models.DateTimeField(null=False, blank=False)
    modified_at = models.DateTimeField(null=False, blank=False)
    
    # Address
    address_line_1 = models.CharField(max_length=250, null=True, blank=True)
    address_line_2 = models.CharField(max_length=250,  null=True, blank=True)
    town = models.CharField(max_length=250, null=True, blank=True)
    state = models.CharField(max_length=250, null=True, blank=True)
    zip = models.CharField(max_length=50, null=True, blank=True)
    
    def address(self):
        bits = []
        for attr in (
            'address_line_1', 'address_line_2', 'town', 'state', 'zip',
            'country'
            ):
            val = unicode(getattr(self, attr, None))
            if val:
                bits.append(val)
        return '\n'.join(bits)
    
    # long and lot for mapping
    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    
    @models.permalink
    def get_absolute_url(self):
        return ('place', (), {
            'country_code': self.country.country_code,
            'slug': self.slug,
        })

    @attrproperty
    def urls(self, name):
        if name == 'absolute':
            return self.get_absolute_url()
    
    def __unicode__(self):
        return '%s, commonly known as %s' % (self.legal_name, self.known_as,)

class Webcam(models.Model):
    place = models.ForeignKey(Place, related_name = 'webcams')
    name = models.CharField(max_length=300, null=True, blank=True)
    url = models.URLField()
    
    def __unicode__(self):
        return self.name

class Enclosure(models.Model):
    place = models.ForeignKey(Place, related_name = 'enclosures')
    animals = models.ManyToManyField(Animal, through='EnclosureAnimal')
    name = models.CharField(max_length=300, null=True, blank=True)

    def __unicode__(self):
        return self.name

class EnclosureAnimal(models.Model):
    enclosure = models.ForeignKey(Enclosure)
    animal = models.ForeignKey(Animal)
    number_of_inhabitants = models.IntegerField(default=0, null=True, blank=True)

    def __unicode__(self):
        retstr = self.animal.common_name
        if self.number_of_inhabitants:
            retstr += ' (%i)' % self.number_of_inhabitants
        if self.enclosure.name:
            retstr += ', %s' % self.enclosure.name
        retstr += ', %s' % self.enclosure.place.known_as
        return retstr