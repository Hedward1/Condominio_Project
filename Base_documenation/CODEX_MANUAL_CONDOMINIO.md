# Manual Técnico para Codex — Sistema Modular de Administração de Condomínios

**Versão:** 1.0  
**Objetivo:** orientar o Codex a desenvolver o sistema de condomínio com coerência técnica, escopo controlado, segurança, arquitetura multi-tenant e foco no MVP.  
**Uso recomendado:** salvar este arquivo como `CODEX.md` ou `docs/CODEX_MANUAL.md` na raiz do repositório.

---

## 1. Missão do sistema

Construir uma plataforma web modular para administração de condomínios, voltada inicialmente para síndicos moradores, pequenos e médios condomínios, conselhos e administradores pequenos.

O sistema deve organizar a rotina do condomínio em um único ambiente, começando pelos módulos essenciais:

1. Core do condomínio.
2. Comunicação oficial.
3. Chamados e ocorrências.
4. Documentos.
5. Reservas de áreas comuns.
6. Painel simples do síndico.

O sistema deve reduzir dependência de WhatsApp, planilhas, papel, conversas soltas e documentos espalhados.

---

## 2. Regras absolutas para o Codex

Antes de executar qualquer tarefa, o Codex deve obedecer estas regras:

1. **Ler este manual antes de alterar código.**
2. **Preservar o escopo do MVP.**
3. **Não criar funcionalidades futuras sem pedido explícito.**
4. **Não implementar boleto, banco, inadimplência, assembleia digital formal, app nativo, portaria completa ou IA avançada no MVP.**
5. **Todo dado operacional deve pertencer a um condomínio.**
6. **Nunca permitir vazamento de dados entre condomínios.**
7. **Toda query de dados de negócio deve ser filtrada por `condominium_id` ou pelo escopo de tenant resolvido.**
8. **Toda alteração sensível deve gerar log de auditoria.**
9. **Permissões devem ser validadas no backend, nunca apenas no frontend.**
10. **Não salvar segredo, token ou senha no código.**
11. **Não apagar dados importantes fisicamente sem regra explícita. Preferir soft delete em entidades de negócio.**
12. **Toda tarefa deve terminar com testes ou, no mínimo, checklist técnico do que foi validado.**
13. **Se houver dúvida de produto, escolher a solução mais simples, segura e aderente ao MVP.**
14. **Se houver risco de LGPD, segurança ou vazamento entre tenants, parar e apontar o risco.**
15. **Evitar overengineering. O MVP precisa funcionar bem antes de ficar sofisticado.**

---

## 3. Decisão arquitetural inicial

### 3.1. Arquitetura recomendada

Usar **monólito modular Django**.

Motivos:

- Entrega mais rápida para MVP.
- Menos complexidade operacional.
- Backend, templates, permissões e regras de negócio ficam no mesmo domínio.
- Facilita desenvolvimento guiado por Codex.
- Facilita deploy inicial.
- Permite evoluir para API e frontend separado depois.

### 3.2. Stack recomendada

Backend:

- Python.
- Django.
- Django REST Framework para APIs internas e futuras integrações.
- PostgreSQL.
- Redis para cache e filas futuras.
- Celery para tarefas assíncronas futuras.
- Pytest para testes.
- Ruff/Black ou ferramenta equivalente para lint e formatação.
- Docker para ambiente local e deploy.

Frontend MVP:

- Django Templates.
- HTMX para interações simples sem SPA pesada.
- Alpine.js apenas quando necessário.
- CSS com Tailwind ou Bootstrap, escolher um e manter consistência.
- Web responsivo antes de app nativo.

Armazenamento de arquivos:

- Desenvolvimento: storage local.
- Produção: storage compatível com S3, se possível.
- Nunca expor caminho real de arquivo.
- Downloads devem passar por autorização.

Observabilidade:

- Logs estruturados.
- Log de auditoria em ações sensíveis.
- Registro de erros.
- Métricas simples de uso por condomínio.

---

## 4. Estrutura de pastas recomendada

```text
condominio-system/
├── README.md
├── CODEX.md
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── manage.py
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   ├── core/
│   ├── audit/
│   ├── communication/
│   ├── tickets/
│   ├── documents/
│   ├── reservations/
│   ├── dashboard/
│   └── common/
├── templates/
├── static/
├── media/
├── tests/
│   ├── factories/
│   ├── integration/
│   └── e2e/
└── docs/
    ├── product/
    ├── technical/
    ├── architecture/
    └── adr/
```

---

## 5. Apps Django e responsabilidades

### 5.1. `apps.common`

Responsável por utilidades compartilhadas.

Deve conter:

- BaseModel.
- SoftDeleteModel.
- mixins.
- validators.
- helpers de paginação.
- helpers de timezone.
- exceptions padronizadas.
- classes base para services/selectors.

Não deve conter regra específica de condomínio, chamado, documento ou reserva.

### 5.2. `apps.accounts`

Responsável por autenticação e usuário.

Entidades:

- User.
- UserProfile, se necessário.
- Password reset.
- Invite token.
- Membership do usuário no condomínio.

Responsabilidades:

- Login.
- Logout.
- Recuperação de senha.
- Convite de usuário.
- Associação do usuário a um ou mais condomínios.
- Troca de condomínio ativo, caso o usuário tenha acesso a mais de um.

