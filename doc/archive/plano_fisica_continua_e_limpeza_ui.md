# 📋 Plano: Física Contínua no Grafo & Limpeza da Interface

Este documento formaliza as decisões de arquitetura e o planejamento de implementação para manter a física do grafo permanentemente ativa e despoluir a interface de usuário do **GrafLean**.

---

## 🎯 Objetivos Principais

1. **Física Contínua no Vis.js (*Always-On Physics*):**
   - Manter a simulação física do Vis.js ativa continuamente (`physics: { enabled: true }`).
   - Com o subgrafo agora restrito a **até 2 níveis** (15 a 40 nós), o cálculo contínuo de forças tem impacto computacional negligenciável (< 0.5% de CPU), proporcionando sensação tátil e amortecimento elástico responsivo ao interagir com o grafo.
   - Eliminar a desativação prematura da física após o evento `stabilizationIterationsDone`.
2. **Despoluição da Barra de Ferramentas do Grafo:**
   - Deletar o botão `⚡ Física: Off/On` (`btn-physics`).
   - Deletar o botão `🔄 Reorganizar` (`btn-reorganize`).
   - Deletar o botão `🔍 Enquadrar` (`btn-fit`).
   - A barra do grafo passa a conter apenas o botão de recolher/expandir o grafo, o contador de nós e a legenda visual de cores das setas (**Envio** em azul e **Recebe** em laranja).
3. **Limpeza do Painel Lateral Inspetor:**
   - Remover o card superior que continha o título, o caminho do arquivo, a docstring e o botão `📋 Copiar Prompt para Agente`.
   - O painel Inspetor passará a focar diretamente no diagnóstico arquitetural:
     - Métricas de Código Limpo ($C_a$, $C_e$, Instabilidade $I$).
     - Listagem de chamadores diretos (**📥 Chamado por**).
     - Listagem de dependências diretas (**📤 Depende de**).
4. **Alinhamento dos Testes Automatizados:**
   - Atualizar a suíte em `tests/test_visualizer.py` para remover asserções de elementos deletados, assegurando 100% de cobertura e aprovação verde em todos os testes.

---

## 🛠️ Detalhamento dos Componentes a Modificar

### 1. `core/visualizer.py`
- **Template HTML do Inspetor:** Remover o container `<div class="card">` do prompt do agente.
- **Template HTML do Grafo:** Remover os 3 botões do elemento `#graph-toolbar`.
- **Script Vis.js:**
  - Manter `physics: { enabled: true }` com amortecimento suave (`damping: 0.85`).
  - Remover o callback que desligava a física em `stabilizationIterationsDone`.

### 2. `tests/test_visualizer.py`
- Remover as asserções de botões da barra excluídos (`btn-reorganize`, `btn-fit`, `btn-physics`).

---

## 🧪 Critérios de Aceite e Verificação

- Execução bem-sucedida de `python3 -m unittest discover -s tests -p "test_*.py" -v`.
- Taxa de sucesso: **62/62 testes aprovados**.
- Interface limpa e responsiva, com nós do grafo móveis e elásticos em tempo real.
