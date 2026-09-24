"""
Motor de Resumos Semânticos Inteligentes.
Infere a responsabilidade de classes, métodos e arquivos analisando seus papéis arquiteturais
e suas conexões ativas no grafo de dependências.
"""

from typing import Dict, List, Optional
from core.models import Node, Edge, SymbolType


class SemanticSummarizer:
    @staticmethod
    def infer_summary(node: Node, inbound_ids: List[str], outbound_ids: List[str], nodes_dict: Dict[str, Node]) -> str:
        """Gera um resumo semântico caso o nó não possua docstring manual."""
        if node.docstring and len(node.docstring.strip()) > 5:
            return node.docstring

        name = node.name
        stype = node.symbol_type

        # 1. Resumos para Classes
        if stype == SymbolType.CLASS:
            return SemanticSummarizer._summarize_class(node, inbound_ids, outbound_ids, nodes_dict)

        # 2. Resumos para Interfaces
        if stype == SymbolType.INTERFACE:
            return f"Contrato de interface que define a especificação para {name.replace('Interface', '')}."

        # 3. Resumos para Métodos
        if stype == SymbolType.METHOD:
            return SemanticSummarizer._summarize_method(node, outbound_ids, nodes_dict)

        # 4. Resumos para Arquivos
        if stype == SymbolType.FILE:
            return SemanticSummarizer._summarize_file(node)

        # 5. Funções gerais / Componentes
        if stype == SymbolType.FUNCTION:
            if name[0].isupper():
                return f"Componente de interface visual React ({name})."
            if name.startswith("use"):
                return f"Custom Hook React para gerenciamento de estado e regras ({name})."
            return f"Função utilitária ({name})."

        return f"Elemento estrutural {name} ({stype.value})."

    @staticmethod
    def _summarize_class(node: Node, inbound_ids: List[str], outbound_ids: List[str], nodes_dict: Dict[str, Node]) -> str:
        name = node.name
        deps = [nodes_dict[d].name for d in outbound_ids if d in nodes_dict and nodes_dict[d].symbol_type == SymbolType.CLASS]
        deps_str = f" Depende de: {', '.join(deps[:3])}." if deps else ""

        if name.endswith("Action"):
            clean_name = name.replace("Action", "")
            return f"Caso de Uso (Application Layer) responsável por orquestrar a operação de {clean_name}.{deps_str}"

        if name.endswith("Controller"):
            clean_name = name.replace("Controller", "")
            return f"Controlador HTTP (Presentation Layer) que recebe requisições de {clean_name}, valida dados e delega para casos de uso.{deps_str}"

        if name.endswith("Request"):
            return f"Form Request de validação e autorização para dados da requisição HTTP ({name})."

        if name.endswith("Resource"):
            return f"API Resource responsável pela serialização e formatação da resposta JSON ({name})."

        if name.endswith("Repository"):
            return f"Repositório de persistência e consulta a dados no banco ({name}).{deps_str}"

        if name.endswith("Service") or "Gateway" in name:
            return f"Serviço de integração ou regra de infraestrutura ({name}).{deps_str}"

        if name.endswith("Exception"):
            return f"Exceção de domínio disparada quando uma regra ou invariante de negócio é violada ({name})."

        if "Test" in name:
            return f"Suíte de testes automatizados para validação de comportamento de {name.replace('Test', '')}."

        return f"Entidade ou modelo de domínio ({name}).{deps_str}"

    @staticmethod
    def _summarize_method(node: Node, outbound_ids: List[str], nodes_dict: Dict[str, Node]) -> str:
        name = node.name
        if name == "__construct":
            return "Método construtor responsável pela inicialização e injeção de dependências."
        if name in ("execute", "executar", "handle", "run"):
            return "Ponto de entrada que executa o fluxo principal da regra de negócio."
        if name.startswith("validate") or name == "rules":
            return "Aplica regras de validação sobre os dados fornecidos."
        if name.startswith("get") or name.startswith("set"):
            return f"Acessor de propriedade ({name})."
        if name == "toArray":
            return "Converte a entidade ou recurso em array associativo para serialização."
        if name in ("charge", "cobrar", "pay"):
            return "Processa a transação financeira de pagamento junto ao provedor."
        if name in ("notify", "send", "enviar"):
            return "Dispara notificações ou comunicações externas."
        return f"Método {name}() que executa operações internas da classe."

    @staticmethod
    def _summarize_file(node: Node) -> str:
        path = node.file_path
        if "Domain" in path:
            return f"Arquivo da Camada de Domínio ({node.name}), contendo regras de negócio centrais e entidades puras."
        if "Application" in path or "Actions" in path:
            return f"Arquivo da Camada de Aplicação ({node.name}), orquestrando casos de uso."
        if "Infrastructure" in path or "Gateways" in path:
            return f"Arquivo da Camada de Infraestrutura ({node.name}), lidando com banco, rede e serviços externos."
        if "Presentation" in path or "Controllers" in path:
            return f"Arquivo da Camada de Apresentação ({node.name}), lidando com entrada e saída HTTP."
        if "tests" in path.lower():
            return f"Arquivo de testes automatizados ({node.name})."
        return f"Arquivo de código-fonte {node.name}."
