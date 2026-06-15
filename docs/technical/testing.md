# Estratégia de Testes

O projeto deve usar `pytest` e `pytest-django`.

A prioridade dos testes é garantir que cada condomínio veja apenas os próprios dados e que permissões sejam aplicadas no backend.

## Categorias obrigatórias

- Isolamento multi-tenant.
- Permissões por perfil.
- Regras de negócio em services.
- Selectors filtrando por condomínio.
- Logs de auditoria.
- Fluxos principais de usuário.

## Regra mínima por módulo

Todo módulo operacional deve ter pelo menos um teste provando que dados de um condomínio não aparecem para usuários de outro condomínio.

## Core

Testar:

- Criação de condomínio.
- Criação de bloco.
- Criação de unidade.
- Criação de membership.
- Listagem apenas de condomínios vinculados ao usuário.

## Comunicação

Testar:

- Criação de rascunho.
- Publicação de comunicado.
- Visualização por morador.
- Bloqueio de rascunho para morador.
- Registro único de leitura.

## Chamados

Testar:

- Abertura de chamado.
- Listagem por perfil.
- Alteração de status.
- Histórico de status.
- Comentários internos visíveis apenas para perfis autorizados.

## Documentos

Testar:

- Upload.
- Visibilidade por perfil.
- Download autorizado.
- Log de acesso.
- Bloqueio de documento sem permissão.

## Reservas

Testar:

- Solicitação de reserva.
- Bloqueio de reserva sobreposta.
- Bloqueio de data indisponível.
- Aprovação pelo síndico.
- Cancelamento com histórico.

## Dashboard

Testar:

- Indicadores filtrados por condomínio.
- Contagem de chamados.
- Contagem de reservas.
- Taxa de leitura de comunicados.

## Comando principal

```powershell
.\.venv\Scripts\python -m pytest
```

## Critério de pronto

Uma tarefa só deve ser considerada pronta quando:

- Testes relevantes foram criados ou atualizados.
- Permissões foram testadas.
- Isolamento multi-tenant foi testado.
- Bugs corrigidos ganharam teste de regressão.
- Se algum teste não pôde ser executado, isso foi documentado.
