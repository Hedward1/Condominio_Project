# Demo Guiada MVP 0.1

Roteiro para uma demonstracao de 5 a 10 minutos do Condominio Project, usando o condominio criado pela seed demo.

## Objetivo da Demo

Mostrar que o MVP ja resolve a rotina operacional basica de um condominio pequeno ou medio:

- o sindico gerencia a base do condominio;
- o morador acessa comunicados, chamados, documentos e reservas;
- as areas administrativas ficam restritas ao gestor;
- os dados sao separados por condominio;
- acoes sensiveis ficam auditadas.

Nao vender nesta demo: boleto, banco, inadimplencia, assembleia formal, app nativo, portaria, notificacoes externas, WhatsApp ou IA.

## Preparacao

Use a versao marcada:

```powershell
git checkout v0.1.0-mvp
```

Prepare o banco e a seed:

```powershell
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo_condominium
.\.venv\Scripts\python manage.py runserver
```

Credenciais padrao:

- Sindico: `sindico.demo@example.com`
- Morador: `morador.demo@example.com`
- Senha: `Demo@12345`

Em ambiente compartilhado, rode a seed com uma senha propria:

```powershell
.\.venv\Scripts\python manage.py seed_demo_condominium --password "SENHA-DEMO-AQUI"
```

Antes de apresentar:

- abrir `http://127.0.0.1:8000/auth/login/`;
- deixar uma janela anonima ou outro navegador separado para o morador;
- confirmar que o condominio ativo e `Condominio Demo`;
- conferir se o dashboard carrega sem erro.

## Narrativa de Abertura

"Este MVP organiza a rotina principal do condominio em um portal unico. O sindico tem uma visao administrativa para manter cadastros, comunicados, chamados, documentos e reservas. O morador tem uma visao simples para acompanhar comunicados oficiais, abrir chamados, acessar documentos autorizados e solicitar reservas."

## Roteiro de 5 a 10 Minutos

### 1. Login e Dashboard do Sindico

Tempo sugerido: 1 minuto.

1. Entrar com `sindico.demo@example.com`.
2. Selecionar ou confirmar o `Condominio Demo`.
3. Abrir o Dashboard.
4. Mostrar os indicadores:
   - unidades;
   - moradores ativos;
   - comunicados no mes;
   - leitura dos comunicados;
   - chamados abertos;
   - documentos ativos;
   - reservas pendentes/aprovadas.

Mensagem para falar:

"O dashboard nao tenta ser BI completo. Ele mostra o basico para o sindico saber onde precisa agir."

### 2. Core Administrativo

Tempo sugerido: 1 minuto.

1. Abrir `Blocos`.
2. Mostrar `Bloco A`.
3. Abrir `Unidades`.
4. Mostrar unidade `101`.
5. Abrir `Membros`.
6. Mostrar sindico e morador.
7. Abrir `Moradores por Unidade`.
8. Mostrar o vinculo do morador com a unidade.

Mensagem para falar:

"A base do condominio fica estruturada antes dos modulos operacionais. Isso evita planilhas soltas e permite controlar permissao por condominio e unidade."

### 3. Comunicacao Oficial

Tempo sugerido: 1 a 2 minutos.

1. Abrir `Gerenciar Comunicados`.
2. Mostrar comunicado publicado `Bem-vindo ao portal do condominio`.
3. Explicar estados: rascunho, publicado e arquivado.
4. Abrir `Comunicados` como mural do morador ou em outra aba.
5. Mostrar que o comunicado publicado aparece no mural.

Mensagem para falar:

"A comunicacao oficial sai do WhatsApp e vira historico do condominio. O morador ve apenas comunicados publicados, e a leitura pode ser registrada."

### 4. Chamados e Ocorrencias

Tempo sugerido: 1 a 2 minutos.

1. Como morador, abrir `Meus Chamados`.
2. Mostrar chamado demo `Lampada queimada no corredor`.
3. Opcional: criar um chamado novo simples.
4. Como sindico, abrir `Gerenciar Chamados`.
5. Mostrar filtros por status, prioridade e categoria.
6. Abrir o detalhe do chamado e mostrar a gestao administrativa.

Mensagem para falar:

