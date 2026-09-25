"""
Testes automatizados para a extração de rotas HTTP em Python, PHP e JavaScript.
"""

import unittest
from core.parsers.python_parser import PythonParser
from core.parsers.php_parser import PHPParser
from core.parsers.js_ts_parser import JSTypeScriptParser
from core.models import SymbolType, EdgeType


class TestHttpRouteExtraction(unittest.TestCase):
    def test_python_fastapi_and_flask_routes(self):
        code = '''
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/v1/users")
async def get_users():
    return []

@router.post("/api/v1/users")
def create_user():
    return {}
'''
        parser = PythonParser()
        result = parser.parse_source(code, "/app/api/users.py")

        route_nodes = [n for n in result.nodes if n.id.startswith("http://")]
        self.assertEqual(len(route_nodes), 2)
        route_names = [n.name for n in route_nodes]
        self.assertIn("🌐 GET /api/v1/users", route_names)
        self.assertIn("🌐 POST /api/v1/users", route_names)

        # Valida que a rota aponta para a função handler via CALLS
        call_edges = [e for e in result.edges if e.source_id.startswith("http://") and e.edge_type == EdgeType.CALLS]
        self.assertEqual(len(call_edges), 2)

    def test_php_laravel_routes(self):
        code = '''<?php
namespace App\\Routes;
use App\\Http\\Controllers\\UserController;

Route::get('/users', [UserController::class, 'index']);
Route::post('/users', 'UserController@store');
'''
        parser = PHPParser()
        result = parser.parse_source(code, "/app/routes/api.php")

        route_nodes = [n for n in result.nodes if n.id.startswith("http://")]
        self.assertEqual(len(route_nodes), 2)
        self.assertIn("🌐 GET /users", [n.name for n in route_nodes])

        calls = [e for e in result.edges if e.source_id == "http://get:/users" and e.edge_type == EdgeType.CALLS]
        self.assertTrue(len(calls) > 0)
        self.assertIn("UserController::index", calls[0].target_id)

    def test_express_routes(self):
        code = '''
const express = require('express');
const router = express.Router();

router.get('/products', (req, res) => res.json([]));
router.post('/checkout', (req, res) => res.json({}));
'''
        parser = JSTypeScriptParser()
        result = parser.parse_source(code, "/app/routes/shop.js")

        route_nodes = [n for n in result.nodes if n.id.startswith("http://")]
        self.assertEqual(len(route_nodes), 2)
        self.assertIn("🌐 GET /products", [n.name for n in route_nodes])
        self.assertIn("🌐 POST /checkout", [n.name for n in route_nodes])


if __name__ == "__main__":
    unittest.main()
