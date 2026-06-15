# Manual do Codex — Condominio Project

Este arquivo é a fonte principal de orientação para o Codex e para qualquer agente de desenvolvimento que atuar neste repositório.

O documento completo de produto e arquitetura base está em:

- `Base_documenation/CODEX_MANUAL_CONDOMINIO.md`
- `Base_documenation/Planejamento de Produto - Sistema Modular de Administracao de Condominios.pdf`

## Missão do projeto

Construir uma plataforma web modular para administração de condomínios, voltada inicialmente para síndicos moradores, pequenos e médios condomínios, conselhos e administradores pequenos.

O sistema deve reduzir dependência de WhatsApp, planilhas, papel, conversas soltas e documentos espalhados.

## Escopo obrigatório do MVP

O MVP deve conter apenas:

1. Core do condomínio.
2. Cadastro de blocos, unidades, moradores, proprietários, inquilinos, síndico, conselho e funcionários.
3. Comunicação oficial.
4. Chamados e ocorrências.
5. Documentos.
6. Reservas de áreas comuns.
7. Dashboard simples do síndico.

## Fora do MVP

Não implementar sem autorização explícita:

- Boleto.
- Integração bancária.
- Inadimplência.
- Contabilidade completa.
- Assembleia digital formal.
- Assinatura digital.
- App mobile nativo.
- Portaria completa.
- QR Code de acesso.
- WhatsApp integrado.
- IA em documentos.
- BI avançado externo.
- Customizações profundas por cliente.

## Arquitetura definida

A arquitetura inicial é um monólito Django modular.

Stack prevista:

- Python.
- Django.
- Django REST Framework.
- PostgreSQL.
- Docker.
- Pytest.
- Ruff.
- Django Templates com HTMX ou frontend responsivo simples.

## Multi-tenancy

A separação inicial será por linha, usando `condominium_id` nas tabelas de negócio.

Regra absoluta:

> Nenhum dado operacional pode ser lido, criado, alterado ou excluído sem escopo de condomínio.

Errado:

```python
Ticket.objects.get(id=ticket_id)
```

Certo:

```python
Ticket.objects.get(id=ticket_id, condominium=request.condominium)
```

Melhor ainda:

```python
get_ticket_for_condominium(ticket_id=ticket_id, condominium=request.condominium)
```

## Apps planejados

```text
apps/
├── common/          # bases, mixins, validators e helpers
├── accounts/        # usuário, autenticação e convites
├── core/            # condomínio, blocos, unidades, vínculos e permissões
├── audit/           # logs de auditoria
├── communication/   # comunicados oficiais
├── tickets/         # chamados e ocorrências
├── documents/       # documentos e permissões de acesso
├── reservations/    # áreas comuns e reservas
└── dashboard/       # indicadores simples do síndico
```

## Padrão de código

Usar separação por camadas:

- `models.py`: estrutura de dados e constraints.
- `selectors.py`: leituras e consultas filtradas por condomínio.
- `services.py`: escritas e regras de negócio.
- `forms.py` ou `serializers.py`: validação de entrada.
- `views.py`: orquestração da requisição.
- `tests/`: testes unitários e de integração.

Views não devem concentrar regra de negócio complexa.

## Segurança e LGPD

Regras obrigatórias:

1. Nunca vazar dados entre condomínios.
2. Validar permissões no backend.
3. Nunca salvar segredo no código.
4. Nunca expor upload por URL pública sem autorização.
5. Registrar ações sensíveis em `AuditLog`.
6. Usar soft delete para entidades de negócio quando fizer sentido.
7. Tratar dados pessoais como sensíveis.
8. Não usar `DEBUG=True` em produção.
9. Não usar `ALLOWED_HOSTS=["*"]` em produção.
10. Não logar senha, token ou documentos sensíveis.

## Testes obrigatórios

Toda feature deve ter testes relevantes.

Prioridade dos testes:

1. Isolamento entre condomínios.
2. Permissões por perfil.
3. Regras de negócio nos services.
4. Selectors sempre filtrando por condomínio.
5. Auditoria em ações sensíveis.
6. Fluxos principais do usuário.

Teste multi-tenant mínimo por módulo:

- Usuário do condomínio A não acessa dados do condomínio B.
- Síndico do condomínio A não gerencia dados do condomínio B.
- Morador só vê dados autorizados.

## Critério de pronto

Uma tarefa só está pronta quando:

- Código implementado.
- Permissões aplicadas no backend.
- Queries filtradas por condomínio.
- Testes criados ou atualizados.
- Migrações criadas quando necessário.
- Erros amigáveis.
- Nenhum segredo exposto.
- Documentação atualizada quando necessário.

## Ritual de trabalho do Codex

Antes de alterar código:

1. Ler este arquivo.
2. Ler o README.
3. Ler os docs técnicos relacionados.
4. Verificar models, services, selectors e testes existentes.
5. Identificar riscos de tenant, permissão e LGPD.

Durante a implementação:

1. Fazer a menor alteração suficiente.
2. Evitar refatorações grandes sem necessidade.
3. Usar services para escrita.
4. Usar selectors para leitura.
5. Não implementar módulos fora do MVP.

Ao finalizar:

1. Explicar o que mudou.
2. Listar arquivos alterados.
3. Informar testes executados.
4. Apontar riscos ou pendências.
5. Sugerir o próximo passo técnico.

## Prompt mestre para sessões do Codex

```text
Você está trabalhando no Condominio Project.

Antes de alterar qualquer código, leia o arquivo CODEX.md e respeite o escopo do MVP.

O sistema é um monólito Django modular, multi-tenant por condomínio, com foco inicial em:
- Core;
- Comunicação oficial;
- Chamados e ocorrências;
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

## Norte final

O objetivo não é construir tudo.

O objetivo é construir certo o suficiente para validar com condomínios reais, mantendo segurança, simplicidade, separação entre tenants e evolução modular.
