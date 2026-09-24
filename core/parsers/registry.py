"""
ParserRegistry (Design Pattern: Factory / Registry).
Seleciona automaticamente o parser correto com base na extensão do arquivo.
"""

from typing import Dict, Optional
from core.parsers.base import BaseParser
from core.parsers.php_parser import PHPParser
from core.parsers.python_parser import PythonParser
from core.parsers.js_ts_parser import JSTypeScriptParser
from core.parsers.html_blade_parser import HTMLBladeParser


class ParserRegistry:
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._register_defaults()

    def _register_defaults(self):
        php = PHPParser()
        python = PythonParser()
        js_ts = JSTypeScriptParser()
        html = HTMLBladeParser()

        self._parsers[".php"] = php
        self._parsers[".py"] = python
        self._parsers[".js"] = js_ts
        self._parsers[".jsx"] = js_ts
        self._parsers[".ts"] = js_ts
        self._parsers[".tsx"] = js_ts
        self._parsers[".html"] = html
        self._parsers[".blade.php"] = html

    def get_parser_for_file(self, file_path: str) -> Optional[BaseParser]:
        """Retorna o parser correspondente ou None caso a extensão não seja suportada."""
        if file_path.endswith(".blade.php"):
            return self._parsers[".blade.php"]
        for ext, parser in self._parsers.items():
            if file_path.endswith(ext):
                return parser
        return None
