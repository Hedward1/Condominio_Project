# Condominio Project

Sistema web modular para administracao de condominios, construido como um monolito Django multi-tenant por condominio.

O MVP funcional base ja cobre a rotina operacional principal: core do condominio, comunicacao oficial, chamados, documentos, reservas e dashboard do sindico.

## Modulos Entregues

- Core: condominios, blocos, unidades, membros e moradores por unidade.
- Comunicacao Oficial: categorias, comunicados, publicacao, arquivamento e leitura.
- Chamados/Ocorrencias: categorias, abertura, comentarios, gestao, filtros e auditoria.
- Documentos: categorias, upload protegido, visibilidade e download autorizado.
- Reservas: areas comuns, solicitacao, aprovacao, rejeicao e cancelamento.
- Dashboard: indicadores simples de core, comunicacao, chamados, documentos e reservas.
- Auditoria: logs para acoes sensiveis.

## Principios

- Todo dado operacional pertence a um condominio.
- Toda query de negocio deve filtrar por condominio.
- Permissoes sao aplicadas no backend.
- Escritas passam por services.
- Leituras passam por selectors.
- Acoes sensiveis geram AuditLog.
- Uploads e downloads passam por autorizacao.
- O MVP evita boleto, banco, inadimplencia, assembleia formal, app nativo, portaria completa e IA avancada.

## Stack

- Python 3.14
- Django 6
- Django REST Framework
- PostgreSQL
- Docker
- Pytest
- Ruff
- Templates Django responsivos

## Setup Local

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

Com Docker:

```powershell
docker compose up --build
```

## Dados Demo

Depois de aplicar migrations, crie um condominio de demonstracao:

```powershell
.\.venv\Scripts\python manage.py seed_demo_condominium
```

Credenciais padrao criadas pelo comando:

- Sindico: `sindico.demo@example.com`
- Morador: `morador.demo@example.com`
- Senha: `Demo@12345`

O comando e idempotente e nao duplica dados quando executado mais de uma vez.
Use `--password` para trocar a senha padrao em ambientes compartilhados.

## Validacao

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python manage.py makemigrations --check --dry-run
```

## Producao

Use `config.settings.production` e defina variaveis reais em ambiente seguro:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.production"
$env:DJANGO_SECRET_KEY="..."
$env:DJANGO_DEBUG="False"
$env:DJANGO_ALLOWED_HOSTS="app.seudominio.com"
$env:DJANGO_CSRF_TRUSTED_ORIGINS="https://app.seudominio.com"
$env:DATABASE_URL="postgres://..."
$env:DJANGO_STATIC_ROOT="/app/staticfiles"
$env:DJANGO_MEDIA_ROOT="/app/media"
```

Consulte [docs/operations/deploy.md](docs/operations/deploy.md) antes de publicar.

## Documentacao

- [CODEX.md](CODEX.md): manual tecnico para desenvolvimento assistido.
- [docs/mvp/checklist.md](docs/mvp/checklist.md): checklist do MVP funcional base.
- [docs/operations/deploy.md](docs/operations/deploy.md): guia de deploy e producao.
- [docs/technical/architecture.md](docs/technical/architecture.md): arquitetura tecnica.
- [docs/technical/security.md](docs/technical/security.md): seguranca, permissoes e LGPD.
- [docs/technical/testing.md](docs/technical/testing.md): estrategia de testes.
- [docs/adr](docs/adr): decisoes arquiteturais.

## Status

MVP funcional base congelado tecnicamente para revisao, demonstracao e preparacao de deploy.