### 5.3. `apps.core`

Coração multi-tenant do sistema.

Entidades principais:

- Condominium.
- Block.
- Unit.
- UnitOccupancy.
- CondominiumMembership.
- Role.
- Permission, se necessário.
- CondominiumSettings.

Responsabilidades:

- Cadastro do condomínio.
- Cadastro de blocos.
- Cadastro de unidades.
- Cadastro de moradores, proprietários, inquilinos, síndico, conselho e funcionários.
- Configurações gerais.
- Base de permissões.
- Escopo multi-tenant.

### 5.4. `apps.audit`

Responsável por histórico e rastreabilidade.

Entidades:

- AuditLog.
- ObjectHistory, se necessário.

Responsabilidades:

- Registrar criação, alteração e exclusão lógica.
- Registrar mudança de status.
- Registrar leitura de documento sensível, quando necessário.
- Registrar download de arquivo sensível.
- Registrar ações administrativas.

### 5.5. `apps.communication`

Responsável por comunicados oficiais.

Entidades:

- Announcement.
- AnnouncementCategory.
- AnnouncementReadReceipt.
- AnnouncementAttachment, se necessário.

Responsabilidades:

- Criar comunicados.
- Publicar comunicados.
- Fixar avisos.
- Categorizar comunicados.
- Registrar confirmação de leitura.
- Exibir mural do condomínio.
- Manter histórico oficial.

### 5.6. `apps.tickets`

Responsável por chamados e ocorrências.

Entidades:

- Ticket.
- TicketCategory.
- TicketComment.
- TicketAttachment.
- TicketStatusHistory.
- TicketPriority.

Responsabilidades:

- Abertura de chamado.
- Comentários.
- Anexos/fotos.
- Status.
- Prioridade.
- Responsável.
- Conclusão.
- Histórico.

### 5.7. `apps.documents`

Responsável por documentos oficiais.

Entidades:

- Document.
- DocumentCategory.
- DocumentVersion.
- DocumentAccessLog.

Responsabilidades:

- Upload.
- Categorias.
- Permissões de acesso.
- Busca.
- Histórico.
- Versionamento futuro.
- Download autorizado.

### 5.8. `apps.reservations`

Responsável por reservas de áreas comuns.

Entidades:

- Amenity.
- AmenityRule.
- AmenityBlockedDate.
- Reservation.
- ReservationStatusHistory.

Responsabilidades:

- Cadastro de áreas comuns.
- Regras de reserva.
- Calendário.
- Bloqueio de datas.
- Aprovação manual ou automática.
- Limite por unidade.
- Histórico.

### 5.9. `apps.dashboard`

Responsável por indicadores simples.

Não deve virar BI complexo no MVP.

Indicadores iniciais:

- Chamados abertos.
- Chamados resolvidos.
- Chamados por status.
- Chamados por categoria.
- Tempo médio de resolução.
- Comunicados publicados.
- Taxa de leitura de comunicados.
- Reservas realizadas.
- Documentos acessados.

---

## 6. Modelo multi-tenant

### 6.1. Estratégia inicial

Usar multi-tenancy por **linha**, com `condominium_id` nas tabelas de negócio.

Exemplo:

```text
tickets_ticket
- id
- condominium_id
- unit_id
- created_by_id
- category_id
- status
- priority
- title
- description
- created_at
- updated_at
```

### 6.2. Regras do tenant

Toda entidade de negócio deve pertencer diretamente ou indiretamente a um condomínio.

Entidades com `condominium_id` direto:

- Block.
- Unit.
- CondominiumMembership.
- Announcement.
- AnnouncementCategory.
- Ticket.
- TicketCategory.
- Document.
- DocumentCategory.
- Amenity.
- Reservation.
- AuditLog.

Entidades com vínculo indireto:

- TicketComment pertence a Ticket.
- TicketAttachment pertence a Ticket.
- AnnouncementReadReceipt pertence a Announcement.
- ReservationStatusHistory pertence a Reservation.
- DocumentVersion pertence a Document.

### 6.3. Resolução do condomínio ativo

O sistema deve resolver o condomínio ativo por uma destas estratégias:

1. Subdomínio: `condominio-a.sistema.com`.
2. Path: `/c/{slug}/...`.
3. Sessão do usuário: usuário escolhe condomínio ativo após login.

Para MVP, usar uma solução simples:

- Usuário faz login.
- Sistema lista condomínios aos quais ele pertence.
- Usuário escolhe condomínio ativo.
- O `condominium_id` ativo fica na sessão.
- Middleware carrega `request.condominium`.
- Todas as views/services usam `request.condominium`.

### 6.4. Regra de ouro

Nenhuma view, API, service ou selector pode buscar objeto de negócio apenas por `id`.

Errado:

```python
Ticket.objects.get(id=ticket_id)
```

Certo:

```python
Ticket.objects.get(id=ticket_id, condominium=request.condominium)
```

Ou melhor:

```python
get_ticket_for_condominium(ticket_id=ticket_id, condominium=request.condominium)
```

---

## 7. Padrões de modelagem

### 7.1. IDs

Usar UUID como chave primária para entidades principais.

Motivos:

