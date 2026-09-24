"""
Testes unitários para o módulo core.creator.
Verifica a criação segura de pastas, proteção contra path traversal
e criação de especificações Markdown com templates para orquestração de agentes.
"""

import os
import shutil
import tempfile
import unittest
from core.creator import create_folder, create_markdown_spec, is_safe_path, TEMPLATES


class TestProjectCreator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_safe_path_validation(self):
        self.assertTrue(is_safe_path(self.test_dir, "docs/specs"))
        self.assertTrue(is_safe_path(self.test_dir, "TASK.md"))
        self.assertFalse(is_safe_path(self.test_dir, "../../etc/passwd"))
        self.assertFalse(is_safe_path(self.test_dir, "/etc/shadow"))

    def test_create_folder_success(self):
        target = "src/services/billing"
        folder_path = create_folder(self.test_dir, target)
        self.assertTrue(os.path.isdir(folder_path))
        self.assertEqual(folder_path, os.path.join(self.test_dir, target))

    def test_create_folder_traversal_rejection(self):
        with self.assertRaises(ValueError):
            create_folder(self.test_dir, "../out-of-bounds")

    def test_create_markdown_task_template(self):
        file_path = create_markdown_spec(
            self.test_dir,
            "docs/TASK_CHECKOUT.md",
            template_key="task",
            context_data={
                "target": "CheckoutService",
                "inbound": "OrderController",
                "outbound": "PaymentGateway"
            }
        )
        self.assertTrue(os.path.isfile(file_path))
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("# 📋 Tarefa do Agente", content)
        self.assertIn("CheckoutService", content)
        self.assertIn("OrderController", content)
        self.assertIn("PaymentGateway", content)

    def test_create_markdown_spec_template(self):
        file_path = create_markdown_spec(
            self.test_dir,
            "architecture/SPEC.md",
            template_key="spec"
        )
        self.assertTrue(os.path.isfile(file_path))
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("# 🏛️ Especificação Arquitetural", content)

    def test_create_markdown_traversal_rejection(self):
        with self.assertRaises(ValueError):
            create_markdown_spec(self.test_dir, "../../evil.md")


if __name__ == "__main__":
    unittest.main()
