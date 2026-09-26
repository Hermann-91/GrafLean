# Plano de evolução do GrafLean — IA + Change Graph + alta performance

## 1. Objetivo

Evoluir o GrafLean para uma experiência de desenvolvimento orientada à compreensão visual do código, mantendo:

- alta performance em projetos grandes;
- gráfico responsivo;
- atualização incremental em tempo real;
- visualização das mudanças produzidas pela IA;
- integração natural com Git;
- navegação por fases/profundidade;
- separação clara entre arquitetura do código e alterações em andamento;
- animações visuais sem obrigar o recálculo do grafo inteiro.

A ideia central é separar **estado estrutural**, **estado de mudança** e **estado da IA**.

---

## 2. Conceito principal

Criar três perspectivas sobre o mesmo índice semântico:

### Code Graph

Responde:

> Como o software está estruturado?

Mostra:

- arquivos;
- classes;
- funções/métodos;
- chamadas;
- dependências;
- inbound/outbound;
- fases de expansão;
- tooltips e informações resumidas.

### Change Graph

Responde:

> O que está mudando?

Mostra:

- arquivos novos;
- arquivos modificados;
- arquivos deletados;
- relações adicionadas/removidas;
- alterações associadas à tarefa atual da IA.

### Impact Graph

Responde:

> O que uma alteração pode afetar?

Mostra:

- nó alterado;
- dependências diretas;
- chamadores;
- dependências indiretas;
- área potencialmente afetada.

---

# 3. Regra arquitetural mais importante

## Não reconstruir o grafo inteiro a cada alteração.

Evitar:

```text
arquivo mudou
    ↓
reindexar tudo
    ↓
gerar JSON inteiro
    ↓
enviar JSON inteiro
    ↓
destruir gráfico
    ↓
renderizar novamente
```

Preferir:

```text
arquivo mudou
    ↓
analisar somente o necessário
    ↓
gerar evento/patch
    ↓
SSE
    ↓
atualizar nós/arestas afetados
    ↓
animar somente a alteração
```

O grafo completo continua existindo como estado lógico no backend, mas o frontend recebe apenas o necessário para atualizar sua representação atual.

---

# 4. Arquitetura proposta

```text
                         IA
                          │
                          ▼
                  Change Manager
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
          CREATE        MODIFY       DELETE
             │            │            │
             └────────────┼────────────┘
                          ▼
                    AST / Indexador
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        Grafo semântico            Git
              │                       │
              └───────────┬───────────┘
                          ▼
                    Event Stream
                         SSE
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
        Code Graph               Change Graph
             │                         │
       Fase 1 / 2 / N             IA + Git
             │                         │
             └────────────┬────────────┘
                          ▼
                    Frontend JS
                          │
                    patch incremental
                          │
                          ▼
                       Vis.js
```

---

# 5. Modelo de estados

Não misturar o estado da IA com o estado do Git.

## Estado da IA

Exemplos:

```text
idle
creating
editing
analyzing
finished
error
```

## Estado do Git

Exemplos:

```text
untracked
modified
deleted
staged
committed
```

## Estado visual

Uma combinação dos dois.

Exemplo:

```text
🟢 novo + pulsando
🟢 novo + estático
🟠 modificado + pulsando
🟠 modificado + estático
🔴 deletado
```

---

# 6. Eventos SSE

Criar eventos semânticos em vez de eventos que ordenem reload completo.

## Criação

```json
{
  "event": "node_created",
  "path": "auth/token_service.py",
  "status": "new"
}
```

## Modificação

```json
{
  "event": "node_changed",
  "path": "auth/service.py",
  "status": "modified"
}
```

## Exclusão

```json
{
  "event": "node_deleted",
  "path": "auth/legacy.py",
  "status": "deleted"
}
```

## Nova relação

```json
{
  "event": "edge_added",
  "source": "auth.py",
  "target": "token_service.py"
}
```

## Remoção de relação

```json
{
  "event": "edge_removed",
  "source": "auth.py",
  "target": "legacy.py"
}
```

## Estado da IA

```json
{
  "event": "ai_state",
  "path": "auth/service.py",
  "state": "editing"
}
```

---

# 7. Visualização do Change Graph

Criar uma aba dedicada:

```text
[ CÓDIGO ] [ IA / GIT ] [ IMPACTO ]
```

### Cores

- Verde: arquivo novo
- Laranja: arquivo modificado
- Vermelho: arquivo deletado
- Neutro: arquivo existente sem alteração

Não depender exclusivamente da cor: usar tooltip/ícone/legenda para acessibilidade.

---

# 8. Animação da IA

A animação deve ser uma camada sobre o grafo.

Não fazer:

```text
evento IA
→ recalcular layout completo
→ reconstruir grafo
→ animar
```

Fazer:

```text
evento IA
→ atualizar estado
→ inserir/modificar nó
→ atualizar relações afetadas
→ executar animação local
```