"Chamados viram um canal oficial de demanda. O morador acompanha os proprios chamados; o sindico gerencia tudo do condominio."

### 5. Documentos

Tempo sugerido: 1 minuto.

1. Como sindico, abrir `Gerenciar Documentos`.
2. Mostrar documento `Regimento interno demo`.
3. Explicar visibilidade: publico para moradores ou somente gestores.
4. Como morador, abrir `Documentos`.
5. Abrir o documento publico.
6. Fazer download pelo botao da tela.

Mensagem para falar:

"O arquivo nao e exposto por link direto. O download passa por uma view protegida, respeitando permissao e condominio ativo."

### 6. Reservas

Tempo sugerido: 1 a 2 minutos.

1. Como morador, abrir `Reservas`.
2. Mostrar reserva demo aprovada do `Salao de festas`.
3. Opcional: solicitar uma nova reserva.
4. Como sindico, abrir `Gerenciar Reservas`.
5. Mostrar filtros por status e area comum.
6. Explicar aprovacao, rejeicao, cancelamento e bloqueio de sobreposicao.

Mensagem para falar:

"A reserva passa a ter fluxo formal. O sistema evita aprovar conflitos de horario para a mesma area."

### 7. Fechamento

Tempo sugerido: 30 segundos.

Mensagem final:

"Esta versao 0.1 cobre o ciclo operacional principal: cadastro, comunicacao, chamados, documentos, reservas, dashboard e auditoria. O foco agora e homologar com usuarios reais, ajustar usabilidade e preparar deploy com seguranca."

## Roteiro Curto de 5 Minutos

Se o tempo estiver apertado:

1. Dashboard do sindico.
2. Core: unidade, membro e morador por unidade.
3. Comunicados: publicar/mural/leitura.
4. Chamados: morador abre, sindico gerencia.
5. Documentos: download protegido.
6. Reservas: solicitacao e aprovacao.

## Roteiro Completo de 10 Minutos

Se houver mais tempo:

1. Login do sindico e dashboard.
2. Core completo: blocos, unidades, membros e moradores por unidade.
3. Gestao de categorias de comunicados.
4. Comunicado publicado no mural do morador.
5. Chamado do morador e visao administrativa do sindico.
6. Documento publico e mencao a documento somente gestores.
7. Reserva aprovada e regra de conflito.
8. Troca para perfil de morador e tentativa de observar que menus administrativos nao aparecem.
9. Fechamento com status MVP 0.1.

## Pontos de Validacao Durante a Demo

- O morador nao deve ver links administrativos.
- O morador deve ver apenas documentos publicos.
- O morador deve ver apenas os proprios chamados.
- Comunicados em rascunho nao aparecem no mural do morador.
- Downloads devem passar pela tela do sistema, nao por URL direta de media.
- A demo deve permanecer no `Condominio Demo`.

## Perguntas Esperadas

### Da para usar em mais de um condominio?

Sim. O modelo e multi-tenant por condominio. Cada dado operacional pertence a um condominio e as consultas de negocio sao filtradas pelo condominio ativo.

### Ja tem boleto ou financeiro?

Nao nesta versao. Isso ficou fora do MVP para manter o produto simples, seguro e validavel.

### O morador recebe notificacao?

Nao nesta versao. O MVP mostra o mural e os fluxos internos; notificacoes externas ficam para evolucao posterior.

### O arquivo fica publico?

Nao. O modulo de documentos usa download protegido pela aplicacao, com validacao de permissao.

### Ja esta pronto para cliente real?

Esta pronto para demonstracao e homologacao. Antes de producao real, ainda precisa revisar infraestrutura, backups, dominio, HTTPS, termos de uso, politica de privacidade e operacao.

## Checklist Pos-Demo

Registrar feedback sobre:

- clareza da navegacao;
- termos usados nas telas;
- fluxo de abertura e acompanhamento de chamado;
- facilidade para encontrar comunicados;
- entendimento de documentos restritos;
- fluxo de reserva;
- indicadores que o sindico realmente quer ver primeiro.

Evitar transformar feedback em modulo novo imediatamente. Priorizar ajustes de usabilidade, seguranca e deploy antes de expandir escopo.
