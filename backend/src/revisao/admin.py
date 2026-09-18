from django.contrib import admin

from revisao.models import Decisao, SessaoCorrecao


class SoLeitura(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SessaoCorrecao)
class SessaoAdmin(SoLeitura):
    list_display = ("resposta", "docente", "condicao", "tempo_ativo_ms", "aberta_em")
    list_filter = ("condicao",)


@admin.register(Decisao)
class DecisaoAdmin(SoLeitura):
    list_display = ("resposta", "criterio", "docente", "nivel", "tipo", "estado_exibido", "vigente")
    list_filter = ("tipo", "estado_exibido", "vigente")
