# 🏛️ Plano de Engenharia: Grafo Top-Down Hierárquico sob Demanda & Ultra-Performance

> **Meta:** Transformar o grafo do GrafLean de uma "nuvem estática de 1.500+ nós" em uma estação de trabalho visual hierárquica fluida e instantânea (< 30ms), inspirada na ergonomia do Sublime Text e no clássico princípio de visualização de software: *"Overview first, zoom and filter, then details-on-demand" (Ben Shneiderman)*.

---

## 📸 1. Diagnóstico do Problema Visual

Em projetos de médio e grande porte (como visto no `proj_promptok`), a visualização estática tradicional atinge um limite severo:
* **Volume Identificado:** Mais de **1.500 nós** e **1.300 conexões** renderizados simultaneamente.
* **Gargalo no Navegador:** O motor Vis.js tenta calcular a física gravitacional contínua (`forceAtlas2Based`) em tempo real para 1.500 elementos a 60 FPS na thread principal do JavaScript, travando o scroll e saturando a CPU do usuário.
* **Sobrecarga Cognitiva:** Uma "bola de nós densa" esconde a estrutura sistêmica real, pois métodos internos privados disputam a mesma atenção visual que classes e arquivos centrais.

---

## ⚠️ 2. Avaliação Crítica de Arquitetura: Por que NÃO usar Docker/Redis?

À luz das literaturas de **Clean Architecture** (*Robert C. Martin*) e **A Philosophy of Software Design** (*John Ousterhout*), avaliamos criticamente a ideia de usar Docker, Redis ou filas de jobs:
1. **O gargalo NÃO é o backend Python:** O parser nativo do GrafLean escaneia o repositório inteiro e gera o JSON em **menos de 120ms** usando Python puro padrão.
2. **O gargalo é 100% no Canvas do front-end:** O atraso ocorre na GPU e na thread de renderização do navegador ao calcular forças para milhares de nós simultâneos.
3. **Complexidade Acidental:** Adicionar Docker e Redis exigiria daemons pesados, consumiria centenas de megabytes de RAM e destruiria a regra de ouro do GrafLean (*Zero dependências externas, 100% biblioteca padrão, portabilidade instantânea*).

**Conclusão:** A solução definitiva é a **Hierarquização sob Demanda no Front-end (Client-Side)**.

---

## 💡 3. A Solução: Navegação Top-Down com Expansão por Clique

Adotaremos a estratégia clássica de visualização de sistemas:

```text
📁 Nível 1: Arquivos e Módulos
    └── 🏛️ Nível 2: Classes e Interfaces
            └── ⚡ Nível 3: Métodos e Funções
```

### Regras de Interação:
1. **Visão Inicial Padrão (Arquitetural — < 80 nós):**
   * Ao abrir o workspace, o grafo carrega **apenas Arquivos e Classes/Interfaces principais**.
   * O volume cai de **1.564 nós para ~60 nós**. O carregamento torna-se **instantâneo (< 15ms)**.
2. **Expansão sob Demanda (1 Clique):**
   * **Ao clicar em um Arquivo:** se possuir classes/interfaces internas não exibidas, elas se expandem ao redor dele conectadas às dependências externas.
   * **Ao clicar em uma Classe:** seus métodos e funções se abrem imediatamente com suas arestas locais de chamada (`CALLS`).
   * **Ao clicar novamente:** os métodos são recolhidos, mantendo o canvas sempre limpo e legível.
3. **Congelamento Imediato de Física (`freezeOnStabilize`):**
   * A física roda apenas 35 iterações em background para posicionar os nós e é **imediatamente desativada** (`physics: false`).
   * O pan/zoom no canvas passa a rodar a **60 FPS cravados** com **0% de uso de CPU**.
   * Botão no topo do grafo: `[⚡ Física: Off/On]` para permitir reorganização livre quando desejado.
4. **Suporte Completo a JSON, CSS e HTTP:**
   * Garantir que extensões `.json` e `.css` sejam indexadas como nós `file` e renderizadas com syntax highlighting no editor integrado.
   * Mapeamento de rotas e chamadas de API como conexões estruturais no grafo.

---

## 🛠️ 4. Roteiro de Implementação

### Passo 1: Metadados Hierárquicos no Visualizador (`core/visualizer.py`)
* Adicionar propriedades `parentId`, `level` (`1=file`, `2=class`, `3=method`) e `isExpanded` em cada nó exportado.
* Cache local `allNodesMap` e `allEdgesMap` no front-end para inserção e remoção instantânea no `vis.DataSet`.

### Passo 2: Interatividade e Expansão Dinâmica no Vis.js
* Evento `network.on('click')` interceptando cliques em nós de classe e arquivo para alternar a visibilidade de seus filhos.
* Seletor de visualização rápida no topo do grafo:
  * `[🏛️ Arquitetura (Padrão)]`
  * `[📁 Macro (Somente Arquivos)]`
  * `[🔬 Expandir Tudo]`
  * `[⚡ Física: Off/On]`

### Passo 3: Indexação de JSON e CSS (`core/tree.py` e `core/graph.py`)
* Assegurar que arquivos `.json` e `.css` façam parte do inventário de arquivos do projeto.

---

## 🧪 5. Verificação e Critérios de Aceite
1. **Latência de Renderização:** O grafo do `proj_promptok` deve carregar em **menos de 50ms**.
2. **Uso de CPU:** Após o carregamento, o uso de CPU da aba do navegador deve ficar em **0%**.
3. **Interatividade Top-Down:** Clicar em uma classe abre seus métodos; clicar novamente recolhe.
4. **Testes Automatizados:** Todos os **56 testes unitários** devem continuar passando com 100% de sucesso.
