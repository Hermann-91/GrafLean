# 📋 Registro de Alterações (Changelog)

Todas as alterações relevantes do **GrafLean** são documentadas neste arquivo, seguindo as diretrizes do padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e aderindo ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [2.3.0] - 2026-09-26

### 🤖 Experiência IA (Fase E)
- **Cápsula de Status "AI Working" no Header**:
  - Badge dinâmico com ponto pulsante neon (`@keyframes ai-pulse`) e exibição do arquivo e ação em execução (`CRIANDO`, `EDITANDO`, `ANALISANDO`).
  - Transição de conclusão suave (`✅ IA: Concluído`).
- **Animações Semânticas Locais no Vis.js**:
  - **Criação de Nós (`node_created`):** Animação fluida de scale-in (tamanho inicial reduzido expandindo suavemente) sem disparar física global.
  - **Modificação (`node_changed`):** Pulso luminoso âmbar temporário destacando a alteração.
  - **Exclusão (`node_deleted`):** Dissolução avermelhada suave de 350ms antes da remoção definitiva do dataset.
  - **Transição Pós-Commit:** Esmaecimento gradual dos anéis de alteração para as cores estruturais do Code Graph.
- **Histórico de Operações da IA (Timeline & Gaveta de Auditoria)**:
  - Buffer circular em memória no `ChangeManager` retendo as últimas 50 operações sem risco de vazamento de memória.
  - Gaveta retrátil no frontend (`ai-history-drawer`) com atalho <kbd>Ctrl</kbd>+<kbd>H</kbd> / <kbd>Cmd</kbd>+<kbd>H</kbd>, exibindo horário, status e links clicáveis para abrir o código no editor e focar no grafo.
- **Novos Endpoints HTTP**:
  - `GET /api/ai-history`: Retorna o log cronológico das ações da IA.
  - `POST /api/ai-history/clear`: Esvazia o histórico sob demanda.
  - `POST /api/ai-state`: Suporte ao campo opcional `message` com descrição contextual.

### 🎨 Refinamentos, Ergonomia & Acessibilidade (Fase F)
- **Mini-Map de Alterações na Perspectiva IA / Git**:
  - Card compacto com barras de proporção semânticas (verde=novos, laranja=modificados, rosa=excluídos) demonstrando o impacto das mutações ativas.
- **Clustering Semântico por Diretórios**:
  - Agrupamento em super-nós por pasta/módulo (`📦 Módulos`) para bases massivas com abertura em duplo-clique.
- **Novos Atalhos de Teclado de Alta Produtividade**:
  - <kbd>1</kbd>, <kbd>2</kbd>, <kbd>3</kbd>: Alternância imediata entre as perspectivas `[ CÓDIGO ]`, `[ IA / GIT ]` e `[ IMPACTO ]`.
  - <kbd>Alt</kbd>+<kbd>N</kbd> e <kbd>Alt</kbd>+<kbd>P</kbd>: Navegação sequencial (próxima e anterior) entre arquivos alterados.
  - <kbd>Ctrl</kbd>+<kbd>H</kbd>: Abertura/fechamento da gaveta de histórico da IA.
- **Telemetria de FPS & Acessibilidade**:
  - Monitor leve de taxa de quadros (FPS) no rodapé do workspace.
  - Respeito integral à preferência de acessibilidade do sistema operacional (`prefers-reduced-motion: reduce`).

### 🧪 Testes Automatizados
- Expansão da suíte para **91 testes automatizados** com 100% de sucesso em ~2.1s.

---

## [2.2.0] - 2026-09-26

