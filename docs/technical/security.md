# Segurança, Permissões e LGPD

## Prioridade máxima

A principal regra de segurança do sistema é:

> Nunca permitir vazamento de dados entre condomínios.

O produto será multi-tenant, então qualquer falha de filtro por condomínio pode expor dados de moradores, unidades, documentos, chamados e reservas de outro cliente.

## Regras obrigatórias

1. Todo dado operacional deve ter escopo de condomínio.
2. Toda query de negócio deve filtrar por condomínio.
3. Permissões devem ser aplicadas no backend.
4. Uploads e downloads devem passar por autorização.
5. Ações sensíveis devem gerar `AuditLog`.
6. Segredos devem ficar fora do código.
7. Dados pessoais devem ser tratados como sensíveis.
8. Erros técnicos não devem aparecer para o usuário final.

## Dados sensíveis esperados

O sistema pode armazenar:

- Nome.
- E-mail.
- Telefone.
- Unidade.
- Papel no condomínio.
- Histórico de chamados.
- Comentários.
- Anexos.
- Documentos condominiais.
- Logs de acesso.

## Permissões

Permissão deve considerar:

1. Usuário autenticado.
2. Condomínio ativo.
3. Membership ativa.
4. Papel do usuário no condomínio.
5. Vínculo com unidade.
6. Permissão específica do objeto.

## Perfis iniciais

- Superadmin da plataforma.
- Síndico.
- Conselho.
- Funcionário.
- Morador.
- Proprietário.
- Inquilino.

## Ações que devem gerar auditoria

- Criação ou alteração de condomínio.
- Convite de usuário.
- Alteração de perfil/permissão.
- Publicação de comunicado.
- Abertura e alteração de chamado.
- Upload e download de documento.
- Aprovação, rejeição ou cancelamento de reserva.
- Alteração de configurações.

## Uploads e documentos

Não expor arquivos diretamente por URL pública.

Downloads devem passar por view/service que valide:

- Usuário autenticado.
- Condomínio ativo.
- Membership ativa.
- Permissão para ver aquele documento.
- Documento ativo.

## Configuração de produção

Em produção:

- `DEBUG=False`.
- `DJANGO_SECRET_KEY` obrigatório.
- `ALLOWED_HOSTS` explícito.
- HTTPS obrigatório.
- Cookies seguros.
- CSRF ativo.
- HSTS habilitado.
- Logs sem dados sensíveis.

## Proibições

O Codex não deve:

- Criar endpoint público para dados internos.
- Buscar objeto de negócio só por `id`.
- Expor uploads sem autorização.
- Logar senha, token ou documentos sensíveis.
- Salvar `.env` no repositório.
- Criar usuário admin padrão no código.
- Usar `ALLOWED_HOSTS=["*"]` em produção.
- Deixar `DEBUG=True` em produção.

## Checklist de segurança por tarefa

- [ ] Query filtrada por condomínio.
- [ ] Permissão validada no backend.
- [ ] Usuário sem acesso recebe 403 ou 404.
- [ ] Acesso entre condomínios foi testado.
- [ ] Upload/download protegido, se aplicável.
- [ ] Ação sensível gera log.
- [ ] Nenhum segredo foi adicionado ao código.
- [ ] Erros são amigáveis.
