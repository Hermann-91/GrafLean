# 📋 Registro de Alterações (Changelog)

Todas as alterações relevantes do **GrafLean** são documentadas neste arquivo, seguindo as diretrizes do padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e aderindo ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

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
