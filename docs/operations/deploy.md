# Guia de Deploy e Producao

Este guia cobre o deploy inicial do MVP funcional base. Ele nao substitui uma revisao de infraestrutura, mas define os requisitos minimos para evitar publicar com configuracao insegura.

## Variaveis Obrigatorias

Use `config.settings.production` em producao:

```text
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<secret forte>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=app.seudominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://app.seudominio.com
DATABASE_URL=postgres://usuario:senha@host:5432/database
DJANGO_STATIC_ROOT=/app/staticfiles
DJANGO_MEDIA_ROOT=/app/media
```

Se a aplicacao estiver atras de proxy/reverse proxy que envia `X-Forwarded-Proto`, habilite:

```text
DJANGO_SECURE_PROXY_SSL_HEADER=True
```

## Checklist de Producao

- [ ] `DJANGO_SECRET_KEY` definido fora do repositorio.
- [ ] `DJANGO_DEBUG=False`.
- [ ] `DJANGO_ALLOWED_HOSTS` sem coringas e sem valores locais.
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` com URL HTTPS publica.
- [ ] Banco PostgreSQL com backup configurado.
- [ ] HTTPS terminando no proxy/load balancer.
- [ ] `STATIC_ROOT` apontando para volume/diretorio servido como static.
- [ ] Volumes persistentes para `media/`, se storage local for usado.
- [ ] Logs sem dados sensiveis.
- [ ] `python manage.py check --deploy` revisado antes de publicar.
- [ ] Migrations aplicadas antes de liberar trafego.

## Comandos de Build

```powershell
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
```

Para ambiente sem Docker:

```powershell
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py collectstatic --noinput
.\.venv\Scripts\python manage.py createsuperuser
```

## Validacao Antes de Publicar

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python manage.py makemigrations --check --dry-run
.\.venv\Scripts\python manage.py check --deploy --settings=config.settings.production
```

O ultimo comando exige variaveis de producao reais no ambiente.

## Observacoes de Uploads

Documentos usam `FileField`, mas o acesso aos arquivos deve continuar passando pela view protegida de download. Nao configure servidor web para expor `MEDIA_URL` publicamente em producao sem uma camada de autorizacao.

Para o MVP, storage local e aceitavel em demo/controlado. Para producao real, planeje storage privado, backup e politica de retencao.

## Seed de Demonstracao

Em ambiente local ou homologacao:

```powershell
.\.venv\Scripts\python manage.py seed_demo_condominium
```

Nao rode seed demo em producao real sem necessidade explicita.
