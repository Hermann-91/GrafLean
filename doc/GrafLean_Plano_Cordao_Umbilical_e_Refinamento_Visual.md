# 🌐 GrafLean — Plano de Evolução: Cordão Umbilical (Full-Stack AST) & Linhas Retina

> **Mapeamento determinístico da ponte Front-end ↔ Back-end e refinamento estético premium de conexões no Grafo.**

---

## 1. Contexto e Motivação Técnica

Nas literaturas clássicas de Arquitetura de Software (*Clean Architecture* de Robert C. Martin e *Building Microservices* de Sam Newman), o limite mais crítico de um sistema reside na fronteira entre a camada de apresentação (*Front-end*) e a camada de serviços/domínio (*Back-end*).

Atualmente, o GrafLean analisa com primor as estruturas internas de cada tecnologia de forma isolada:
- No **Back-end** (Python, PHP, Node.js), mapeia classes, métodos, herança e registra endpoints com IDs canônicos universais: `http://{method}:{path}`.
- No **Front-end** (JS, TS, HTML, Blade), mapeia imports locais, hierarquia de classes, componentes React/JSX e inclusão de assets.

### ⚠️ O Ponto Cego (O "Cordão Umbilical" Quebrado):
O front-end consome o back-end via protocolos de rede (chamadas `fetch()`, instâncias do `axios`, chamadas `apiClient` e submissões `<form action="...">`). Como os analisadores de front-end ignoravam essas chamadas clientes, o front-end e o back-end apareciam no grafo como duas "ilhas" desconectadas.

Além disso, as conexões visuais no Vis.js foram configuradas com larguras pesadas (`width: 2.2` / `1.2`), criando linhas grosseiras que geram sobrecarga visual em bases com mais de 50 nós.

---

## 2. Objetivos Principais

1. **Estabelecer o Cordão Umbilical Front ↔ Back:** Detectar chamadas de rede no código cliente (JS, TS, React, Vue, HTML, Blade) e conectá-las diretamente aos endpoints e controllers já mapeados no back-end.
2. **Refinamento Estético das Linhas (Padrão Retina/Linear):** Reduzir a espessura das arestas para valores ultrafinos (`0.75px` a `1.35px`), pontas de seta sutis (`scaleFactor: 0.42`) e suavização visual para eliminar o aspecto grosseiro.
3. **Garantia de Qualidade em Dupla Camada:** Cada fase conterá testes automatizados unitários/integração e um roteiro de conferência humana para validação interativa no navegador.

---

## 3. Planejamento Faseado de Execução

```text
[ Fase 1: Retina Lines ] ──> Testes + Teste Humano
          ↓
[ Fase 2: JS/TS Client HTTP ] ──> Testes + Teste Humano
          ↓
[ Fase 3: HTML Forms & Actions ] ──> Testes + Teste Humano
          ↓
[ Fase 4: Linker Canônico ] ──> Testes + Teste Humano
          ↓
[ Fase 5: Release & Changelog ]
```

---

### 🎨 FASE 1: Refinamento Estético das Linhas (Retina & Clean Edges)

- **Objetivo:** Tornar as linhas do grafo visualmente leves, nítidas e elegantes no padrão Monokai OLED.
- **Implementações Técnicas:**
  - Arquivo: `core/visualizer/assets/scripts/app.js`
  - Redução de largura padrão das arestas: de `1.2px` para `0.75px`.
  - Redução de largura sob foco (inbound/outbound): de `2.2px` para `1.35px`.
  - Redução da escala das pontas de setas: de `scaleFactor: 0.75` para `0.42`.
  - Ajuste de opacidade em repouso: `rgba(255, 255, 255, 0.10)`.
  - Seleção e hover equilibrados: `selectionWidth: 1.6` e `hoverWidth: 1.0`.

#### 🧪 Testes da Fase 1:
- **Automatizado:** Executar `python3 -m unittest discover -s tests` garantindo que os 92 testes continuem íntegros sem quebra de asserções no visualizador.
- **👁️ Teste Humano (Conferência no Navegador):**
  1. Abrir o workspace no navegador (`http://127.0.0.1:7357/p/...`).
  2. Verificar visualmente se as linhas estão finas, discretas e não poluem a leitura dos nomes dos arquivos.
  3. Clicar em um nó e conferir se o realce das linhas conectadas (ciano para envio, âmbar para recebimento) é elegante e preciso.

---

### ⚡ FASE 2: Analisador Front-end JS/TypeScript para Chamadas HTTP (Client AST)

