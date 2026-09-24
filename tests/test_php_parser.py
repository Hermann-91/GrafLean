"""
Testes automatizados para o extrator PHP (PHPParser) via unittest e pytest.
Valida extração de classes, DI, chamadas e docstrings.
"""

import unittest
from core.parsers.php_parser import PHPParser
from core.models import SymbolType, EdgeType


PHP_SAMPLE_CODE = """<?php
namespace App\\Actions;

use App\\Contracts\\GatewayPagamentoInterface;
use App\\Repositories\\PedidoRepository;

/**
 * Caso de uso responsável por processar o checkout de pedidos.
 */
class ProcessarCheckout
{
    public function __construct(
        private GatewayPagamentoInterface $gateway,
        private PedidoRepository $pedidoRepo
    ) {}

    public function executar(array $dados): bool
    {
        $sucesso = $this->gateway->cobrar($dados['valor']);
        if ($sucesso) {
            $this->pedidoRepo->salvar($dados);
            return true;
        }
        return false;
    }
}
"""


class TestPHPParser(unittest.TestCase):
    def setUp(self):
        self.parser = PHPParser()
        self.result = self.parser.parse_source(PHP_SAMPLE_CODE, "app/Actions/ProcessarCheckout.php")

    def test_php_parser_extracts_class_and_docstring(self):
        # Localiza o nó da classe
        class_nodes = [n for n in self.result.nodes if n.symbol_type == SymbolType.CLASS]
        self.assertEqual(len(class_nodes), 1)
        class_node = class_nodes[0]

        self.assertEqual(class_node.id, "App\\Actions\\ProcessarCheckout")
        self.assertEqual(class_node.name, "ProcessarCheckout")
        self.assertIn("Caso de uso responsável por processar o checkout", class_node.docstring)

    def test_php_parser_extracts_constructor_dependency_injection(self):
        inject_edges = [e for e in self.result.edges if e.edge_type == EdgeType.INJECTS]
        self.assertEqual(len(inject_edges), 2)

        targets = {e.target_id for e in inject_edges}
        self.assertIn("App\\Contracts\\GatewayPagamentoInterface", targets)
        self.assertIn("App\\Repositories\\PedidoRepository", targets)

    def test_php_parser_extracts_method_calls(self):
        call_edges = [e for e in self.result.edges if e.edge_type == EdgeType.CALLS]
        self.assertGreaterEqual(len(call_edges), 2)

        called_targets = {e.target_id for e in call_edges}
        self.assertIn("App\\Contracts\\GatewayPagamentoInterface::cobrar", called_targets)
        self.assertIn("App\\Repositories\\PedidoRepository::salvar", called_targets)


if __name__ == "__main__":
    unittest.main()
