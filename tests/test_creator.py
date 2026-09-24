"""
Testes unitários para o módulo core.creator.
Verifica a criação segura de pastas, proteção contra path traversal
e criação de especificações Markdown com templates para orquestração de agentes.
"""

import os
import shutil
import tempfile
import unittest
from core.creator import (
    create_folder, create_markdown_spec, is_safe_path,
    rename_resource, delete_resource, TEMPLATES
)


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

    def test_rename_resource_success(self):
        old_file = create_markdown_spec(self.test_dir, "docs/OLD.md")
        self.assertTrue(os.path.isfile(old_file))

        new_file = rename_resource(self.test_dir, "docs/OLD.md", "NEW.md")
        self.assertFalse(os.path.exists(old_file))
        self.assertTrue(os.path.isfile(new_file))
        self.assertTrue(new_file.endswith("NEW.md"))

    def test_rename_resource_traversal_rejection(self):
        create_markdown_spec(self.test_dir, "docs/OLD.md")
        with self.assertRaises(ValueError):
            rename_resource(self.test_dir, "docs/OLD.md", "../../evil.md")

    def test_delete_resource_file_and_directory(self):
        file_path = create_markdown_spec(self.test_dir, "to_delete/TEST.md")
        self.assertTrue(os.path.isfile(file_path))

        delete_resource(self.test_dir, "to_delete/TEST.md")
        self.assertFalse(os.path.exists(file_path))

        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, "to_delete")))
        delete_resource(self.test_dir, "to_delete")
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "to_delete")))

    def test_delete_resource_root_protection(self):
        with self.assertRaises(ValueError):
            delete_resource(self.test_dir, ".")
        with self.assertRaises(ValueError):
            delete_resource(self.test_dir, "")


if __name__ == "__main__":
    unittest.main()