- **Objetivo:** Detectar chamadas de saída via `fetch`, `axios` e `apiClient` em arquivos `.js`, `.jsx`, `.ts`, `.tsx`.
- **Implementações Técnicas:**
  - Arquivo: `core/parsers/js_ts_parser.py`
  - Expressões Regulares de Alta Performance:
    - **`fetch()`:** Captura a URL do primeiro argumento e o método (padrão `GET`, ou `POST`/`PUT`/`DELETE` se configurado no objeto de opções).
    - **`axios` e `apiClient`:** Captura chamadas como `axios.get('/api/users')`, `axios.post('/api/save', payload)`, `apiClient.delete(...)`.
  - Geração de Arestas Semânticas:
    - Criar `Edge(source_id=file_node_id, target_id="http://{method}:{path}", edge_type=EdgeType.CALLS, description="Chamada API HTTP: {METHOD} {PATH}")`.

#### 🧪 Testes da Fase 2:
- **Automatizado:** Criar teste unitário em `tests/test_js_ts_http_parser.py` validando extração de `fetch()` e `axios` em exemplos de React e TypeScript.
- **👁️ Teste Humano (Conferência no Terminal e Dados):**
  1. Executar inspeção via CLI em um arquivo JS/TS que faça requisições.
  2. Conferir se os nós das rotas HTTP aparecem na lista de saídas (*Outbound*) do arquivo inspecionado.

---

### 📄 FASE 3: Analisador Front-end HTML & Blade para Formulários e Ações

- **Objetivo:** Detectar submissões de dados e rotas em templates `.html` e `.blade.php`.
- **Implementações Técnicas:**
  - Arquivo: `core/parsers/html_blade_parser.py`
  - Captura de tags `<form>`:
    - Regex: `<form\s+[^>]*action=['"](?P<action>[^'"]+)['"](?:\s+[^>]*method=['"](?P<method>[a-zA-Z]+)['"])?`
    - Método padrão: `GET` caso omitido, ou `POST`/`PUT` conforme atributo.
  - Geração de Arestas Semânticas:
    - `Edge(source_id=file_node_id, target_id="http://{method}:{action}", edge_type=EdgeType.CALLS, description="Submissão de Formulário")`.

#### 🧪 Testes da Fase 3:
- **Automatizado:** Criar teste unitário em `tests/test_html_forms_parser.py` validando extração de `<form action="/api/login" method="POST">`.
- **👁️ Teste Humano (Conferência):**
  1. Verificar se um template HTML contendo `<form>` aponta para o endpoint correto.

---

### 🔗 FASE 4: Linker Arquitetural no `ProjectGraph` (A União do Cordão Umbilical)

- **Objetivo:** Conectar a aresta gerada pelo front-end diretamente ao nó canônico da rota e do controller gerados pelo back-end.
- **Implementações Técnicas:**
  - Arquivo: `core/graph.py` (método `_link_and_resolve_edges`)
  - **Normalização de Rotas HTTP:**
    - Tratamento de barras iniciais e finais (`/api/projects` vs `api/projects/`).
    - Desconsiderar query parameters em chamadas do front (ex: `/api/search?q=teste` resolve para a rota base `/api/search`).
    - Vinculação com os nós já criados por FastAPI, Flask, Laravel e Express (`http://get:/api/projects`).
  - **Inspeção Bidirecional:**
    - Ao inspecionar o arquivo JS no Inspetor, o painel *Outbound* exibe o endpoint HTTP.
    - Ao inspecionar a rota ou controller do back-end, o painel *Inbound* exibe exatamente os arquivos de front-end que a consomem.

#### 🧪 Testes da Fase 4:
- **Automatizado:** Teste de integração end-to-end em `tests/test_fullstack_umbilical.py` criando um mini-projeto com Front-end (React/JS) e Back-end (Python/FastAPI) e validando o caminho completo `JS -> Rota HTTP -> Controller Python`.
- **👁️ Teste Humano (Conferência Visual Completa):**
  1. Abrir o projeto no navegador.
  2. Clicar com 1 clique em um arquivo front-end (ex: `app.js`).
  3. Observar a linha saindo do arquivo front-end e conectando-se diretamente ao nó do endpoint back-end.
  4. Clicar no endpoint e conferir no painel lateral de métricas (*Inspetor*) a relação de chamada direta.

---

### 📦 FASE 5: Consolidação, Changelog & Versão

- **Objetivo:** Atualizar documentação, registrar a versão no `CHANGELOG.md` e validar 100% da suíte de testes.
- **Implementações Técnicas:**
  - Registro da versão correspondente no `CHANGELOG.md`.
  - Execução da suíte completa de testes.
  - Commits atômicos no Git.

---

## 4. Critérios de Aceitação

- [ ] Todas as arestas do Vis.js renderizadas com espessura fina e elegante (`0.75px` a `1.35px`).
- [ ] Chamadas `fetch()` e `axios` em arquivos JS/TS mapeadas como conexões no grafo.
- [ ] Formulários HTML/Blade com `action` mapeados para seus respectivos endpoints.
- [ ] Arestas entre front-end e back-end perfeitamente resolvidas e visíveis no grafo.
- [ ] Suíte de testes automatizados com 100% de sucesso.
- [ ] Validação humana aprovada no navegador em cada fase.
