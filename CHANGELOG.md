# 📋 Registro de Alterações (Changelog)

Todas as alterações relevantes do **GrafLean** são documentadas neste arquivo, seguindo as diretrizes do padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e aderindo ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

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
