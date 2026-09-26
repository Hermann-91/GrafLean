# Plano de Ação: Sublime Architecture Lens 🔍🏛️

> **Nota de Contexto (Concluído/Histórico):** A integração como plugin do Sublime Text serviu como protótipo inicial (Fase 1). O projeto evoluiu para o **GrafLean**, uma IDE autônoma de alta performance e Hub PWA independente de editores externos (consulte `doc/plano_graflean_hub_pwa.md`).

## 1. Visão Geral e Objetivo
O **Sublime Architecture Lens** é uma ferramenta de produtividade e engenharia de software para o **Sublime Text**, projetada para desenvolvedores com raciocínio sistêmico top-down (pensamento em teia). Inspirada nas melhores capacidades de análise estática do *Graphify* e nos livros clássicos de arquitetura (*Arquitetura Limpa* e *A Philosophy of Software Design*), a ferramenta funciona como uma lente de raio-X arquitetural:

Ao repousar o cursor (`on_hover`) sobre uma **função, método, classe ou cabeçalho de arquivo**, o editor exibe instantaneamente um pop-up elegante contendo:
1. **Identidade e Papel:** Camada arquitetural e propósito (extraído da docstring ou resumo).
2. **Conexões Top-Down (Inbound / Outbound):** Quem consome este elemento e do que ele depende, com links clicáveis que navegam direto para o arquivo e linha exata.
3. **Métricas de Saúde Arquitetural:** Acoplamento Aferente ($C_a$), Acoplamento Eferente ($C_e$), profundidade de módulo e alerta de dependência circular.
4. **Mapa Global:** Atalho para abrir no navegador o grafo interativo completo do projeto.

---

## 2. Localização e Estrutura do Projeto
**Caminho Raiz:** `./` (Repositório GrafLean)

### Estrutura de Diretórios:
```text
GrafLean/
├── doc/
│   └── plano_architecture_lens.md    # Este plano técnico
├── AGENT.md                          # Contrato de atuação e diretrizes de excelência do Agente
├── README.md                         # Guia de instalação, atalhos e funcionamento
├── Default.sublime-keymap            # Atalhos de teclado no Sublime Text
├── ArchitectureLens.sublime-settings # Configurações (ex: auto_index, debounce, tema)
├── architecture_lens.py              # Camada de Apresentação (ViewEventListener e Pop-up HTML)
├── core/                             # Núcleo Agnóstico de AST e Grafo (Python Puro)
│   ├── __init__.py
│   ├── models.py                     # Estruturas de dados (Node, Edge, SymbolType, Metrics)
│   ├── graph.py                      # Grafo em memória e serialização em .arch_graph.json
│   ├── analyzer.py                   # Métricas (Ca, Ce, ciclos, profundidade de Ousterhout)
│   ├── visualizer.py                 # Exportador do mapa interativo HTML (Canvas/Mermaid)
│   └── parsers/                      # Extratores de AST por linguagem
│       ├── __init__.py
│       ├── base.py                   # Contrato abstrato BaseParser
│       ├── php_parser.py             # Parser estático para PHP 8+ (Classes, Namespaces, DI, Calls)
│       └── python_parser.py          # Parser nativo usando biblioteca ast do Python
└── tests/                            # Bateria rigorosa de testes unitários e de integração
    ├── __init__.py
    ├── fixtures/                     # Amostras de código real (ex: Controller, Service, Model)
    ├── test_models.py
    ├── test_php_parser.py
    ├── test_graph.py
    └── test_analyzer.py
```

---

## 3. Fases de Implementação e Detalhamento Técnico

### Fase 1: O Motor de Análise Estática (`core/`)
* **`models.py`:** Define os tipos de nós (`FILE`, `CLASS`, `METHOD`, `FUNCTION`, `INTERFACE`), arestas (`CALLS`, `INHERITS`, `IMPLEMENTS`, `IMPORTS`) e estruturas de métricas.
* **`parsers/php_parser.py`:** Extrai tokens estruturais de arquivos PHP (identifica `class`, `interface`, `namespace`, injeção no `__construct`, chamadas `$this->service->method()` e cláusulas `use`).
* **`parsers/python_parser.py`:** Utiliza o módulo nativo `ast` do Python para extrair símbolos de scripts Python.
* **`graph.py` & `analyzer.py`:** Indexa o diretório do projeto, calcula acoplamento aferente ($C_a = \text{in-degree}$) e eferente ($C_e = \text{out-degree}$) e identifica ciclos com detecção de componentes fortemente conectados.

### Fase 2: O Plugin do Sublime Text (`architecture_lens.py`)
* Herda de `sublime_plugin.ViewEventListener`.
* Implementa `on_hover(point, hover_zone)` filtrando para a zona de texto (`sublime.HOVER_TEXT`).
* Obtém a palavra/símbolo e o caminho do arquivo aberto.
* Renderiza o pop-up com `view.show_popup()`:
  * CSS embutido elegante com paleta harmoniosa para Sublime Dark Themes.
  * Links no formato `<a href="sublime:open_symbol?file=...&line=...">NomeDoSimbolo</a>`.
  * Ao clicar no link, o Sublime abre o arquivo correspondente e foca na linha indicada.

### Fase 3: Mapa Global Interativo e Integração com o Laboratório
* Comando `Architecture: Show Project Architecture` na paleta de comandos (`Ctrl+Shift+P`).
* Gera um arquivo `arch_map.html` autocontido com visualização de nós e comunidades em tela cheia.
* Teste prático e validação em projetos de exemplo e suítes de teste automatizadas.

---

## 4. Plano de Verificação e Qualidade

### Testes Automatizados (`pytest`)
Executar na pasta do projeto:
```bash
pytest -v tests/
```
* **`test_php_parser.py`:** Garante que classes com namespaces, injeções de dependência e chamadas de métodos são extraídas com 100% de exatidão.
* **`test_analyzer.py`:** Valida que ciclos de dependência são detectados e as métricas $C_a$ e $C_e$ batem com os princípios do *Clean Architecture*.
* **`test_graph.py`:** Garante que o arquivo `.arch_graph.json` é gerado e lido em menos de 10ms.
