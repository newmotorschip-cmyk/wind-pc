"""Testes do roteador de modelos (sem chamadas reais de API)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from unittest.mock import patch, MagicMock
from src.core.context import ContextManager
from src.router.models import MODELS, ROUTING, TaskType, ModelSpec, ModelTier
from src.router.router import ModelRouter


class TestModelSpec(unittest.TestCase):

    def test_estimate_cost(self):
        spec = MODELS["claude-haiku-5-5"]
        cost = spec.estimate_cost(1000, 500)
        expected = (1000 * spec.cost_per_1k_input + 500 * spec.cost_per_1k_output) / 1000
        self.assertAlmostEqual(cost, expected, places=8)

    def test_local_always_free(self):
        spec = MODELS["local-stub"]
        self.assertEqual(spec.estimate_cost(10000, 10000), 0.0)

    def test_all_task_types_have_routes(self):
        for tt in TaskType:
            self.assertIn(tt, ROUTING, f"TaskType.{tt.name} sem rota definida")


class TestContextManager(unittest.TestCase):

    def test_budget_starts_full(self):
        ctx = ContextManager(daily_budget=2.0)
        self.assertEqual(ctx.daily_cost, 0.0)
        self.assertEqual(ctx.remaining, 2.0)
        self.assertTrue(ctx.can_spend(0.001))

    def test_budget_tracks_usage(self):
        ctx = ContextManager(daily_budget=1.0)
        ctx.record("claude-haiku-5-5", 1000, 500, 0.5, "conversation")
        self.assertAlmostEqual(ctx.daily_cost, 0.5)
        self.assertAlmostEqual(ctx.remaining, 0.5)

    def test_budget_blocks_overspend(self):
        ctx = ContextManager(daily_budget=0.001)
        ctx.record("claude-sonnet-5-5", 1000, 500, 0.001, "reasoning")
        self.assertFalse(ctx.can_spend(0.001))

    def test_summary_keys(self):
        ctx = ContextManager()
        s = ctx.summary()
        for key in ("daily_cost_usd", "daily_budget_usd", "remaining_usd", "calls_today"):
            self.assertIn(key, s)


class TestModelRouter(unittest.TestCase):

    def _make_router(self, anthropic_key="test-key", openai_key=""):
        ctx = ContextManager(daily_budget=10.0)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": anthropic_key, "OPENAI_API_KEY": openai_key}):
            return ModelRouter(ctx), ctx

    def test_pick_haiku_for_conversation(self):
        ctx = ContextManager(daily_budget=10.0)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            router = ModelRouter(ctx)
            model = router._pick_model(TaskType.CONVERSATION)
        self.assertEqual(model.id, "claude-haiku-5-5")

    def test_pick_sonnet_for_reasoning(self):
        ctx = ContextManager(daily_budget=10.0)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            router = ModelRouter(ctx)
            model = router._pick_model(TaskType.REASONING)
        self.assertEqual(model.id, "claude-sonnet-5-5")

    def test_fallback_when_no_openai(self):
        """Sem OPENAI_API_KEY, CODING deve cair para Sonnet (anthropic)."""
        ctx = ContextManager(daily_budget=10.0)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True):
            # Garantir que OPENAI_API_KEY não está no ambiente
            os.environ.pop("OPENAI_API_KEY", None)
            router = ModelRouter(ctx)
            model = router._pick_model(TaskType.CODING)
        self.assertEqual(model.provider, "anthropic")

    def test_raises_when_no_models_available(self):
        ctx = ContextManager(daily_budget=10.0)
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            router = ModelRouter(ctx)
            with self.assertRaises(RuntimeError):
                router._pick_model(TaskType.CONVERSATION)

    def test_call_with_mocked_claude(self):
        ctx = ContextManager(daily_budget=10.0)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            router = ModelRouter(ctx)
            with patch.object(router._claude, "call", return_value=("resposta mock", 100, 50)):
                text, model_id, cost = router.call(
                    messages=[{"role": "user", "content": "olá"}],
                    system="system",
                    task_type=TaskType.CONVERSATION,
                )
        self.assertEqual(text, "resposta mock")
        self.assertEqual(model_id, "claude-haiku-5-5")
        self.assertGreater(cost, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
