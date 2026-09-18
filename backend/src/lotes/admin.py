from django.contrib import admin

from lotes.models import Lote, Resposta


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("titulo", "dono", "modelo_llm", "n_execucoes", "limiar_acordo", "sintetico")
    list_filter = ("sintetico", "modelo_llm")


@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "lote", "aviso", "n_substituicoes")
    list_filter = ("aviso", "lote")
    readonly_fields = ("lote", "codigo", "texto", "hash_texto", "n_substituicoes", "aviso")

    def has_add_permission(self, request):
        return False
