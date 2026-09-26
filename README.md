# 🔍 GrafLean — Architecture-First IDE & Top-Down Lens

> **Lente de Raio-X Arquitetural e Plataforma de Code Review Local de Alta Performance.**
> Mapeamento determinístico de dependências em grafos, métricas de *Clean Architecture*, árvore estrutural e editor com tema Monokai Sublime, equipado com sincronização contínua em tempo real (*Watch Mode*) para programação em par com IA.

---

## ⚡ Por que o GrafLean?

Durante o desenvolvimento de software e o uso intenso de modelos de IA, desenvolvedores frequentemente sofrem com a **sobrecarga cognitiva**:
* *"Quem chama este método?"*
* *"Esta alteração introduziu uma dependência circular?"*
* *"Este módulo é profundo (Deep Module) ou esconde complexidade acidental?"*
* *"Como auditar o impacto sistêmico do código gerado pela IA em menos de 1 segundo?"*

O **GrafLean** soluciona esse gargalo operando como uma **IDE de raio-X arquitetural**. Ele não depende de plugins pesados, bibliotecas externas (`pip install`) ou conexões com a internet: analisa os códigos via AST nativo em **< 15ms**, gerando uma estação de trabalho visual integrada e interativa no seu navegador.

---

## 🌟 Principais Recursos

### 1. 🖥️ Workspace Integrado de IDE (Estilo Sublime / JetBrains)
* **Header Minimalista e Nivelado (38px):** Linha contínua horizontal alinhando Navegação, Trilho de Abas do Editor e Toolbar do Grafo sem degraus verticais, liberando espaço útil para visualização do código.
  * **Preservação de Atalhos:** Ao recolher o código ou o grafo, botões dinâmicos de reabertura (`▶` e `🌐`) surgem na barra de navegação para restauração imediata em 1 clique.
  * **Cápsula Ultra-Discreta de Controle (Inferior Direito):** Alternador de 1 clique entre `🟢 Ao Vivo` e `⚪ Pausado` para economizar CPU/bateria, acompanhado do botão `⏻` para desligar o processo Python e fechar a janela automaticamente.
* **Coluna de Navegação Lateral:**
  * **[📁 Árvore]:** Visão hierárquica com dotfiles liberados (`.env`, `.gitignore`, etc.), ícones temáticos e contadores de símbolos com busca dinâmica.
  * **[ℹ️ Inspetor]:** Diagnóstico arquitetural instantâneo com Métricas de Robert C. Martin ($C_a$, $C_e$, $I$), docstrings e listas diretas de chamadores (*Inbound*) e dependências (*Outbound*).
  * **Botão `◀` Recolher:** Oculte o painel lateral com um clique para foco total no código.
* **Sistema de Múltiplas Abas Inteligentes (Sublime Tab Bar):**
  * **Pré-visualização (*Preview Tabs* em itálico):** Clique simples na árvore abre o arquivo temporariamente sem poluir a barra de abas.
  * **Fixação (*Pinned Tabs* retas):** Duplo clique no arquivo na árvore ou na própria aba fixa o arquivo permanentemente.
  * **Navegação Rápida:** Rolagem com a roda do mouse, atalhos `Ctrl+Tab`, `Ctrl+Shift+Tab` e `Ctrl+W` para fechar.
* **Coluna Central — Editor Monokai Sublime (True Black):**
  * Fundo em Preto Absoluto (`#000000`) para contraste máximo em telas OLED.
  * CodeMirror Monokai integrado com preservação de sintaxe em tempo de edição, quebra de linha (*word wrap*) e salvamento direto com `Ctrl+S`.
* **Busca Universal e Navegação Ágil:**
  * **`Ctrl+P` / `Cmd+P` (Quick Open):** Salto instantâneo para arquivos e símbolos AST com busca fuzzy em memória.
  * **`Ctrl+Shift+F` / `Cmd+Shift+F` (Find in Files):** Busca global de texto em todo o repositório com snippets e destaque visual.
* **Divisores Arrastáveis com o Mouse (`col-resize`):**
  * Divisor interno entre Árvore e Editor de Código.
  * Divisor externo entre o Workspace de Código e o Grafo.