- Evita enumeração simples de IDs.
- Ajuda segurança.
- Facilita integração futura.

### 7.2. Campos padrão

Entidades principais devem herdar de um modelo base:

```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

Para entidades auditáveis:

```python
class AuditableModel(BaseModel):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        abstract = True
```

Para soft delete:

```python
class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        abstract = True
```

### 7.3. Nomenclatura

- Apps em inglês.
- Models em inglês.
- Campos em inglês.
- Textos de interface em português.
- Choices em inglês no código e labels em português.
- Services com verbos: `create_ticket`, `publish_announcement`, `approve_reservation`.

### 7.4. Migrations

- Nunca editar migration já aplicada em ambiente compartilhado.
- Criar nova migration para mudanças.
- Nomear migrations com clareza quando possível.
- Validar constraints antes de colocar em produção.
- Evitar migrations que façam operações pesadas sem planejamento.

---

## 8. Modelo de dados inicial

### 8.1. Core

#### Condominium

Campos sugeridos:

- id.
- name.
- slug.
- document_number, opcional.
- address.
- city.
- state.
- postal_code.
- is_active.
- created_at.
- updated_at.

Regras:

- `slug` único.
- Condomínio inativo não permite novas ações operacionais.
- Superadmin pode ver todos.
- Usuários normais só veem condomínios onde possuem membership.

#### Block

Campos:

- id.
- condominium_id.
- name.
- description.
- is_active.

Constraints:

- `unique(condominium_id, name)`.

#### Unit

Campos:

- id.
- condominium_id.
- block_id.
- number.
- floor.
- description.
- is_active.

Constraints:

- `unique(condominium_id, block_id, number)` quando houver bloco.
- `unique(condominium_id, number)` pode ser usado para condomínios sem bloco.

#### CondominiumMembership

Campos:

- id.
- condominium_id.
- user_id.
- role.
- is_active.
- invited_by_id.
- joined_at.

Roles iniciais:

- `SUPERADMIN`.
- `CONDO_ADMIN`.
- `SYNDIC`.
- `COUNCIL`.
- `STAFF`.
- `RESIDENT`.
- `OWNER`.
- `TENANT`.

Regra:

- Um usuário pode ter papéis diferentes em condomínios diferentes.
- Nunca usar `is_staff` do Django como permissão de condomínio.
- `is_staff` deve ficar restrito ao admin técnico/plataforma.

#### UnitOccupancy

Campos:

- id.
- condominium_id.
- unit_id.
- user_id.
- occupancy_type.
- is_primary.
- starts_at.
- ends_at.
- is_active.

Tipos:

- `OWNER`.
- `TENANT`.
- `RESIDENT`.
- `DEPENDENT`.

---

## 9. Matriz de permissões inicial

### 9.1. Perfis

#### Superadmin da plataforma

Pode:

- Gerenciar todos os condomínios.
- Acessar painel administrativo técnico.
- Ativar/desativar condomínio.
- Ver logs técnicos.

Não deve ser usado no dia a dia do condomínio.

#### Síndico

Pode:

- Gerenciar dados do condomínio.
- Gerenciar blocos e unidades.
- Convidar moradores.
- Publicar comunicados.
- Gerenciar chamados.
- Gerenciar documentos.
- Gerenciar reservas.
- Ver dashboard.

#### Conselho

Pode:

- Ver comunicados.
- Ver chamados, dependendo da configuração.
- Ver documentos permitidos.
- Ver reservas.
- Ver dashboard básico.
- Não deve alterar configurações críticas.

#### Funcionário

Pode:

- Ver e atualizar chamados atribuídos.
- Comentar chamados.
- Ver reservas, se permitido.
- Não deve acessar dados financeiros futuros sem permissão.

#### Morador

Pode:

- Ver comunicados publicados.
- Confirmar leitura.
- Abrir chamados.
- Comentar nos próprios chamados.
- Ver documentos liberados.
- Solicitar reservas.
- Ver suas próprias reservas.

#### Proprietário

Pode:

- Tudo de morador, se residir.
- Ver documentos e prestações de contas permitidas ao proprietário.
- Pode ter unidades vinculadas sem residir.

#### Inquilino

Pode:

- Acessar recursos de morador conforme vínculo com unidade.
- Algumas permissões podem ser diferentes das de proprietário.

### 9.2. Regra central

Permissão deve considerar:

1. Usuário autenticado.
2. Condomínio ativo.
3. Membership ativa.
4. Papel no condomínio.
5. Vínculo com unidade, quando aplicável.
6. Permissão específica do objeto, quando aplicável.

---

## 10. Comunicação oficial

### 10.1. Entidades

#### AnnouncementCategory

Campos:

- id.
- condominium_id.
- name.
- color.
- is_active.

#### Announcement

Campos:

- id.
- condominium_id.
- category_id.
- title.
- content.
- status.
- is_pinned.
- published_at.
- expires_at.
- created_by_id.
- created_at.
- updated_at.

Status:

- `DRAFT`.
- `PUBLISHED`.
- `ARCHIVED`.

#### AnnouncementReadReceipt

Campos:

- id.
- announcement_id.
- user_id.
- read_at.

Constraints:

- `unique(announcement_id, user_id)`.

### 10.2. Regras de negócio

- Morador só vê comunicado publicado.
- Rascunho só aparece para síndico/admin.
- Confirmação de leitura deve ser registrada uma vez por usuário.
- Aviso fixado aparece antes dos demais.
- Comunicado arquivado não deve aparecer no mural principal.
- Comunicados devem manter histórico; evitar exclusão física.
- Publicação deve registrar `published_at`.

### 10.3. Fluxo

1. Síndico cria comunicado como rascunho.
2. Síndico revisa.
3. Síndico publica.
4. Moradores visualizam no mural.
5. Sistema registra leitura.
6. Síndico acompanha taxa de leitura.

### 10.4. Critérios de aceite

- Usuário sem membership não acessa comunicado.
- Morador de outro condomínio não acessa comunicado por URL direta.
- Síndico vê rascunhos do próprio condomínio.
- Morador não vê rascunhos.
- Leitura duplicada não cria registros duplicados.
- Dashboard mostra taxa de leitura.

---

## 11. Chamados e ocorrências

### 11.1. Entidades

#### TicketCategory

Campos:

- id.
- condominium_id.
- name.
- description.
- default_priority.
- is_active.

#### Ticket

Campos:

- id.
- condominium_id.
- unit_id.
- category_id.
- title.
- description.
- status.
- priority.
- created_by_id.
- assigned_to_id.
- opened_at.
- resolved_at.
- closed_at.
- created_at.
- updated_at.

Status:

- `OPEN`.
- `IN_PROGRESS`.
- `WAITING_RESIDENT`.
- `RESOLVED`.
- `CLOSED`.
- `CANCELLED`.

Prioridade:

- `LOW`.
- `MEDIUM`.
- `HIGH`.
- `URGENT`.

#### TicketComment

Campos:

- id.
- ticket_id.
- author_id.
- content.
- is_internal.
- created_at.

#### TicketAttachment

Campos:

- id.
- ticket_id.
- uploaded_by_id.
- file.
- original_filename.
- content_type.
- size_bytes.
- created_at.

#### TicketStatusHistory

Campos:

- id.
- ticket_id.
- from_status.
- to_status.
- changed_by_id.
- reason.
- created_at.

### 11.2. Regras de negócio

- Morador pode abrir chamado para unidade vinculada a ele.
- Síndico pode abrir chamado para qualquer unidade.
- Funcionário pode atualizar chamado atribuído.
- Morador só vê chamados dele ou da unidade dele.
- Síndico vê todos do condomínio.
- Conselho vê conforme configuração futura; no MVP pode ver apenas resumo ou todos, conforme decisão de produto.
- Comentário interno só aparece para síndico, admin e funcionário.
- Mudança de status deve gerar histórico.
- Resolver chamado preenche `resolved_at`.
- Fechar chamado preenche `closed_at`.
- Cancelar chamado exige motivo.
- Anexo deve respeitar limite de tamanho e tipos permitidos.

### 11.3. Fluxo

1. Morador abre chamado.
2. Sistema registra status `OPEN`.
3. Síndico classifica e atribui responsável.
4. Responsável muda para `IN_PROGRESS`.
5. Responsável comenta andamento.
6. Chamado é marcado como `RESOLVED`.
7. Morador ou síndico fecha como `CLOSED`.

### 11.4. Critérios de aceite

- Chamado de um condomínio não aparece em outro.
- Status muda apenas por perfil autorizado.
- Histórico é criado a cada mudança.
- Morador não vê comentário interno.
- Upload de arquivo inválido é bloqueado.
- Dashboard contabiliza chamados por status e categoria.

---

## 12. Documentos

### 12.1. Entidades

#### DocumentCategory

Campos:

- id.
- condominium_id.
- name.
- description.
- visibility.
- is_active.

Visibilidade inicial:

- `ALL_RESIDENTS`.
- `OWNERS_ONLY`.
- `COUNCIL_ONLY`.
- `MANAGEMENT_ONLY`.

#### Document

Campos:

- id.
- condominium_id.
- category_id.
- title.
- description.
- file.
- original_filename.
- content_type.
- size_bytes.
- visibility.
- uploaded_by_id.
- is_active.
- created_at.
- updated_at.

#### DocumentAccessLog

Campos:

- id.
- condominium_id.
- document_id.
- user_id.
- action.
- created_at.

Ações:

- `VIEW`.
- `DOWNLOAD`.

### 12.2. Regras de negócio

- Documento sempre pertence a um condomínio.
- Acesso depende de role e visibilidade.
- Download deve registrar log.
- Documento inativo não aparece para moradores.
- Síndico pode ver documentos inativos para fins administrativos.
- Excluir documento deve ser soft delete.
- Futuramente, versionamento pode ser ativado com DocumentVersion.

### 12.3. Critérios de aceite

- Morador sem permissão não acessa documento por URL direta.
- Documento de outro condomínio retorna 404 ou 403.
- Download autorizado gera log.
- Busca respeita tenant e permissão.
- Documento inativo não aparece na listagem pública.

---

## 13. Reservas de áreas comuns

### 13.1. Entidades

#### Amenity

Campos:

- id.
- condominium_id.
- name.
- description.
- capacity.
- requires_approval.
- is_active.

Exemplos:

- Salão de festas.
- Churrasqueira.
- Quadra.
- Piscina.
- Academia.
- Coworking.
- Brinquedoteca.

#### AmenityRule

Campos:

- id.
- amenity_id.
- min_hours_before_reservation.
- max_days_ahead.
- max_reservations_per_unit_month.
- allowed_weekdays.
- start_time.
- end_time.
- terms_text.

#### AmenityBlockedDate

Campos:

- id.
- amenity_id.
- starts_at.
- ends_at.
- reason.
- created_by_id.

#### Reservation

Campos:

- id.
- condominium_id.
- amenity_id.
- unit_id.
- requested_by_id.
- starts_at.
- ends_at.
- status.
- notes.
- approved_by_id.
- approved_at.
- cancelled_by_id.
- cancelled_at.
- cancellation_reason.
- created_at.
- updated_at.

Status:

- `PENDING`.
- `APPROVED`.
- `REJECTED`.
- `CANCELLED`.

### 13.2. Regras de conflito

Uma reserva não pode ser aprovada se houver outra reserva aprovada para a mesma área no mesmo intervalo.

Regra de overlap:

```python
existing.starts_at < new.ends_at and existing.ends_at > new.starts_at
```

Também deve verificar bloqueios:

```python
blocked.starts_at < new.ends_at and blocked.ends_at > new.starts_at
```

### 13.3. Regras de negócio

- Morador só reserva área do próprio condomínio.
- Morador deve estar vinculado a uma unidade ativa.
- Área inativa não pode ser reservada.
- Se `requires_approval=True`, reserva entra como `PENDING`.
- Se `requires_approval=False`, reserva pode entrar como `APPROVED`, desde que não haja conflito.
- Síndico pode aprovar, rejeitar ou cancelar.
- Morador pode cancelar a própria reserva dentro das regras.
- Cancelamento deve guardar motivo quando feito por síndico.
- Limite por unidade deve ser aplicado quando configurado.

### 13.4. Critérios de aceite

- Não permite reserva sobreposta.
- Não permite reserva em data bloqueada.
- Não permite reserva fora do horário permitido.
- Não permite reserva acima do limite mensal por unidade.
- Morador de outro condomínio não acessa reserva.
- Síndico vê calendário completo.
- Morador vê suas reservas e calendário disponível.

---

## 14. Dashboard do síndico

### 14.1. Escopo MVP

O dashboard deve começar simples.

Cards iniciais:

- Total de unidades.
- Moradores ativos.
- Chamados abertos.
- Chamados em andamento.
- Chamados resolvidos no mês.
- Comunicados publicados no mês.
- Taxa média de leitura.
- Reservas do mês.
- Documentos mais acessados.

### 14.2. Regras

- Dados sempre filtrados por condomínio.
- Não criar cubo analítico complexo no MVP.
- Não duplicar dados sem necessidade.
- Usar queries otimizadas e índices.
- Se algum indicador ficar pesado, criar tabela agregada apenas depois de medir.

---

## 15. APIs e URLs

### 15.1. Padrão web

Usar URLs simples para telas:

```text
/auth/login/
/condominiums/select/
/dashboard/
/core/units/
/communication/announcements/
/tickets/
/documents/
/reservations/
```

### 15.2. Padrão API

APIs devem usar versionamento:

```text
/api/v1/condominiums/
/api/v1/units/
/api/v1/announcements/
/api/v1/tickets/
/api/v1/documents/
/api/v1/amenities/
/api/v1/reservations/
```

### 15.3. Respostas de API

Padrão de erro:

```json
{
  "error": {
    "code": "permission_denied",
    "message": "Você não tem permissão para acessar este recurso."
  }
}
```

Padrão de listagem:

```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": []
}
```

---

## 16. Camadas de código

### 16.1. Views

Views devem:

- Receber request.
- Validar autenticação.
- Chamar forms/serializers.
- Chamar services/selectors.
- Retornar template ou response.

Views não devem concentrar regra de negócio complexa.

### 16.2. Selectors

Selectors fazem leitura.

Exemplos:

```python
list_tickets_for_condominium(condominium, filters)
get_ticket_for_user(condominium, user, ticket_id)
list_announcements_for_user(condominium, user)
```

### 16.3. Services

Services fazem escrita e regra de negócio.

Exemplos:

```python
create_ticket(condominium, user, data)
change_ticket_status(condominium, user, ticket, new_status)
publish_announcement(condominium, user, announcement)
request_reservation(condominium, user, data)
approve_reservation(condominium, user, reservation)
```

### 16.4. Forms/Serializers

Forms/serializers devem:

- Validar formato.
- Validar campos obrigatórios.
- Normalizar dados simples.

Não devem carregar regras de permissão complexas.

---

## 17. Segurança e LGPD

### 17.1. Dados pessoais

O sistema pode armazenar:

- Nome.
- E-mail.
- Telefone.
- Vínculo com unidade.
- Papel no condomínio.
- Histórico de ações.
- Documentos e anexos.

Tratar tudo como sensível.

### 17.2. Princípios

- Coletar apenas o necessário.
- Exibir apenas para quem precisa.
- Registrar acesso a documentos sensíveis.
- Permitir desativação de usuários.
- Evitar exclusão física sem política definida.
- Proteger uploads.
- Filtrar todo acesso por condomínio.
- Usar HTTPS em produção.
- Usar cookies seguros em produção.
- Ativar CSRF.
- Validar permissões no backend.

### 17.3. Proibições

O Codex não deve:

- Criar endpoint público sem autenticação para dados internos.
- Expor arquivos por URL direta sem autorização.
- Retornar dados de outro condomínio.
- Logar senha, token ou documento sensível.
- Gravar segredo no Git.
- Criar usuário admin padrão em código.
- Usar `DEBUG=True` em produção.
- Usar `ALLOWED_HOSTS=["*"]` em produção.

### 17.4. Auditoria mínima

Registrar:

- Criação de condomínio.
- Alteração de permissões.
- Convite de usuário.
- Criação/publicação de comunicado.
- Abertura e alteração de chamado.
- Upload/download de documento.
- Aprovação/cancelamento de reserva.
- Alteração de configurações.

---

## 18. Testes obrigatórios

### 18.1. Tipos de teste

Unitários:

- Models.
- Services.
- Selectors.
- Validators.

Integração:

- Views.
- APIs.
- Fluxos completos.

Permissão:

- Acesso por role.
- Acesso entre tenants.
- Acesso por unidade.

Regressão:

- Bugs corrigidos devem ganhar teste.

### 18.2. Testes multi-tenant obrigatórios

Para cada módulo, criar pelo menos um teste que prove:

- Usuário do condomínio A não acessa dados do condomínio B.
- Síndico do condomínio A não gerencia dados do condomínio B.
- Morador só vê dados autorizados.
- Filtro por `condominium_id` está aplicado.

### 18.3. Checklist de teste por módulo

Comunicação:

- Criar rascunho.
- Publicar comunicado.
- Morador visualiza comunicado publicado.
- Morador não visualiza rascunho.
- Confirmação de leitura não duplica.

Chamados:

- Morador abre chamado.
- Síndico altera status.
- Comentário interno não aparece ao morador.
- Histórico de status é criado.
- Anexo inválido é bloqueado.

Documentos:

- Upload funciona.
- Permissão de visibilidade é respeitada.
- Download gera log.
- Documento de outro condomínio é bloqueado.

Reservas:

- Reserva sem conflito é criada.
- Reserva sobreposta é bloqueada.
- Reserva em data bloqueada é bloqueada.
- Aprovação altera status.
- Cancelamento registra motivo.

---

## 19. Critérios de pronto

Uma tarefa só está pronta quando:

1. Código implementado.
2. Regras de permissão aplicadas.
3. Tenant aplicado em todas as queries.
4. Testes relevantes criados ou atualizados.
5. Migração criada, se necessário.
6. Admin Django atualizado, se necessário.
7. UI mínima funcional, se for tela.
8. Mensagens de erro amigáveis.
9. Nenhum segredo no código.
10. Checklist de impacto preenchido.

---

## 20. Estratégia de deploy

### 20.1. Ambiente local

Usar Docker Compose com:

- app Django.
- PostgreSQL.
- Redis.
- Mailhog ou equivalente para e-mails locais.

### 20.2. Variáveis de ambiente

`.env.example` deve conter:

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=
DJANGO_ALLOWED_HOSTS=
DATABASE_URL=
REDIS_URL=
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
STORAGE_BACKEND=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
```

