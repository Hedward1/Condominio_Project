# Checklist do MVP Funcional Base

## Core

- [x] Condominios com escopo multi-tenant.
- [x] Blocos com criar, editar e desativar.
- [x] Unidades com criar, editar e desativar.
- [x] Membros com criacao e desativacao.
- [x] Moradores por unidade com criacao e desativacao.
- [x] Protecao contra desativar entidades com dependencias ativas.
- [x] Tenant ativo via sessao e middleware.
- [x] Permissoes de gestor no backend.

## Comunicacao Oficial

- [x] Categorias de comunicados.
- [x] Comunicados em rascunho, publicados e arquivados.
- [x] Publicacao e arquivamento apenas por gestor.
- [x] Mural do morador com apenas comunicados publicados.
- [x] Confirmacao de leitura idempotente.
- [x] Indicadores no dashboard.

## Chamados/Ocorrencias

- [x] Categorias de chamados.
- [x] Abertura de chamado por morador.
- [x] Lista do morador limitada aos proprios chamados.
- [x] Gestao administrativa de chamados.
- [x] Comentarios publicos e internos.
- [x] Filtros administrativos por status, prioridade e categoria.
- [x] Validacao de responsavel pertencente ao condominio.

## Documentos

- [x] Categorias de documentos.
- [x] Upload de documentos por gestor.
- [x] Download protegido por view autorizada.
- [x] Visibilidade publica para moradores ou somente gestores.
- [x] Morador ve apenas documentos publicos do condominio ativo.
- [x] Filtros administrativos por visibilidade e categoria.
- [x] Indicador no dashboard.

## Reservas

- [x] Areas comuns.
- [x] Solicitacao de reserva por morador.
- [x] Gestor aprova, rejeita e cancela reservas.
- [x] Bloqueio de aprovacao com sobreposicao real em reserva aprovada da mesma area.
- [x] Cancelamento restrito ao gestor nesta v1.
- [x] Filtros administrativos por status e area comum.
- [x] Indicadores no dashboard.

## Auditoria e Seguranca

- [x] AuditLog para acoes sensiveis.
- [x] Selectors tenant-safe para leituras.
- [x] Services para escritas e regras de negocio.
- [x] Permissoes no backend.
- [x] Pagina 403 amigavel.
- [x] Testes de isolamento entre condominios.
- [x] Upload/download sem exposicao direta por `MEDIA_URL`.

## Fora do MVP

- [ ] Boleto.
- [ ] Integracao bancaria.
- [ ] Inadimplencia.
- [ ] Assembleia digital formal.
- [ ] App mobile nativo.
- [ ] Portaria completa.
- [ ] Notificacoes externas, WhatsApp, push ou email transacional.
- [ ] IA avancada.
- [ ] BI avancado.

## Comandos de Congelamento

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python manage.py makemigrations --check --dry-run
```
