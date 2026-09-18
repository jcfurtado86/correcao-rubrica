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
cp .env.example .env          # sem chave, só o modelo "Dublê": tudo roda sem custo e sem rede
docker compose up -d
docker compose exec backend python src/manage.py migrate
docker compose exec backend python src/manage.py createsuperuser
docker compose exec backend python src/manage.py carregar_exemplo   # rubrica de exemplo
```

Interface em http://localhost:5183, API em http://localhost:8810/api/docs/ e admin em
http://localhost:8810/admin/.

## Testes

```bash
docker compose exec backend pytest      # backend, em 8 processos (ou no host: cd backend && .venv/bin/pytest)
cd frontend && npm test                 # funções do frontend
python3 e2e/us1.py                      # ponta a ponta pela interface (ver e2e/README.md)
```

Nenhum teste automatizado chama o modelo real. Para usar o Gemini: `GEMINI_API_KEY` de projeto
**com faturamento** e `GEMINI_PAID_TIER=true` no `.env`. Os modelos Gemini passam a aparecer
para escolha na criação do lote. O nível gratuito não é usado (research R9).

## Documentação

- [Manual da docente](docs/manual-docente.md)
- [Rascunho do parecer de tratamento de dados](docs/parecer-tratamento-dados.md)
- [Modelo público de rubrica](docs/modelos/verificacao-validacao.json)
- [Testes de ponta a ponta](e2e/README.md)
