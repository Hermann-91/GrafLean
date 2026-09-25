# Especificação de Implementação: Otimização de Performance e Interatividade do Grafo

## 1. Contexto e Diagnóstico de Performance
Em projetos com alta densidade de nós e padrões de injeção ou registro centralizados (como o robô de trading `HKKond`/`Robo_Trade_IA_Gemini`, com mais de 2.200 nós e super-hubs como `StrategyRegistry` conectando mais de 400 estratégias), a expansão transitiva de 2 níveis gerava poluição visual e queda de responsividade.

## 2. Seletor de Profundidade do Subgrafo (Fase 1 vs Fase 2)
Implementação de controle minimalista na barra de ferramentas do Grafo:
- **Fase 1 - Foco Direto (Padrão)**:
  - Profundidade: 1 nível (apenas nós conectados diretamente ao nó em foco).
  - Cardinalidade típica: 3 a 15 nós.
  - Complexidade de renderização: $O(V_1 + E_1)$ quase instantânea (< 0.2ms).
  - Vantagem: visualização limpa, sem sobreposição de arestas e foco cognitivo imediato.
- **Fase 2 - Visão Transitiva**:
  - Profundidade: 2 níveis (dependências diretas e suas respectivas conexões).
  - Uso: auditoria de impacto cascata de alterações arquiteturais.

## 3. Desacoplamento da Interação no Grafo (Clique Simples vs Duplo Clique)
Seguindo os princípios de Usabilidade e Separação de Preocupações (Separation of Concerns - SoC):

| Disparador | Alvo | Ação no Grafo | Ação no Inspetor | Ação no Editor de Código | Ação na Árvore |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1 Clique no Grafo** | Nó do Grafo | Re-foca subgrafo | Atualiza métricas e dependências | **Mantém o arquivo atual** (não altera) | **Não altera** |
| **2 Cliques no Grafo** | Nó do Grafo | Re-foca subgrafo | Atualiza métricas e dependências | **Carrega o arquivo no editor** | **Destaca e rola até o arquivo** |
| **1 Clique na Árvore** | Arquivo/Pasta | Re-foca subgrafo | Atualiza métricas e dependências | **Carrega o arquivo no editor** | **Destaca o arquivo ativo** |

## 4. Arquitetura Técnica Frontend (Vis.js + Mediator)
- **Estado de Profundidade**: Variável reativa `currentGraphDepth = 1` com listener de troca no `<select id="select-graph-depth">`.
- **Filtro de Vizinhança**: Função `getNeighborhood(focusId, depth)` adaptativa para respeitar a profundidade escolhida.
- **Eventos Vis.js**:
  - `network.on('click')`: invoca `focusNodeLightweight(nodeId)`, atualizando apenas o subgrafo e o painel de propriedades, sem invocar `Mediator.select()` que forçava a troca de código.
  - `network.on('doubleClick')`: invoca `Mediator.select(nodeId)`, realizando a troca completa de arquivo e árvore.
