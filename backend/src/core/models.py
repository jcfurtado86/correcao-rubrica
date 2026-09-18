from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class GerenciadorDeUsuarios(BaseUserManager):
    use_in_migrations = True

    def _criar(self, email, password, **extras):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        usuario = self.model(email=self.normalize_email(email).lower(), **extras)
        if password:
            usuario.set_password(password)
        else:
            usuario.set_unusable_password()
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extras):
        extras.setdefault("is_staff", False)
        extras.setdefault("is_superuser", False)
        return self._criar(email, password, **extras)

    def create_superuser(self, email, password=None, **extras):
        extras.setdefault("is_staff", True)
        extras.setdefault("is_superuser", True)
        extras.setdefault("papel", Usuario.Papel.PESQUISADOR)
        return self._criar(email, password, **extras)


class Usuario(AbstractUser):
    """Pessoa usuária. Login por e-mail; sem username (data-model.md, core)."""

    class Papel(models.TextChoices):
        DOCENTE = "DOCENTE", "Docente"
        PESQUISADOR = "PESQUISADOR", "Pesquisador"

    username = None
    first_name = None
    last_name = None
    email = models.EmailField("e-mail", unique=True)
    nome = models.CharField(max_length=150, blank=True)
    papel = models.CharField(max_length=12, choices=Papel.choices, default=Papel.DOCENTE)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = GerenciadorDeUsuarios()

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.nome or self.email

    @property
    def eh_pesquisador(self) -> bool:
        return self.papel == self.Papel.PESQUISADOR