* **Painel Direito — Grafo Top-Down Interativo:**
  * **Triplo Seletor de Perspectivas:** Alternância instantânea na barra superior entre:
    * `[ CÓDIGO ]`: Mapa estrutural arquitetural padrão por símbolos e conexões.
    * `[ IA / GIT ]`: Foco dedicado nas mutações ativas com cores semânticas (verde=novo, laranja=modificado, vermelho=excluído), elementos neutros atenuados e animação pulsante da IA.
    * `[ IMPACTO ]`: Foco cirúrgico no nó alterado e na sua cascata de chamadores e dependências de 1º e 2º grau.
  * **Seletor de Profundidade (Fase 1 vs Fase 2):** Alternância instantânea entre 🎯 *Fase 1 (Foco Direto)* e 🌐 *Fase 2 (Visão Transitiva)*, eliminando a poluição visual em projetos densos ou com super-hubs.
  * **Proteção de Escala (Limite Inteligente):** Limite de renderização (`GRAPH_NODE_LIMIT = 250`) com banner de proteção não-obstrutivo e botão `Expandir Região` sob demanda.
  * **Change Summary Banner:** Estatísticas em tempo real no topo da visão de mudanças com contadores e botão `Próxima Mudança ▶`.
  * **Navegação Desacoplada e Ergonômica:** **1 clique** no nó foca e inspeciona dependências e métricas no Inspetor mantendo o código aberto na tela; **2 cliques** confirmam a troca ativa de arquivo no editor e na árvore.
  * **Física Contínua e Suave:** Visualização orgânica com reposicionamento dinâmico sem congelamento da interface.

### 2. ⚡ Performance Instantânea & Live Reload em Tempo Real
* **Carregamento Instantâneo (< 50ms) com Lazy Loading:** O servidor entrega a IDE de imediato sem leitura em massa de disco. O código de cada arquivo é buscado sob demanda apenas ao ser clicado (`/api/file-content`), otimizando projetos gigantes (como robôs de trading com mais de 2.200 nós).
* **Abertura Pronta com Árvore e Código:** Ao entrar no workspace, a árvore de arquivos já está pronta e o primeiro arquivo já abre no editor Monokai sem espera.
* **Patches Incrementais Semânticos (SSE):** Quando você ou a IA cria, altera ou exclui arquivos, o backend emite eventos estruturados (`node_created`, `node_changed`, `node_deleted`, `ai_state`, etc.). O frontend aplica os patches diretamente no Vis.js sem destruir o grafo e sem perder as posições físicas dos nós.
* **Endpoints REST para Agentes de IA:**
  * `POST /api/ai-state`: Permite que assistentes de IA (ex: Claude, Gemini, CLI) sinalizem em tempo real qual arquivo estão criando, editando ou analisando.
  * `POST /api/changes`: Consulta o resumo consolidado das alterações ativas (Git + IA).
* **Preservação de Estado:** Ao recarregar, o sistema memoriza exatamente qual arquivo, linha e aba estavam ativos via `sessionStorage`.

### 3. 🎯 Rastreamento Git Instantâneo (< 5ms)
* **Status em Tempo Real:** Detecta automaticamente arquivos novos não rastreados (`??`/`A`) e modificados (`M`) via `git status --porcelain`.
* **Destaque Visual Duplo:**
  * **Na Árvore de Arquivos:** Badges visuais estilizados `[+ Novo]` em verde neon e `[~ Mod]` em âmbar.
  * **No Grafo Vis.js:** Anéis de borda espessos com realce luminoso nas mesmas tonalidades semânticas.
  * **No Inspetor:** Exibição do status de versionamento do componente ativo.

### 4. 🤖 Orquestração de Agentes & Criação de Especificações
* **Criação Rápida de Recursos:** Modal interativo integrado na UI e comando CLI dedicado (`graf-lens-new`).
* **Templates Prontos para Agentes:**
  * **`TASK.md`:** Objetivos, contexto de chamadores/dependências, restrições Clean Code, critérios de aceite e passos de execução.
  * **`SPEC.md`:** Especificação arquitetural com limites, contratos de interface e invariantes.
  * **`CONTEXT.md`:** Contexto operacional completo da stack, diretrizes e comandos essenciais.
* **Copiar Prompt para Agente em 1 Clique:** No painel Inspetor, gere instantaneamente um prompt contextualizado com as métricas $C_a$, $C_e$, $I$, lista de chamadores e dependências para colar no terminal do seu agente autônomo.
* **Segurança Estrita:** Proteção nativa contra ataques de *Path Traversal* (`..`).

### 5. 🌐 Suporte Poliglota Nativo
* 🐘 **PHP 8+ / Laravel:** Namespaces, Classes, Interfaces, Métodos, Chamadas `$this->service->metodo()` e Injeção de Dependências no Construtor.
* 🐍 **Python:** Módulos, Classes, Herança, Funções, Assinaturas e Imports via AST nativo.
* ⚛️ **JavaScript & TypeScript:** Funções, Classes, Componentes React, Hooks customizados (`use...`) e Services do Angular.
* 📄 **HTML & Blade (Laravel):** Diretivas `@extends`, `@include` e componentes `<x-... />`.

