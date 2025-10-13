from django.contrib import admin
from .models import Terreno, Cascina

# Register your models here.


class TerrenoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'superficie', 'cascina')
    list_filter = ('cascina',)
    search_fields = ('nome',)

class CascinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cliente')
    list_filter = ('cliente',)
    search_fields = ('nome',)

admin.site.register(Terreno, TerrenoAdmin)
admin.site.register(Cascina, CascinaAdmin)