### 🚀 Arquitetura & Alta Performance
- **Modularização Arquitetural do `visualizer.py`**:
  - Eliminação da dívida técnica do arquivo monolítico de 3.398 linhas.
  - Criação do pacote modular `core/visualizer/`:
    - `data_serializer.py`: classe `GraphDataSerializer` com métodos dedicados e sanitização estrita (RFC 8259).
    - `template_engine.py`: classe `TemplateEngine` com carregamento único e cache em memória (zero leitura repetida de disco em tempo de execução).
    - `visualizer.py`: orquestrador desacoplado `ArchitectureVisualizer` mantendo 100% de retrocompatibilidade com a API pública.
    - `assets/`: isolamento limpo de templates (`workspace.html`), estilos (`style.css`) e scripts (`app.js`) sem interpolações frágeis de f-string ou escape de chaves duplas.

### 🧠 Change Manager & Eventos Semânticos SSE (Fase A)
- **Desacoplamento de Estados**:
  - `core/change_manager.py`: separação estrita entre o estado operacional transitório da IA (`idle`, `creating`, `editing`, `analyzing`, `finished`, `error`) e o estado versionado do Git (`untracked`, `modified`, `deleted`, `staged`, `committed`).
- **Eventos Granulares em Tempo Real**:
  - Emissão de patches estruturados via SSE: `node_created`, `node_changed`, `node_deleted`, `edge_added`, `edge_removed`, `ai_state`, `git_status`.
- **Motor de Patches Incrementais no Frontend**:
  - Aplicação direta de alterações via `nodes.add()`, `nodes.update()`, `nodes.remove()`, preservando posições e estabilidade do layout Vis.js sem reconstruir o grafo do zero.
- **Novas Rotas REST**:
  - `POST /api/ai-state`: Permite que assistentes de IA e ferramentas externas sinalizem em tempo real qual arquivo estão criando, editando ou analisando.
  - `POST /api/changes`: Consulta do resumo atual das alterações (contadores de novos, modificados e excluídos).

### 🎨 Change Graph & Abas de Perspectiva (Fase B)
- **Seletor de Perspectivas Triplo**:
  - `[ CÓDIGO ]`: Mapa arquitetural estrutural padrão.
  - `[ IA / GIT ]`: Foco dedicado nas mutações ativas, com código de cores verde (novo), laranja (modificado), vermelho (deletado) e elementos neutros esmaecidos.
  - `[ IMPACTO ]`: Foco isolado na cascata de chamadores e dependências de 1º e 2º grau do nó selecionado.
- **Experiência Visual e Animações da IA**:
  - Efeito luminoso pulsante (`@keyframes ai-pulse`) em nós com operação ativa da IA (`creating` ou `editing`).
  - Suporte a acessibilidade com desativação automática de transições quando `prefers-reduced-motion: reduce` estiver ativo.
- **Change Summary Banner**:
  - Banner dinâmico com contadores em tempo real e botão de navegação facilitada `Próxima Mudança ▶`.

### ⚡ Otimização de Performance e Escala (Fase C)
- **Limite Protetivo de Visualização**:
  - `GRAPH_NODE_LIMIT = 250` com banner não-bloqueante e botão `Expandir Região`.
- **Preservação de Layout e Física Pacificada**:
  - Estabilização imediata da simulação de nós para zero gasto residual de CPU e bateria.
- **Suíte de Testes de Carga**:
  - Benchmarks automatizados validando serialização de 1.000 nós em < 200ms e 3.000 nós em < 500ms, além de rajadas de 150 eventos sequenciais da IA.

### 🧪 Testes
- Suíte automatizada expandida para **85 testes unitários e de integração** com 100% de sucesso.

---

## [2.1.0] - 2026-09-26

