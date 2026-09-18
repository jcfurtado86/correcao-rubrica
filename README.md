# Correção Assistida por Rubrica

MVP do TCC "Correção Assistida por Rubrica com Aferição de Consistência Avaliativa"
(Glauco Silva Sousa; orientação Júlio Furtado).

A docente define a rubrica. O sistema pré-avalia cada resposta critério por critério, com
justificativa ancorada em trecho literal do texto do estudante, e **declara a divergência**
quando execuções repetidas do modelo não convergem. A decisão final é sempre da docente.

- Especificação, plano e tarefas: [`specs/001-mvp-correcao-assistida/`](specs/001-mvp-correcao-assistida/)
- Princípios do projeto: [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- Validação ponta a ponta: [`quickstart.md`](specs/001-mvp-correcao-assistida/quickstart.md)

## Subir

```bash
cp .env.example .env          # LLM_PROVIDER=dumb roda tudo sem custo e sem rede
docker compose up -d
docker compose exec backend python src/manage.py migrate
docker compose exec backend python src/manage.py createsuperuser
docker compose exec backend python src/manage.py carregar_exemplo
```

Interface em http://localhost:5183, API em http://localhost:8810/api/docs/ e admin em
http://localhost:8810/admin/.

## Testes

```bash
cd backend && .venv/bin/pytest          # backend, em paralelo (banco do compose em localhost:55433)
cd frontend && npm test                 # funções do frontend
```

Nenhum teste chama o modelo real. Para usar o Gemini: `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`
de projeto **com faturamento** e `GEMINI_PAID_TIER=true`. O nível gratuito não é usado
(research R9).