### 20.3. Produção inicial

Pode usar:

- VPS simples.
- Docker.
- PostgreSQL gerenciado ou container com backup.
- Nginx/Caddy como reverse proxy.
- HTTPS.
- Backup diário do banco.
- Backup de arquivos enviados.

### 20.4. Comandos de release

Pipeline básico:

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
pytest
```

---

## 21. Roadmap técnico recomendado

### Fase 1 — Fundação

Entregas:

- Projeto Django.
- Docker.
- Settings por ambiente.
- User customizado ou decisão explícita de usar User padrão.
- Login/logout.
- Core multi-tenant.
- Condominium, Block, Unit.
- Membership e roles.
- Middleware de condomínio ativo.
- Admin básico.
- Testes de isolamento entre condomínios.

### Fase 2 — Comunicação

Entregas:

- Categorias.
- CRUD de comunicados.
- Publicação.
- Mural.
- Confirmação de leitura.
- Indicador de leitura.
- Testes de permissão.

### Fase 3 — Chamados

Entregas:

- Categorias.
- Abertura de chamado.
- Listagem por perfil.
- Comentários.
- Anexos.
- Mudança de status.
- Histórico.
- Dashboard básico de chamados.

### Fase 4 — Documentos

Entregas:

- Categorias.
- Upload.
- Visibilidade por perfil.
- Download autorizado.
- Log de acesso.
- Busca simples.

### Fase 5 — Reservas

Entregas:

- Cadastro de áreas.
- Regras.
- Calendário/listagem.
- Solicitação.
- Aprovação/rejeição.
- Bloqueio de conflito.
- Histórico.

### Fase 6 — Dashboard MVP

Entregas:

- Cards principais.
- Filtros por período.
- Indicadores por condomínio.
- Queries otimizadas.

---

## 22. O que não fazer agora

Não implementar no MVP:

- Boleto.
- Integração bancária.
- Inadimplência.
- Contabilidade completa.
- Assembleia digital formal.
- Assinatura digital.
- App mobile nativo.
- Push notification nativo.
- WhatsApp integrado.
- Portaria completa.
- QR Code de acesso.
- IA em documentos.
- BI avançado externo.
- Customizações por cliente além de configurações simples.
- Marketplace.
- Gestão de fornecedores complexa.

Esses itens podem aparecer no código apenas como comentários de roadmap ou ADR, não como implementação ativa.

---

## 23. Padrão de trabalho do Codex

Para cada tarefa, o Codex deve seguir este ritual:

### 23.1. Entender

Ler:

- `CODEX.md`.
- `README.md`.
- Arquivos do app afetado.
- Models relacionados.
- Tests existentes.
- URLs/forms/templates relacionados.

### 23.2. Planejar

Antes de alterar, definir:

- Arquivos que serão alterados.
- Entidades afetadas.
- Riscos de permissão.
- Riscos multi-tenant.
- Testes necessários.

### 23.3. Implementar

Fazer a menor alteração suficiente.

Não refatorar o projeto inteiro para resolver uma tarefa pequena.

### 23.4. Testar

Executar testes relevantes.

Se não puder executar, explicar exatamente por quê.

### 23.5. Reportar

Ao final, responder:

- O que foi alterado.
- Arquivos principais.
- Como testar.
- Riscos/pendências.
- Próximo passo recomendado.

---

## 24. Prompt mestre para usar com Codex

Use este prompt no início das sessões de desenvolvimento:

```text
Você está trabalhando no Sistema Modular de Administração de Condomínios.

