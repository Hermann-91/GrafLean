"""
Testes automatizados para os parsers de Python, JavaScript/TypeScript,
HTML/Blade e o ParserRegistry usando unittest nativo.
"""

import unittest
from core.parsers.registry import ParserRegistry
from core.parsers.python_parser import PythonParser
from core.parsers.js_ts_parser import JSTypeScriptParser
from core.parsers.html_blade_parser import HTMLBladeParser
from core.parsers.markdown_parser import MarkdownParser
from core.models import SymbolType, EdgeType


class TestMultiLanguageParsers(unittest.TestCase):
    def setUp(self):
        self.registry = ParserRegistry()

    def test_registry_detects_correct_parser(self):
        self.assertIsInstance(self.registry.get_parser_for_file("app.py"), PythonParser)
        self.assertIsInstance(self.registry.get_parser_for_file("Checkout.tsx"), JSTypeScriptParser)
        self.assertIsInstance(self.registry.get_parser_for_file("index.html"), HTMLBladeParser)
        self.assertIsInstance(self.registry.get_parser_for_file("layout.blade.php"), HTMLBladeParser)
        self.assertIsInstance(self.registry.get_parser_for_file("TASK.md"), MarkdownParser)

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

    def test_markdown_parser_extracts_title_sections_and_links(self):
        code = '''# 📋 Tarefa do Agente

## 🎯 Objetivo
Executar testes.

## 🔗 Referências
Veja [Order](src/Domain/Models/Order.php) para detalhes.
'''
        parser = MarkdownParser()
        result = parser.parse_source(code, "tasks/TASK.md")
        files = [n for n in result.nodes if n.symbol_type == SymbolType.FILE]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "TASK.md")
        self.assertEqual(files[0].docstring, "📋 Tarefa do Agente")

        funcs = [n for n in result.nodes if n.symbol_type == SymbolType.FUNCTION]
        sec_names = [f.name for f in funcs]
        self.assertIn("🎯 Objetivo", sec_names)
        self.assertIn("🔗 Referências", sec_names)

        links = [e for e in result.edges if e.edge_type == EdgeType.CALLS]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].target_id, "src/Domain/Models/Order.php")


if __name__ == "__main__":
    unittest.main()
