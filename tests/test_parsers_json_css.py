"""
Testes automatizados para os parsers de JSON e CSS.
"""

import unittest
from core.parsers.json_parser import JSONParser
from core.parsers.css_parser import CSSParser
from core.models import SymbolType, EdgeType


class TestJSONAndCSSParsers(unittest.TestCase):
    def test_json_parser_package_manifest(self):
        json_code = '''{
            "name": "my-frontend-app",
            "version": "1.0.0",
            "scripts": {
                "dev": "vite",
                "build": "vite build"
            },
            "dependencies": {
                "vue": "^3.0.0",
                "axios": "^1.0.0"
            }
        }'''
        parser = JSONParser()
        result = parser.parse_source(json_code, "/app/package.json")

        self.assertEqual(len(result.nodes), 3)  # file + 2 scripts
        self.assertEqual(result.nodes[0].symbol_type, SymbolType.FILE)
        self.assertIn("my-frontend-app", result.nodes[0].docstring)

        script_names = [n.name for n in result.nodes[1:]]
        self.assertIn("npm run dev", script_names)
        self.assertIn("npm run build", script_names)

        dep_targets = [e.target_id for e in result.edges if e.edge_type == EdgeType.USES and ("vue" in e.target_id or "axios" in e.target_id)]
        self.assertIn("vue", dep_targets)
        self.assertIn("axios", dep_targets)

    def test_css_parser_imports_and_classes(self):
        css_code = '''
        @import url("./theme/colors.css");
        @import "typography.css";

        .card-container {
            display: flex;
            background: #fff;
        }

        .btn-primary {
            color: blue;
        }
        '''
        parser = CSSParser()
        result = parser.parse_source(css_code, "/app/styles/main.css")

        self.assertEqual(result.nodes[0].symbol_type, SymbolType.FILE)
        class_names = [n.name for n in result.nodes if n.symbol_type == SymbolType.FUNCTION]
        self.assertIn(".card-container", class_names)
        self.assertIn(".btn-primary", class_names)

        import_edges = [e for e in result.edges if e.edge_type == EdgeType.USES and "@import" in (e.description or "")]
        self.assertEqual(len(import_edges), 2)


if __name__ == "__main__":
    unittest.main()
