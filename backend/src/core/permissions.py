from rest_framework.permissions import BasePermission


class EhPesquisador(BasePermission):
    message = "Somente pesquisador."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.eh_pesquisador)


def pode_ver_lote(usuario, lote) -> bool:
    """Dono do lote; pesquisador só vê lotes de estudos que criou (FR-027)."""
    if lote.dono_id == usuario.id:
        return True
    if usuario.eh_pesquisador and hasattr(lote, "estudos"):
        return lote.estudos.filter(pesquisador=usuario).exists()
    return False
