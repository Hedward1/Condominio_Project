# Sistema Modular de Administracao de Condominios

Monolito Django modular para administracao de condominios, com multi-tenancy por linha e escopo inicial de MVP.

## Escopo MVP

- Core do condominio
- Comunicacao oficial
- Chamados e ocorrencias
- Documentos
- Reservas de areas comuns
- Dashboard simples do sindico

## Primeiros comandos

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

## Testes

```powershell
.\.venv\Scripts\python -m pytest
```

## Decisoes de seguranca

- O tenant ativo e carregado por middleware a partir da sessao.
- Objetos de negocio usam `condominium_id`.
- Leituras ficam em selectors com filtro por condominio.
- Escritas ficam em services com validacao de permissao.
- Acoes sensiveis gravam `AuditLog`.
