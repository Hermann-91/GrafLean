"""
Testes unitários para o ChangeManager.
Valida separação de estados da IA e Git, eventos semânticos e cálculo de deltas.
"""

import unittest
from core.change_manager import ChangeManager, AIState, GitState, ChangeEvent


class TestChangeManager(unittest.TestCase):
    def setUp(self):
        self.cm = ChangeManager("/mock/project")

    def test_sse_event_formatting(self):
        evt = ChangeEvent(event="node_created", data={"path": "auth/token.py", "status": "new"})
        sse_str = evt.to_sse()

        self.assertTrue(sse_str.startswith("event: node_created\n"))
        self.assertIn('"path": "auth/token.py"', sse_str)
        self.assertTrue(sse_str.endswith("\n\n"))

    def test_ai_state_transitions_and_subscribers(self):
        received_events = []
        self.cm.subscribe(lambda e: received_events.append(e))

        # IA inicia criação
        evt = self.cm.set_ai_state("auth/service.py", AIState.CREATING)
        self.assertEqual(evt.event, "ai_state")
        self.assertEqual(evt.data["state"], "creating")
        self.assertEqual(len(received_events), 1)

        # IA edita
        self.cm.set_ai_state("auth/service.py", "editing")
        self.assertEqual(self.cm.ai_states["auth/service.py"], AIState.EDITING)
        self.assertEqual(len(received_events), 2)

        # IA finaliza
        clear_evt = self.cm.clear_ai_state("auth/service.py")
        self.assertIsNotNone(clear_evt)
        self.assertEqual(clear_evt.data["state"], "idle")
        self.assertNotIn("auth/service.py", self.cm.ai_states)

    def test_filesystem_delta_emits_semantic_events(self):
        old_snap = {
            "/p/existing.py": 100.0,
            "/p/to_modify.py": 100.0,
            "/p/to_delete.py": 100.0
        }
        new_snap = {
            "/p/existing.py": 100.0,         # Intacto
            "/p/to_modify.py": 200.0,        # Modificado
            "/p/new_file.py": 150.0          # Criado
        }

        events = self.cm.compute_filesystem_delta(old_snap, new_snap)
        event_types = {e.event: e.data["path"] for e in events}

        self.assertIn("node_created", event_types)
        self.assertEqual(event_types["node_created"], "/p/new_file.py")

        self.assertIn("node_changed", event_types)
        self.assertEqual(event_types["node_changed"], "/p/to_modify.py")

        self.assertIn("node_deleted", event_types)
        self.assertEqual(event_types["node_deleted"], "/p/to_delete.py")

    def test_git_status_transitions_and_summary(self):
        status_map = {
            "auth/token.py": "new",
            "auth/service.py": "modified"
        }
        self.cm.update_git_status(status_map)

        summary = self.cm.get_summary()
        self.assertEqual(summary["git_summary"]["new"], 1)
        self.assertEqual(summary["git_summary"]["modified"], 1)
        self.assertEqual(summary["git_summary"]["deleted"], 0)
        self.assertEqual(summary["git_summary"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
