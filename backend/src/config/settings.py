"""Configuração Django (12-factor: o que varia por ambiente vem de variável de ambiente)."""

from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR.parent.parent / ".env", overwrite=False)

_SECRET_KEY_DEV = "dev-chave-insegura-trocar-em-producao"
SECRET_KEY = env("SECRET_KEY", default=_SECRET_KEY_DEV)
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

if not DEBUG and SECRET_KEY == _SECRET_KEY_DEV:
    raise ImproperlyConfigured("Defina a variável de ambiente SECRET_KEY em produção.")
if not DEBUG and ("*" in ALLOWED_HOSTS or not ALLOWED_HOSTS):
    raise ImproperlyConfigured("Defina ALLOWED_HOSTS com os hosts reais em produção.")

if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    # apps do domínio (plan.md, Project Structure)
    "core",
    "conectores",
    "rubricas",
    "lotes",
    "avaliacao",
    "revisao",
    "estudos",
    "metricas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://correcao:correcao@localhost:55433/correcao"
    ),
}

AUTH_USER_MODEL = "core.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Belem"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Upload só em memória (research R9) -----------------------------------
# A planilha de respostas traz nome, e-mail e matrícula de estudantes. Com o
# handler padrão, arquivos acima de 2,5 MB iriam para um arquivo temporário em
# disco; aqui o upload nunca toca o disco e morre com a requisição.
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]
LIMITE_UPLOAD_BYTES = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = LIMITE_UPLOAD_BYTES
DATA_UPLOAD_MAX_MEMORY_SIZE = LIMITE_UPLOAD_BYTES + 1024 * 1024  # margem para os campos do form
LIMITE_LINHAS_PLANILHA = 1000

# --- API -------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Números saem como números (o SPA faz conta com custo e acordo).
    "COERCE_DECIMAL_TO_STRING": False,
    "EXCEPTION_HANDLER": "core.exceptions.tratar_excecoes",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": env("THROTTLE_LOGIN", default="10/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Correção Assistida por Rubrica",
    "DESCRIPTION": "API do MVP (specs/001-mvp-correcao-assistida).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5183")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[FRONTEND_URL])

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="correcao@localhost")

# --- Celery (research R8) ----------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6380/0")
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
# Com acks_late, uma tarefa reservada por um worker que morreu só volta à fila
# depois deste prazo (padrão do Redis: 1 h). 10 min cobre uma chamada lenta
# mais a maior espera entre tentativas (research R8).
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 600}
# Execução EM_ANDAMENTO há mais que isto é considerada abandonada (worker caiu).
EXECUCAO_ABANDONADA_APOS_S = 600

# --- Modelo de linguagem (research R2, R3, R7, R9) --------------------------
# "dumb" é o dublê determinístico offline; "gemini" usa a API do Google.
LLM_PROVIDER = env("LLM_PROVIDER", default="dumb")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.6-flash")
# Só com chave de projeto com faturamento. Os termos do nível gratuito permitem ao
# Google usar e revisar o conteúdo enviado; o projeto não o usa (research R9).
GEMINI_PAID_TIER = env.bool("GEMINI_PAID_TIER", default=False)
TETO_USD_PADRAO = env.float("TETO_USD_PADRAO", default=10.0)
LLM_CONCORRENCIA = env.int("LLM_CONCORRENCIA", default=8)
LLM_RATE_LIMIT = env("LLM_RATE_LIMIT", default="120/m")
LLM_MAX_TENTATIVAS = env.int("LLM_MAX_TENTATIVAS", default=6)
LLM_TIMEOUT_S = env.int("LLM_TIMEOUT_S", default=60)
LLM_MAX_TOKENS_SAIDA = env.int("LLM_MAX_TOKENS_SAIDA", default=8192)
TOKENS_SAIDA_ESTIMADOS = env.int("TOKENS_SAIDA_ESTIMADOS", default=1050)
LIMITE_CARACTERES_RESPOSTA = env.int("LIMITE_CARACTERES_RESPOSTA", default=15000)

# --- Logs sem texto de estudante (Princípio IV) -----------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "sem_texto_de_estudante": {"()": "core.logs.FiltroSemTexto"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["sem_texto_de_estudante"],
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
