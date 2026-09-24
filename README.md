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
* **Coluna de Navegação Lateral:**
  * **[📁 Árvore]:** Visão hierárquica construída com o *Composite Pattern*, exibindo diretórios, arquivos, classes, métodos e contadores com busca dinâmica.
  * **[ℹ️ Inspetor]:** Diagnóstico arquitetural instantâneo com Métricas de Robert C. Martin ($C_a$, $C_e$, $I$), docstrings e listas diretas de chamadores (*Inbound*) e dependências (*Outbound*).
  * **Botão `◀` Recolher:** Oculte o painel lateral com um clique para foco total no código.
* **Coluna Central — Editor Monokai Sublime (True Black):**
  * Fundo em Preto Absoluto (`#000000`) para contraste máximo em telas OLED.
  * Gutter com numeração de linhas, realce da linha ativa e coloração de sintaxe 1:1 com o Sublime Text.
* **Divisores Arrastáveis com o Mouse (`col-resize`):**
  * Divisor interno entre Árvore e Editor de Código.
  * Divisor externo entre o Workspace de Código e o Grafo.
* **Painel Direito — Grafo Top-Down Interativo:**
  * Renderização interativa via Vis.js com física e sincronização bidirecional (*Mediator Pattern*): ao clicar em um nó no grafo, a árvore se abre e o editor rola até a linha exata.

### 2. ⚡ Live Reload em Tempo Real (`graf-lens-watch`)
* **Sincronização Contínua com IA:** Monitora alterações de arquivos em background sem consumir CPU.
* **Server-Sent Events (SSE):** Quando você ou a IA cria ou altera um arquivo (`.php`, `.py`, `.js`, etc.), o grafo e o editor re-escaneiam e atualizam a tela em tempo real.
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

Garantia de qualidade contínua com a biblioteca padrão `unittest` do Python (26 testes automatizados executando em menos de 200 milissegundos):

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
```text
Ran 26 tests in 0.183s
OK
```

---

## 🛡️ Integridade e Privacidade
* **Zero Dependências Externas:** 100% biblioteca padrão do Python (`json`, `ast`, `http.server`, `threading`, `socketserver`).
* **Privacidade Absoluta:** O código nunca sai da sua máquina local.
* **Editor Sublime Text Intocado:** Nenhuma alteração é realizada em seus binários ou arquivos de configuração do Sublime.