Antes de alterar qualquer código, leia o arquivo CODEX.md e respeite o escopo do MVP.

O sistema é um monólito Django modular, multi-tenant por condomínio, com foco inicial em:
- Core;
- Comunicação;
- Chamados;
- Documentos;
- Reservas;
- Dashboard simples do síndico.

Regras obrigatórias:
- Todo dado de negócio deve ser filtrado por condomínio.
- Nunca permita acesso cruzado entre condomínios.
- Permissões devem ser aplicadas no backend.
- Não implemente boleto, banco, assembleia formal, app nativo, portaria completa ou IA avançada no MVP.
- Use services/selectors para regras de negócio.
- Crie ou atualize testes relevantes.
- Ao final, explique alterações, arquivos afetados e como validar.

Agora execute a tarefa descrita mantendo o escopo controlado:
[TAREFA AQUI]
```

---

## 25. Exemplos de tarefas bem formuladas para Codex

### 25.1. Core

```text
Implemente os models iniciais do app core:
Condominium, Block, Unit, CondominiumMembership e UnitOccupancy.

Use UUID, timestamps, is_active, constraints por condomínio e testes garantindo que unidades de condomínios diferentes não se misturam.
Não implemente módulos futuros.
```

### 25.2. Comunicação

```text
Implemente o módulo de comunicados com AnnouncementCategory, Announcement e AnnouncementReadReceipt.

