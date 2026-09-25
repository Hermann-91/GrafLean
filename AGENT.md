# Contrato do Agente de Engenharia — GrafLean 🔍🧠

Este documento define as diretrizes técnicas, arquiteturais e comportamentais para qualquer assistente de IA ou agente autônomo que atue no desenvolvimento desta ferramenta.

---

## 1. Missão Primordial do Projeto
Construir uma **Architecture-First IDE & Hub Centralizado (PWA Local)** de alta performance que elimine a sobrecarga cognitiva da navegação em sistemas complexos, fornecendo visualização instantânea de arquitetura, relações entre arquivos, classes e funções, e métricas de acoplamento em tempo real.

---

## 2. Princípios de Atuação e Regras Não-Negociáveis ⚠️

### 1. Orçamento Rigoroso de Latência (< 15ms)
- Respostas e renderização da árvore e nós de código devem ser instantâneas.
- **Regra de Ouro:** NUNCA faça I/O de disco pesado, consultas de rede ou extrações complexas durante a execução do hover.
- O grafo deve ser carregado em memória no startup ou atualizado em thread secundária assíncrona.
- A busca por símbolo durante o hover deve ter complexidade $O(1)$.

### 2. Separação Estrita de Responsabilidades (Clean Architecture)
- O diretório `core/` é o núcleo da aplicação e **NÃO PODE DEPENDER** de bibliotecas externas ou frameworks de terceiros.
- O `core/` deve ser executável via CLI independente e 100% testável com `unittest`.
- Camadas de apresentação (Web UI / PWA / CLI) apenas consomem o `core/` sem vazar lógica de domínio.

### 3. Honestidade e Precisão do Grafo (Regra Graphify)
- O extrator sintático nunca deve inventar conexões hipotéticas.
- Conexões determinísticas (ex: `new PedidoRepository()`, `$this->service->process()`, `use App\Models\User`) são arestas concretas.
- Chamadas dinâmicas ou resoluções de container não determinísticas devem ser marcadas como `AMBIGUOUS` ou `DYNAMIC`.
- Ciclos de dependência (A ➔ B ➔ A) devem ser detectados e sinalizados como alertas arquiteturais.

### 4. Ergonomia Cognitiva para o Desenvolvedor (Pensamento Top-Down)
- O desenvolvedor tem raciocínio sistêmico em teia: precisa ver de onde o dado vem e para onde vai antes que a função isolada faça sentido.
- O pop-up deve sempre responder:
  1. *O que é este elemento e qual sua responsabilidade?*
  2. *Quem o chama? (Inbound / Ca)*
  3. *Do que ele depende? (Outbound / Ce)*
  4. *Qual é o diagnóstico de saúde arquitetural?*
- Links clicáveis na interface de árvore e grafo devem navegar imediatamente para o arquivo e linha de destino no editor integrado.

### 5. Qualidade e Testes Contínuos (TDD)
- Todo parser, modelo e analisador de métricas deve conter cobertura de testes em `tests/`.
- Testar com trechos reais de código em PHP 8+ e Python.

---

## 3. Modos de Operação do Agente
1. **Modo Planejador / Arquiteto:** Antes de codificar um componente, detalha interfaces e fluxos no formato Clean Code / SOLID.
2. **Modo Implementador:** Código tipado, limpo, modular e com tratamento gracioso de erros (sem quebrar a renderização caso um arquivo tenha erro de sintaxe).
3. **Modo Validador:** Execução de `pytest` e checagem de integridade das arestas antes de considerar uma tarefa concluída.
