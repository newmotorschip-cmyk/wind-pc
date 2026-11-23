"""Testes de memória (store, episódica, semântica)."""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from pathlib import Path
from src.memory.store import MemoryStore
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory


class TestMemoryStore(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = Path(self._tmpdir) / "test.db"
        self.store = MemoryStore(path=self._db)

    def tearDown(self):
        self.store.close()

    def test_put_and_get(self):
        iid = self.store.put(
            mem_type="episodic",
            origin="user",
            content="conteúdo de teste",
            title="Teste de inserção",
            tags=["teste", "unit"],
        )
        item = self.store.get(iid)
        self.assertIsNotNone(item)
        self.assertEqual(item["title"], "Teste de inserção")

    def test_search_fts(self):
        self.store.put(
            mem_type="semantic",
            origin="wind",
            content="Bosch EDC17 é uma ECU de motor diesel comum em veículos europeus",
            title="EDC17 overview",
            tags=["ecu", "bosch"],
        )
        results = self.store.search("Bosch EDC17", limit=5)
        self.assertGreater(len(results), 0)
        self.assertIn("EDC17", results[0]["title"])

    def test_update_state(self):
        iid = self.store.put(
            mem_type="episodic",
            origin="wind",
            content="hipótese sobre falha",
            title="Falha ABS",
        )
        self.store.update_state(iid, "validated")
        item = self.store.get(iid)
        self.assertEqual(item["state"], "validated")

    def test_delete(self):
        iid = self.store.put(
            mem_type="semantic",
            origin="user",
            content="dado temporário",
            title="Temporário",
        )
        self.store.delete(iid)
        self.assertIsNone(self.store.get(iid))

    def test_list_by_type(self):
        for i in range(3):
            self.store.put(
                mem_type="episodic",
                origin="user",
                content=f"caso {i}",
                title=f"Caso {i}",
            )
        items = self.store.list_by_type("episodic", limit=10)
        self.assertEqual(len(items), 3)


class TestEpisodicMemory(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = Path(self._tmpdir) / "ep_test.db"
        self.store = MemoryStore(path=self._db)
        self.ep = EpisodicMemory(self.store)

    def tearDown(self):
        self.store.close()

    def test_record_interaction(self):
        iid = self.ep.record_interaction(
            user_text="Como diagnostico P0300?",
            wind_text="P0300 indica falhamento múltiplo. Verifique velas e bobinas.",
            session_id="sess-001",
            model="claude-haiku-5-5",
        )
        item = self.ep.get(iid)
        self.assertIsNotNone(item)
        self.assertEqual(item["state"], "validated")

    def test_search_case(self):
        self.ep.record_case(
            title="Falha Corolla 2020 P0300",
            content={"veiculo": "Corolla 2020", "dtc": "P0300", "solucao": "troca de velas"},
            tags=["corolla", "p0300"],
        )
        results = self.ep.search("Corolla P0300")
        self.assertGreater(len(results), 0)


class TestSemanticMemory(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = Path(self._tmpdir) / "sem_test.db"
        self.store = MemoryStore(path=self._db)
        self.sem = SemanticMemory(self.store)

    def tearDown(self):
        self.store.close()

    def test_store_and_search(self):
        iid = self.sem.store_knowledge(
            title="TriCore TC1797 — base address",
            content="O TriCore TC1797 inicia a execução a partir de 0x80000000. "
                    "O flash interno mapeado em 0x80000000–0x87FFFFFF.",
            tags=["tricore", "ghidra", "baseaddress"],
            state="proposed",
        )
        results = self.sem.search("TriCore base address")
        self.assertGreater(len(results), 0)

    def test_validate_knowledge(self):
        iid = self.sem.store_knowledge(
            title="V850 — reset vector",
            content="O reset vector do V850 é 0x00000000.",
            tags=["v850"],
        )
        self.sem.validate(iid)
        item = self.sem.get(iid)
        self.assertEqual(item["state"], "validated")

    def test_format_results(self):
        self.sem.store_knowledge("Bosch ME17", "ECU gasolina comum em VW/Audi", tags=["bosch"])
        results = self.sem.search("Bosch ME17")
        formatted = self.sem.format_results(results)
        self.assertIn("[Memória semântica relevante]", formatted)
        self.assertIn("Bosch ME17", formatted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
