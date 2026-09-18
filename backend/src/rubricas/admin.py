from django.contrib import admin

from rubricas.models import Criterio, Nivel, Rubrica, VersaoRubrica


class NivelInline(admin.TabularInline):
    model = Nivel
    extra = 0


@admin.register(Criterio)
class CriterioAdmin(admin.ModelAdmin):
    list_display = ("nome", "versao", "ordem", "tipo", "peso")
    list_filter = ("tipo",)
    inlines = [NivelInline]


class VersaoInline(admin.TabularInline):
    model = VersaoRubrica
    extra = 0
    fields = ("numero", "congelada", "hash")
    readonly_fields = fields


@admin.register(Rubrica)
class RubricaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "dono", "criado_em")
    search_fields = ("titulo",)
    inlines = [VersaoInline]
