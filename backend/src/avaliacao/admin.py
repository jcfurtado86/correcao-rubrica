from django.contrib import admin

from avaliacao.models import Execucao, Rodada, Trecho


class SoLeitura(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Rodada)
class RodadaAdmin(SoLeitura):
    list_display = (
        "lote",
        "numero",
        "status",
        "modelo",
        "custo_estimado_usd",
        "custo_acumulado_usd",
    )
    list_filter = ("status", "modelo")


class TrechoInline(admin.TabularInline):
    model = Trecho
    extra = 0
    readonly_fields = ("texto_citado", "localizado", "inicio", "fim")
    can_delete = False


@admin.register(Execucao)
class ExecucaoAdmin(SoLeitura):
    list_display = (
        "resposta",
        "criterio",
        "indice",
        "status",
        "valida",
        "nivel_codigo",
        "motivo_invalidez",
    )
    list_filter = ("rodada", "status", "valida", "motivo_invalidez")
    inlines = [TrechoInline]