## Exemplo

```text
IA cria arquivo

          🟢
         ╱          ●    ●

nó aparece
↓
fade/scale
↓
ligações aparecem
↓
nó entra no layout
↓
estado fica estável
```

Para modificações:

```text
arquivo existente
      ↓
estado normal
      ↓
laranja pulsante
      ↓
processamento concluído
      ↓
laranja estático
```

---

# 9. Commit como transição visual

Quando a etapa da IA for concluída:

```text
AI Working
     ↓
Commit
     ↓
Git atualizado
     ↓
Change Graph limpa
     ↓
Code Graph recebe novo estado
```

O ideal é uma transição suave:

```text
🟢 / 🟠 / 🔴
      ↓
fade
      ↓
estado estrutural normal
```

O commit não precisa apagar imediatamente a percepção da mudança.

Uma pequena transição visual pode reforçar a sensação de histórico.

---

# 10. Performance: limite de nós

Criar um limite configurável.

Exemplo inicial:

```text
GRAPH_NODE_LIMIT = 250
```

Esse número deve ser tratado como proteção, não como mecanismo principal.

A regra principal deve ser:

> Renderizar somente a região relevante.

Exemplo:

```text
Projeto:
3.000 nós
17.000 relações

Frontend:
30 nós
42 relações
```

---

# 11. Expansão progressiva

Manter a ideia de fases existente no GrafLean.

Evoluir de:

```text
Fase 1
Fase 2
```

para um modelo conceitualmente extensível:

```text
Fase 1
Fase 2
Fase 3
...
```

Mas cada fase deve ser carregada sob demanda.

Exemplo:

```text
              A
             /             B   C
           /           D   E
```

Ao expandir B:

```text
              A
             /             B   C
          / |          D  E  F
```

Não reconstruir o gráfico inteiro.

---

# 12. Preservação do layout

Um problema importante de UX é o gráfico "pular" quando um nó é adicionado.

Sempre que possível:

1. preservar posições existentes;
2. calcular posição apenas para novos nós;
3. minimizar movimentação dos nós antigos;
4. animar apenas o necessário;
5. evitar executar layout global a cada evento.

Isso é especialmente importante durante a criação em tempo real pela IA.

---

# 13. Agrupamento para projetos grandes

Quando houver muitos nós, permitir agregação semântica.

Exemplo:

```text
src/
 ├── api/
 ├── services/
 ├── models/
 └── database/
```

Pode virar:

```text
[API] ─────→ [SERVICES] ─────→ [DATABASE]
                │
                ▼
             [MODELS]
```

Ao clicar:

```text
[SERVICES]
    ↓
service_a.py
service_b.py
service_c.py
...
```

Isso mantém o mapa compreensível sem perder informação.

---

# 14. Mini-map de alterações

Na aba IA/Git, mostrar uma visão pequena do conjunto das alterações.

Exemplo:

```text
┌────────────────────────┐
│      CHANGE MAP        │
│                        │
│       ●──●             │
│      /    \            │
│     ●      ●──●        │
│            │           │
│            ●           │
│                        │
│  7 modificados         │
│  3 novos               │
│  1 deletado             │
└────────────────────────┘
```

O gráfico principal mostra somente o cluster atualmente selecionado.

---

# 15. Impact Graph

Ao selecionar um arquivo alterado:

```text
auth/service.py
```

mostrar:

```text
             Controller
                  │
                  ▼
          🟠 AuthService
             /                   ▼         ▼
      Repository    Logger
           │
           ▼
        Database
```

O foco deve ser a alteração, não o projeto inteiro.

---

# 16. Tooltip semântico

Manter o comportamento atual do GrafLean.

Ao passar o mouse:

```text
┌──────────────────────────────┐
│ UserService.create()         │
│                              │
│ Cria um novo usuário.        │
│                              │
│ Chamado por:                 │
│ • UserController             │
│                              │
│ Depende de:                  │
│ • UserModel                  │
│ • UserRepository             │
└──────────────────────────────┘
```

A informação deve ser curta.

Para detalhes completos:

```text
[ Abrir arquivo ]
[ Inspecionar ]
```

---

# 17. IA e índice semântico

A IA não deve precisar analisar novamente todo o projeto sempre que possível.

Criar uma representação semântica reutilizável:

```text
arquivo
classe
método
função
dependência
chamador
chamada
documentação
comentários
Git status
```

A IA pode receber somente o contexto relevante.

Exemplo:

```text
Arquivo atual
+
símbolo selecionado
+
chamadores
+
dependências
+
mudanças recentes
```

Isso reduz trabalho repetido e ajuda a manter o contexto controlado.

---

# 18. Pipeline recomendado

## Fase A — Fundação

- [x] Criar Change Manager.
- [x] Separar estado IA de estado Git.
- [x] Definir modelo de eventos.
- [x] Criar tipos de eventos SSE.
- [x] Implementar patches incrementais.
- [x] Garantir que reload completo continue como fallback.

