from django.contrib import admin

from estudos.models import AlocacaoResposta, Estudo, Participacao


class ParticipacaoInline(admin.TabularInline):
    model = Participacao
    extra = 0
    readonly_fields = ("docente", "posicao", "braco", "ordem", "concluida_em")


@admin.register(Estudo)
class EstudoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "pesquisador", "lote", "status", "criado_em")
    list_filter = ("status",)
    inlines = [ParticipacaoInline]


@admin.register(AlocacaoResposta)
class AlocacaoAdmin(admin.ModelAdmin):
    list_display = ("estudo", "resposta", "metade")
    list_filter = ("estudo", "metade")
