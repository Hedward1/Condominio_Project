# Condominio Project

Sistema modular de administração de condomínios, desenvolvido para centralizar comunicação, chamados, documentos, reservas e indicadores em uma plataforma simples, segura e transparente.

## Objetivo

O projeto tem como objetivo criar uma plataforma web para ajudar síndicos, moradores, conselhos e pequenos administradores a organizar a rotina operacional do condomínio, reduzindo dependência de WhatsApp, planilhas, papel e controles manuais.

## Escopo inicial do MVP

O MVP será focado nos seguintes módulos:

- Core do condomínio;
- Cadastro de blocos, unidades e moradores;
- Comunicação oficial;
- Chamados e ocorrências;
- Documentos;
- Reservas de áreas comuns;
- Dashboard simples do síndico.

## Fora do MVP inicial

Para manter o escopo controlado, os seguintes itens não serão implementados na primeira versão:

- Boleto;
- Integração bancária;
- Inadimplência;
- Assembleia digital formal;
- App mobile nativo;
- Portaria completa;
- IA avançada;
- Customizações profundas por cliente.

## Arquitetura planejada

A arquitetura inicial será um monólito Django modular, com PostgreSQL e separação multi-tenant por condomínio.

## Stack prevista

- Python;
- Django;
- PostgreSQL;
- Django REST Framework;
- Docker;
- Pytest;
- HTMX ou frontend web responsivo simples.

## Princípios do projeto

- Simples antes de completo;
- Modular antes de customizável demais;
- Segurança e LGPD desde o primeiro commit;
- Multi-tenant desde o início;
- Histórico antes de conversa solta;
- Dados antes de achismo;
- Web responsivo antes de app nativo.

## Primeiros comandos previstos

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

## Testes previstos

```powershell
.\.venv\Scripts\python -m pytest
```

## Documentação

- [`CODEX.md`](CODEX.md): manual técnico para orientar o Codex e qualquer agente de desenvolvimento.
- [`docs/product/strategy.md`](docs/product/strategy.md): estratégia de produto e escopo do MVP.
- [`docs/technical/architecture.md`](docs/technical/architecture.md): arquitetura técnica planejada.
- [`docs/technical/security.md`](docs/technical/security.md): segurança, permissões e LGPD.
- [`docs/technical/testing.md`](docs/technical/testing.md): estratégia de testes.
- [`docs/adr`](docs/adr): decisões arquiteturais registradas.

## Status

Projeto em fase inicial de documentação, validação e preparação técnica.
