from django.contrib import admin
from zoo.animals.models import Species, SpeciesGroup, SuperSpecies

excludees = ['created_at', 'created_by', 'modified_at', 'modified_by']

admin.site.register(Species,
    list_display = ('common_name', 'species_group', 'latin_name', 'slug'),
    list_filter = ['species_group'],
    search_fields = ['common_name', 'latin_name'],
    prepopulated_fields = {'slug': ('common_name',)},
    exclude = excludees,
)
admin.site.register(SpeciesGroup)
admin.site.register(SuperSpecies,
    exclude = excludees,
    prepopulated_fields = {'slug': ('common_name',)},
)
