# Arquitetura Técnica

## Decisão principal

O sistema será iniciado como um monólito Django modular.

Essa decisão prioriza:

- Entrega rápida do MVP.
- Menor complexidade operacional.
- Permissões centralizadas.
- Deploy simples.
- Melhor controle de isolamento multi-tenant.
- Facilidade para o Codex navegar no projeto.

## Stack inicial

- Python.
- Django.
- Django REST Framework.
- PostgreSQL.
- Docker.
- Pytest.
- Ruff.
- Django Templates com HTMX ou frontend responsivo simples.

## Apps planejados

```text
apps/
├── common/
├── accounts/
├── core/
├── audit/
├── communication/
├── tickets/
├── documents/
├── reservations/
└── dashboard/
```

## Responsabilidades por app

### `apps.common`

Bases abstratas, helpers, validators, exceptions e utilidades compartilhadas.

### `apps.accounts`

Usuários, autenticação, convites, recuperação de senha e vínculo do usuário com condomínios.

### `apps.core`

Condomínios, blocos, unidades, moradores, proprietários, inquilinos, síndico, conselho, funcionários, memberships e permissões.

### `apps.audit`

Logs de auditoria para ações sensíveis.

### `apps.communication`

Comunicados oficiais, categorias, publicação, mural e confirmação de leitura.

### `apps.tickets`

Chamados, ocorrências, categorias, comentários, anexos, status, prioridade e histórico.

### `apps.documents`

Documentos, categorias, permissões de acesso, uploads, downloads autorizados e logs de acesso.

### `apps.reservations`

Áreas comuns, regras de reserva, bloqueios, solicitações, aprovações, cancelamentos e calendário.

### `apps.dashboard`

Indicadores simples para o síndico.

## Multi-tenancy

A estratégia inicial é row-based multi-tenancy.

Tabelas de negócio devem ter `condominium_id` diretamente sempre que prático.

Exemplos:

- `Block`.
- `Unit`.
- `CondominiumMembership`.
- `Announcement`.
- `Ticket`.
- `Document`.
- `Amenity`.
- `Reservation`.
- `AuditLog`.

Entidades filhas podem herdar o escopo pelo objeto pai, mas selectors e services devem validar o condomínio mesmo assim.

## Condomínio ativo

Para o MVP, o condomínio ativo deve ser resolvido assim:

1. Usuário faz login.
2. Sistema lista condomínios vinculados ao usuário.
3. Usuário escolhe o condomínio ativo.
4. O ID do condomínio ativo fica na sessão.
5. Middleware carrega `request.condominium`.
6. Selectors e services usam `request.condominium`.

## Camadas de código

### Views

Recebem request, validam autenticação, chamam forms/serializers, chamam services/selectors e retornam resposta.

Views não devem concentrar regra de negócio complexa.

### Selectors

Leituras e consultas.

Devem sempre filtrar por condomínio.

Exemplos:

```python
list_tickets_for_condominium(condominium, filters)
get_ticket_for_condominium(condominium, ticket_id)
list_announcements_for_user(condominium, user)
```

### Services

Escritas e regras de negócio.

Exemplos:

```python
create_ticket(condominium, user, data)
change_ticket_status(condominium, user, ticket, new_status)
publish_announcement(condominium, user, announcement)
request_reservation(condominium, user, data)
approve_reservation(condominium, user, reservation)
```

## Performance inicial

- Paginar listagens.
- Usar `select_related` e `prefetch_related`.
- Indexar `condominium_id`, `status`, `created_at`, `unit_id`, `category_id` e datas de reserva.
- Evitar dashboards calculados com loops em Python.
- Criar agregações somente quando houver necessidade real.

## Evolução futura

Módulos como notificações, IA, pagamentos, portaria e BI avançado podem virar serviços separados no futuro, mas não devem ser separados no MVP.
