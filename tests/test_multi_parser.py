"""
Testes automatizados para os parsers de Python, JavaScript/TypeScript,
HTML/Blade e o ParserRegistry usando unittest nativo.
"""

import unittest
from core.parsers.registry import ParserRegistry
from core.parsers.python_parser import PythonParser
from core.parsers.js_ts_parser import JSTypeScriptParser
from core.parsers.html_blade_parser import HTMLBladeParser
from core.models import SymbolType, EdgeType


class TestMultiLanguageParsers(unittest.TestCase):
    def setUp(self):
        self.registry = ParserRegistry()

    def test_registry_detects_correct_parser(self):
        self.assertIsInstance(self.registry.get_parser_for_file("app.py"), PythonParser)
        self.assertIsInstance(self.registry.get_parser_for_file("Checkout.tsx"), JSTypeScriptParser)
        self.assertIsInstance(self.registry.get_parser_for_file("index.html"), HTMLBladeParser)
        self.assertIsInstance(self.registry.get_parser_for_file("layout.blade.php"), HTMLBladeParser)

    def test_python_parser_extracts_classes_and_calls(self):
        code = '''
class OrderService(BaseService):
    """Gerencia pedidos."""
    def process(self, order):
        self.repo.save(order)
'''
        parser = PythonParser()
        result = parser.parse_source(code, "services/order.py")
        classes = [n for n in result.nodes if n.symbol_type == SymbolType.CLASS]
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, "OrderService")
        self.assertEqual(classes[0].docstring, "Gerencia pedidos.")

    def test_js_ts_parser_extracts_react_components_and_hooks(self):
        code = '''
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import Header from './Header';

export const CheckoutView = () => {
    const { user } = useAuth();
    return <Header />;
};
'''
        parser = JSTypeScriptParser()
        result = parser.parse_source(code, "components/CheckoutView.tsx")
        funcs = [n for n in result.nodes if n.symbol_type == SymbolType.FUNCTION]
        self.assertEqual(len(funcs), 1)
        self.assertEqual(funcs[0].name, "CheckoutView")
        self.assertEqual(funcs[0].docstring, "Componente React")

        calls = [e for e in result.edges if e.edge_type == EdgeType.CALLS]
        call_descs = [e.description for e in calls]
        self.assertTrue(any("Uso do Hook useAuth" in (d or "") for d in call_descs))
        self.assertTrue(any("Renderiza <Header />" in (d or "") for d in call_descs))

    def test_html_blade_parser_extracts_extends_and_components(self):
        code = '''
@extends('layouts.app')
@include('partials.nav')
<x-alert type="success" />
<link rel="stylesheet" href="style.css">
'''
        parser = HTMLBladeParser()
        result = parser.parse_source(code, "resources/views/home.blade.php")
        edges = result.edges
        targets = {e.target_id for e in edges}
        self.assertIn("blade://layouts.app", targets)
        self.assertIn("blade://partials.nav", targets)
        self.assertIn("blade-component://alert", targets)
        self.assertIn("asset://style.css", targets)


if __name__ == "__main__":
    unittest.main()