### ✨ Adicionado
- **Header Minimalista e Nivelado em Linha Única (38px)**:
  - Eliminação completa de cabeçalhos empilhados, liberando cerca de 38px de altura útil vertical de tela para código e grafo.
  - Alinhamento horizontal contínuo entre as 3 zonas da IDE:
    - **Zona 1 (Navegação):** Botão `🏛️` (Hub), nome do projeto, `📁` (Árvore), `ℹ️` (Inspetor) e campo de busca logo abaixo com atalho `📝` para busca global.
    - **Zona 2 (Editor de Código):** Trilho de abas, botão `💾 Salvar` dinâmico em verde neon Monokai (`#a6e22e`) visível apenas em modo de edição, alternador `✏️` / `👁️`, botão `📋` (Copiar) e `◀` (Recolher editor).
    - **Zona 3 (Grafo):** Seletor de profundidade `[🎯 Fase 1]`, contadores compactos, setas de fluxo `↑` (Envio) / `↓` (Recebe), atalhos `🔍` (Ctrl+P), `📝` (Ctrl+Shift+F) e botão `🌐` (Ocultar/Expandir Grafo).
- **Preservação de Atalhos ao Recolher Painéis (Reabertura Instantânea)**:
  - Injeção de botões dinâmicos de restauração (`▶` para Código e `🌐` para Grafo) na barra de navegação superior, garantindo que o usuário nunca fique preso quando os painéis forem recolhidos.
- **Cápsula Ultra-Discreta de Controle (Inferior Direito)**:
  - Design minimalista Monokai Glassmorphic de 10px em fundo escuro semitransparente com blur, substituindo o antigo bloco chamativo.
  - **Interruptor Ligar/Pausar (1 clique):** Alterna entre `🟢 Ao Vivo` e `⚪ Pausado`, permitindo suspender o polling de disco e economizar CPU/bateria enquanto programa.
  - **Botão `⏻` (Desligar Python e Fechar Janela):** Solicita confirmação rápida, encerra o processo Python no terminal via `POST /api/shutdown` e fecha a janela do navegador automaticamente (`window.close()`).
- **Endpoint `POST /api/shutdown`**:
  - Implementado tanto no `HubServer` quanto no `ArchitectureWatcher` com encerramento seguro desacoplado via thread.
  - Botão `⏻` adicionado também ao cabeçalho da Biblioteca de Projetos do Hub.

### 🧪 Testes
- Expansão da suíte automatizada para **71 testes unitários e de integração** executados com 100% de aprovação.

---

## [2.0.0] - 2026-09-26

### ✨ Adicionado
- **Sistema de Múltiplas Abas com Preview Tabs e Pinned Tabs**:
  - **Aba de Pré-visualização (*Preview Tab* em itálico)**: Clique único na árvore abre o arquivo temporariamente. Navegar entre arquivos substitui a mesma aba, eliminando acúmulo desnecessário.
  - **Aba Fixada (*Pinned Tab* normal)**: Duplo clique na árvore, duplo clique na própria aba ou clicar em `✏️ Editar` fixa o arquivo permanentemente.
  - Rolagem horizontal de abas com a roda do mouse (`wheel`), contenção de nomes longos com ellipsis e botão `✕` fixo à direita.
  - Atalhos integrados: `Ctrl+W` para fechar a aba ativa, `Ctrl+Tab` e `Ctrl+Shift+Tab` para ciclar abas.
  - Persistência seletiva no `localStorage` salvando apenas as abas fixadas entre sessões.
- **Busca Global em Arquivos (*Find in Files* — `Ctrl+Shift+F` / `Cmd+Shift+F`)**:
  - Modal flutuante de busca de conteúdo textual em todos os arquivos do repositório.
  - Filtro opcional *Case Sensitive* (`Aa`), agrupamento de resultados por arquivo, snippets com linhas numeradas e realce luminoso das ocorrências.
  - Navegação fluida via teclado (`↑`/`↓`/`Enter`) com abertura e foco direto na linha selecionada.
  - Endpoint nativo de busca com regex em memória e proteção anti-Path Traversal: `/api/search-content`.
- **Busca Rápida de Arquivos e Símbolos (*Quick Open* — `Ctrl+P` / `Cmd+P`)**:
  - Modal de busca instantânea estilo *Command Palette* do Sublime Text sobre o índice em memória ($O(N)$, sem chamadas desnecessárias de disco).
  - Navegação por teclado com setas e `Enter` para salto direto ao arquivo ou símbolo AST.