---

## ⌨️ Atalhos de Produtividade (Estilo Sublime Text)

| Atalho | Ação |
| :--- | :--- |
| <kbd>Ctrl</kbd> + <kbd>P</kbd> | **Quick Open:** Busca rápida e salto instantâneo de arquivo ou símbolo |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>F</kbd> | **Find in Files:** Busca global de conteúdo em todos os arquivos |
| <kbd>Ctrl</kbd> + <kbd>S</kbd> | **Salvar Arquivo:** Salva instantaneamente o arquivo em edição no disco |
| <kbd>Ctrl</kbd> + <kbd>W</kbd> | **Fechar Aba:** Fecha a aba ativa atual |
| <kbd>Ctrl</kbd> + <kbd>Tab</kbd> | **Próxima Aba:** Alterna para a próxima aba aberta |
| <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Tab</kbd> | **Aba Anterior:** Alterna para a aba anterior |

---

## 📐 Fundamentos Teóricos e Princípios de Engenharia

O GrafLean foi projetado aplicando os princípios das principais literaturas de Engenharia de Software:

1. **Clean Architecture (*Robert C. Martin*):**
   * **Acoplamento Aferente ($C_a$):** Número de classes externas que dependem deste módulo.
   * **Acoplamento Eferente ($C_e$):** Número de classes que este módulo consome.
   * **Instabilidade ($I = \frac{C_e}{C_a + C_e}$):** Varia de 0 (módulo totalmente estável e confiável) a 1 (módulo totalmente instável e dependente).
   * **Auditoria de Ciclos:** Identifica violações da regra de dependência acíclica (A ➔ B ➔ A).
2. **A Philosophy of Software Design (*John Ousterhout*):**
   * **Deep Modules:** Identifica módulos cuja interface pública é compacta mas que encapsulam grande funcionalidade interna.
3. **Padrões de Projeto Utilizados:**
   * **Composite Pattern:** Modelação homogênea da árvore de diretórios e arquivos de código.
   * **Mediator Pattern:** Sincronização desacoplada entre Grafo Vis.js, Árvore, Inspetor e Editor.
   * **Registry / Factory Pattern:** Seleção dinâmica do parser de acordo com a extensão do arquivo.
   * **Observer via SSE:** Disparo reativo de eventos de atualização do servidor para o cliente.
   * **Single Responsibility & Template Cache:** Pacote modular `core/visualizer/` separando extração de dados (`GraphDataSerializer`), cache de assets em memória (`TemplateEngine`) e orquestração limpa.

---

## 🚀 Como Usar no Terminal

O sistema instala executáveis globais em `~/.local/bin/`, disponíveis em qualquer diretório:

```bash
# 1. Modo Vigilante em Tempo Real (Recomendado para Pair Programming com IA)
graf-lens-watch [pasta_do_projeto]

# 2. Gerar Mapa Interativo e Abrir no Navegador
graf-lens-map [pasta_do_projeto]

# 3. Auditar Acoplamento e Ciclos de Dependência no Terminal
graf-lens-audit [pasta_do_projeto]

# 4. Inspecionar Métricas de uma Classe ou Método Específico
graf-lens-info NomeDaClasse [pasta_do_projeto]

# 5. Escaneamento Rápido em Lote (Gera .arch_graph.json)
graf-lens-scan [pasta_do_projeto]

# 6. Criar Pastas e Especificações Markdown para Agentes
graf-lens-new folder docs/specs
graf-lens-new md docs/specs/TASK_CHECKOUT.md --template task
```

---

## 🧪 Suíte de Testes Automatizados

Garantia de qualidade contínua com a biblioteca padrão `unittest` do Python (**85 testes automatizados** executando em ~1.2s com 100% de sucesso, incluindo testes de stress com 1.000 e 3.000 nós):

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
```text
Ran 85 tests in 1.275s
OK
```

---

## 🛡️ Integridade e Privacidade
* **Zero Dependências Externas:** 100% biblioteca padrão do Python (`json`, `ast`, `http.server`, `threading`, `socketserver`).
* **Privacidade Absoluta:** O código nunca sai da sua máquina local.
* **Zero Footprint no Sistema:** Nenhum arquivo ou configuração global de terceiros é alterada indevidamente.