## Fase B — Change Graph

- [x] Criar aba IA/Git.
- [x] Implementar cores de novo/modificado/deletado.
- [x] Implementar legenda.
- [x] Implementar tooltip.
- [x] Implementar estado pulsante durante operação da IA.

## Fase C — Performance

- [x] Limite de nós.
- [x] Expansão sob demanda.
- [x] Preservação de layout.
- [x] Atualização incremental.
- [x] Evitar layout global.
- [x] Testes com 1.000, 3.000, 10.000+ nós.

## Fase D — Impact Graph

- [x] Seleção de alteração.
- [x] Mostrar chamadores.
- [x] Mostrar dependências.
- [x] Mostrar relações indiretas.
- [x] Criar expansão progressiva.

## Fase E — Experiência IA

- [x] Estado "AI Working".
- [x] Animação de criação.
- [x] Animação de modificação.
- [x] Animação de exclusão.
- [x] Agrupamento de alterações.
- [x] Histórico da operação.
- [x] Transição após commit.

## Fase F — Refinamento

- [x] Mini-map.
- [x] Clustering.
- [x] Controles de profundidade.
- [x] Atalhos de teclado.
- [x] Preferências de animação.
- [x] Modo de acessibilidade sem animações.
- [x] Métricas de performance.

---

# 19. Critérios de performance

Não medir somente "tempo para abrir".

Medir:

### Inicialização

```text
tempo até primeira visualização
```

### Interação

```text
tempo para expandir um nó
```

### Atualização

```text
tempo entre evento SSE e alteração visual
```

### Animação

```text
FPS durante criação de nós
```

### Memória

```text
RAM com:
100 nós
500 nós
1.000 nós
3.000 nós
10.000 nós
```

### Stress test

Simular uma IA criando:

```text
10 arquivos
25 arquivos
50 arquivos
100 arquivos
```

em sequência.

O objetivo é que o frontend continue responsivo mesmo quando o índice total do projeto for muito maior.

---

# 20. Regra de fallback

Se o gráfico atingir o limite:

```text
⚠ Visualização limitada

O projeto possui mais nós do que o limite
atual de visualização.

[ Expandir região ]
[ Aumentar limite ]
[ Abrir somente alterações ]
```

Nunca travar silenciosamente.

---

# 21. Experiência ideal

O fluxo final deve ser:

```text
Usuário pede alteração à IA
          ↓
IA começa
          ↓
Change Graph abre/atualiza
          ↓
novos nós aparecem em verde
          ↓
alterações ficam laranja
          ↓
remoções ficam vermelhas
          ↓
relações aparecem incrementalmente
          ↓
usuário acompanha a arquitetura
          ↓
IA termina
          ↓
testes/verificação
          ↓
commit
          ↓
mudanças são consolidadas
          ↓
Code Graph representa o novo estado
```

---

# 22. Princípio de UX

A interface deve responder rapidamente a três perguntas:

### "O que existe?"

**Code Graph**

### "O que mudou?"

**Change Graph**

### "O que isso afeta?"

**Impact Graph**

Essa divisão evita transformar um único gráfico em uma interface excessivamente complexa.

---

# 23. O que não fazer

Evitar:

- redesenhar todo o grafo em cada mudança;
- enviar o JSON completo a cada evento;
- recalcular todos os layouts;
- renderizar milhares de nós por padrão;
- misturar Git status e estado transitório da IA;
- fazer a animação depender do sucesso do layout global;
- perder as posições dos nós existentes;
- mostrar informação demais no tooltip;
- fazer o usuário abrir arquivos para descobrir relações simples.

---

# 24. Ordem de implementação recomendada

A sequência mais segura é:

```text
1. Change Manager
       ↓
2. Eventos SSE semânticos
       ↓
3. Patch incremental no frontend
       ↓
4. Estado IA + estado Git
       ↓
5. Change Graph
       ↓
6. Animações locais
       ↓
7. Limite de nós
       ↓
8. Expansão progressiva
       ↓
9. Impact Graph
       ↓
10. Mini-map / clustering
```

Não começar pela animação.

Primeiro garantir:

```text
evento → estado → patch → render
```

Depois colocar a animação em cima disso.

---

# 25. Visão final

O diferencial do GrafLean pode ser menos "mais uma IDE com IA" e mais:

> **uma interface visual para compreender como o software está sendo construído e modificado pela IA.**

A combinação é:

```text
Python
  +
AST
  +
índice semântico
  +
Git
  +
SSE
  +
JavaScript/Vis.js
  +
IA
  +
visualização incremental
```

O gráfico deixa de ser apenas uma representação estática de dependências.

Ele passa a representar:

**arquitetura + mudança + impacto + evolução.**

E a regra técnica que sustenta tudo isso é:

> **O backend conhece o grafo inteiro. O frontend só renderiza o que o usuário precisa ver agora.**