Inclua status DRAFT, PUBLISHED e ARCHIVED.
Moradores só podem ver comunicados publicados do próprio condomínio.
Síndico pode criar rascunho e publicar.
Crie testes de permissão e isolamento multi-tenant.
```

### 25.3. Chamados

```text
Implemente o fluxo básico de chamados:
TicketCategory, Ticket, TicketComment e TicketStatusHistory.

Morador abre chamado para unidade vinculada.
Síndico vê todos os chamados do condomínio.
Morador só vê chamados próprios ou da sua unidade.
Toda mudança de status deve gerar histórico.
Crie testes.
```

### 25.4. Documentos

```text
Implemente documentos com categoria, upload, visibilidade por perfil e log de download.

O download deve validar permissão no backend.
Não exponha arquivo diretamente por URL pública.
Crie testes para bloquear acesso entre condomínios.
```

### 25.5. Reservas

```text
Implemente reserva de áreas comuns com Amenity, AmenityRule, AmenityBlockedDate e Reservation.

Bloqueie reservas sobrepostas.
Bloqueie reservas em datas bloqueadas.
Se a área exigir aprovação, criar reserva como PENDING.
Se não exigir, criar como APPROVED quando não houver conflito.
Crie testes.
```

---

## 26. Padrões de UI

### 26.1. Princípios

- Interface simples.
- Poucos cliques.
- Textos claros.
- Mobile-first/responsivo.
- Não parecer ERP pesado.
- Foco no síndico e morador comum.

### 26.2. Telas MVP

Obrigatórias:

- Login.
- Seleção de condomínio.
- Dashboard.
- Lista de unidades.
- Lista de moradores.
- Mural de comunicados.
- Criar/editar comunicado.
- Lista de chamados.
- Abrir chamado.
- Detalhe do chamado.
- Lista de documentos.
- Upload de documento.
- Lista/calendário de reservas.
- Solicitar reserva.
- Aprovar reserva.

### 26.3. Mensagens

Evitar mensagens técnicas.

Ruim:

```text
IntegrityError duplicate key value violates unique constraint.
```

Bom:

```text
Já existe uma unidade com este número neste bloco.
```

---

## 27. Índices e performance

### 27.1. Índices recomendados

Criar índices para:

- `condominium_id`.
- `created_at`.
- `status`.
- `category_id`.
- `unit_id`.
- `user_id`.
- `published_at`.
- `starts_at` e `ends_at` em reservas.

### 27.2. Cuidados

- Evitar N+1 queries.
- Usar `select_related` e `prefetch_related`.
- Paginar listas.
- Não carregar anexos pesados em listagens.
- Não calcular dashboard com loops em Python se puder usar agregação SQL.

---

## 28. Administração interna

Usar Django Admin para suporte técnico inicial, mas não depender dele como produto final.

Admin deve permitir:

- Ver condomínios.
- Ver usuários.
- Ver memberships.
- Ver logs.
- Ver entidades principais.

Admin não substitui telas do síndico.

---

## 29. Documentação que deve existir no repositório

Criar e manter:

```text
README.md
CODEX.md
docs/product/strategy.md
docs/technical/architecture.md
docs/technical/security.md
docs/technical/testing.md
docs/adr/0001-django-monolith.md
docs/adr/0002-row-based-multitenancy.md
docs/adr/0003-mvp-scope.md
```

ADR significa Architecture Decision Record.

Cada ADR deve conter:

- Contexto.
- Decisão.
- Alternativas consideradas.
- Consequências.

---

## 30. Decisões já tomadas

1. O produto será modular.
2. O Core é obrigatório.
3. O MVP terá Core, Comunicação, Chamados, Documentos, Reservas e Dashboard simples.
4. O sistema será web responsivo antes de app nativo.
5. A arquitetura inicial será monólito Django modular.
6. O banco será PostgreSQL.
7. O multi-tenant inicial será por linha com `condominium_id`.
8. Segurança e LGPD entram desde o primeiro commit.
9. O sistema não tentará competir com ERP completo no início.
10. O foco é validar uso real e pagamento antes de escalar.

---

## 31. Decisões em aberto

Estas decisões precisam ser confirmadas antes ou durante o desenvolvimento:

1. Nome comercial do produto.
2. Identidade visual.
3. Domínio.
4. Política de cobrança.
5. Se haverá subdomínio por condomínio no futuro.
6. Limite de armazenamento por plano.
7. Política de retenção de dados.
8. Quem pode ver chamados: conselho vê todos ou apenas indicadores?
9. Proprietário não residente terá quais acessos?
10. Inquilino poderá reservar áreas comuns sem aprovação do proprietário?
11. Documentos financeiros entram no MVP ou ficam para evolução?
12. Reservas terão termo de aceite?
13. Notificação por e-mail entra no MVP ou depois?

Quando uma decisão estiver em aberto, o Codex deve implementar a opção mais simples e segura, ou deixar explícito como configuração.

---

## 32. Checklist anti-vazamento multi-tenant

Antes de finalizar qualquer PR/tarefa, verificar:

- [ ] Todas as queries de listagem filtram por condomínio.
- [ ] Todos os detalhes buscam objeto por condomínio.
- [ ] Forms não aceitam IDs de outro condomínio.
- [ ] Serializers validam relações com o mesmo condomínio.
- [ ] Admin está protegido.
- [ ] Teste tenta acessar objeto de outro condomínio.
- [ ] Upload/download valida permissão.
- [ ] Dashboard filtra por condomínio.
- [ ] Logs incluem condomínio quando aplicável.

---

## 33. Checklist de segurança

- [ ] CSRF ativo.
- [ ] Autenticação exigida.
- [ ] Permissão no backend.
- [ ] Arquivos protegidos.
- [ ] Validação de tipo/tamanho de upload.
- [ ] Sem segredo no código.
- [ ] Sem debug em produção.
- [ ] Logs sem dados sensíveis.
- [ ] Erros amigáveis.
- [ ] Auditoria para ações sensíveis.

---

## 34. Checklist de MVP

O MVP só pode ser considerado pronto quando:

- [ ] Login funciona.
- [ ] Usuário acessa apenas condomínios vinculados.
- [ ] Síndico cadastra blocos e unidades.
- [ ] Síndico cadastra/convida moradores.
- [ ] Síndico publica comunicado.
- [ ] Morador lê comunicado.
- [ ] Sistema registra leitura.
- [ ] Morador abre chamado.
- [ ] Síndico gerencia chamado.
- [ ] Sistema guarda histórico do chamado.
- [ ] Síndico sobe documento.
- [ ] Morador acessa documento permitido.
- [ ] Sistema bloqueia documento sem permissão.
- [ ] Morador solicita reserva.
- [ ] Sistema bloqueia reserva conflitante.
- [ ] Síndico aprova reserva.
- [ ] Dashboard mostra indicadores simples.
- [ ] Testes multi-tenant passam.
- [ ] Deploy inicial funciona.
- [ ] Backup definido.
- [ ] Termos e política de privacidade preparados antes de cliente real.

---

## 35. Norte técnico final

O Codex deve construir este sistema como um produto real, não como protótipo descartável.

A prioridade é:

1. Segurança.
2. Separação entre condomínios.
3. Simplicidade.
4. Histórico e auditoria.
5. Usabilidade para síndico e morador.
6. Código limpo.
7. Testes.
8. Evolução modular.

Sempre que houver conflito entre fazer algo sofisticado e fazer algo seguro/simples, escolher o seguro e simples.

O objetivo não é construir tudo.  
O objetivo é construir certo o suficiente para validar com condomínios reais.