- **Editor Semântico com Realce em Modo de Edição (CodeMirror Monokai OLED)**:
  - Fundo Preto Absoluto OLED (`#000000`) preservando a sintaxe Monokai durante a digitação.
  - Quebra de linha automática (*word wrap*) e salvamento direto no disco com `Ctrl+S` e notificação toast.
  - Tecla `Tab` com indentação padronizada de 4 espaços.
- **Árvore de Arquivos com Dotfiles e Ícones Temáticos**:
  - Suporte completo a arquivos de configuração ocultos (`.env`, `.gitignore`, `.editorconfig`, `.htaccess`, `.github`, etc.).
  - Resolução dinâmica de ícones visuais para PHP, Python, JS/TS, Markdown, HTML, CSS, JSON, YAML, Shell, Composer, Artisan e Git.
- **Watcher em Tempo Real e Git Status Reativo**:
  - Sincronização contínua via Server-Sent Events (SSE) sem necessidade de recarregar a página (sem F5).
  - Badges visuais em tempo real na árvore (`+ Novo`, `~ Mod`, `- Rem`) e nos anéis luminosos do Grafo Vis.js.
- **Preservação de Abas Nativas do Navegador no Launcher**:
  - Parâmetro `--no-browser` e remoção do confinamento `--app` em `run_app.sh`, permitindo abrir abas nativas (`Ctrl+T`) para documentações, ferramentas de IA e múltiplos projetos simultâneos.

### ⚡ Performance
- Lazy loading de código-fonte sob demanda via `/api/file-content` mantendo a inicialização do workspace em menos de 15ms.

### 🧪 Testes
- Expansão da suíte automatizada para **70 testes unitários e de integração** executados em < 1 segundo com 100% de aprovação.

---

## [1.2.0] - 2026-09-25

### ✨ Adicionado
- **Seletor Minimalista de Profundidade no Grafo**: Controle integrado na barra de ferramentas permitindo alternar entre `🎯 Fase 1 (Foco Direto)` e `🌐 Fase 2 (Visão Transitiva)`.
- **Navegação Desacoplada e Ergonômica**:
  - **1 Clique**: Inspeciona dependências e métricas no Inspetor mantendo intacto o código atualmente aberto no editor.
  - **2 Cliques**: Troca deliberada de contexto, abrindo o código no editor Monokai e destacando na árvore de arquivos.
- **Lazy Loading de Código-Fonte**: Endpoint seguro `/api/file-content` (com validação anti-Path Traversal) para carregamento de arquivos sob demanda via `fetch`.
- **Abertura Pronta Imediata**: Inicialização automática do primeiro arquivo de entrada no editor Monokai ao entrar no projeto.

### ⚡ Performance
- **Renderização 100% em Memória (`render_html`)**: Eliminação de gravação e releitura em disco ao acessar a rota do workspace `/p/<id>`.
- **Inicialização Assíncrona Não-Bloqueante (`initGraphAsync`)**: O Vis.js é delegado para segundo plano via `setTimeout`, liberando a exibição imediata da árvore e do editor em menos de 50ms.
- **Corte de I/O em Repositórios Densos**: Eliminação do loop de leitura preventiva de todos os arquivos do disco em `get_live_data` e na geração do HTML.

### 🐛 Corrigido
- **Reatividade da Árvore de Arquivos**: Adição do payload atualizado em respostas de criação, renomeação e exclusão, eliminando a necessidade de F5.
- **Criação de Arquivos Genéricos**: Correção do endpoint `/api/create-file` para arquivos sem extensão `.md`.
- **Inspeção de Elementos**: Remoção de referências a nós excluídos do DOM que causavam `TypeError: Cannot set properties of null`.

### 🧪 Testes
- Expansão da suíte automatizada para **63 testes unitários** cobrindo AST, Git, Hub Server, PWA, Lazy Loading e Visualizador.
