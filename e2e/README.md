# Testes de ponta a ponta

Dirigem a interface real (Playwright + Chromium) contra o stack do `docker compose`.

## Preparar

```bash
docker compose up -d
docker compose exec backend python src/manage.py migrate
docker compose exec backend python src/manage.py shell -c "
from core.models import Usuario
Usuario.objects.create_superuser('pesquisa@exemplo.org', 'Pesquisa#2026', nome='Pesquisador')
Usuario.objects.create_user('docente@exemplo.org', 'Docente#2026', nome='Docente Teste')"
pip install playwright requests && playwright install chromium
```

Para rodar todos em sequência, use `THROTTLE_LOGIN=100/min` no `.env`: eles fazem muitos logins.

## Rodar

| Script | Quickstart | O que verifica |
|---|---|---|
| `us1.py` | V1–V3 | rubrica, importação anônima com chave, estimativa, rodada, trechos, auditoria 0 identificadores |
| `us2.py` | V4 | fila com não convergentes primeiro, divergente sem nível sugerido |
| `us3.py` | V5 | decisão por clique e teclado, histórico, notas só de finalizadas |
| `us4.py` | V6 | reaplicação, estabilidade, limiar de sensibilidade, exportação reproduzida pelo script |
| `us5.py` | V8 | estudo: convite, senha, as duas condições, ocultação no servidor, exportação P01… |
| `us6.py` | V9 | exportar e importar modelo de rubrica |
| `v7_modelo_real.py` | V7 | rodada com o Gemini real (**tem custo**; aborta acima de US$ 2) |

```bash
python3 e2e/us1.py            # etc.; capturas de tela em e2e/capturas/
python3 e2e/v7_modelo_real.py gemini gemini-3.6-flash 10 5
```
