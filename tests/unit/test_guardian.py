"""Testes do Guardian (classificador + validador)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import unittest
from src.guardian.classifier import DataClass, classify, classify_batch
from src.guardian.validator import GuardianValidator, ValidationError


class TestClassifier(unittest.TestCase):

    def test_public(self):
        self.assertEqual(classify("Como calibrar o mapa de torque do Bosch EDC17?"), DataClass.PUBLIC)

    def test_secret_api_key(self):
        self.assertEqual(classify("Minha ANTHROPIC_API_KEY=sk-ant-abc123"), DataClass.SECRET)

    def test_secret_password(self):
        self.assertEqual(classify("senha: minhasenha123"), DataClass.SECRET)

    def test_financial_cpf(self):
        self.assertEqual(classify("CPF do cliente: 123.456.789-00"), DataClass.FINANCIAL)

    def test_financial_cnpj(self):
        self.assertEqual(classify("CNPJ: 12.345.678/0001-90"), DataClass.FINANCIAL)

    def test_personal_placa(self):
        self.assertEqual(classify("Veículo placa ABC-1234"), DataClass.PERSONAL)

    def test_personal_email(self):
        self.assertEqual(classify("Contato: joao@example.com"), DataClass.PERSONAL)

    def test_client_keyword(self):
        self.assertEqual(classify("nome do cliente: João Silva"), DataClass.CONFIDENTIAL_CLIENT)

    def test_classify_batch_most_sensitive(self):
        texts = ["Bosch EDC17", "ANTHROPIC_API_KEY=sk-123", "mapa de torque"]
        self.assertEqual(classify_batch(texts), DataClass.SECRET)

    def test_classify_batch_public_only(self):
        texts = ["Ghidra TriCore", "firmware análise", "calibração"]
        self.assertEqual(classify_batch(texts), DataClass.PUBLIC)


class TestValidator(unittest.TestCase):

    def setUp(self):
        self.v = GuardianValidator()

    def test_blocks_secret(self):
        messages = [{"role": "user", "content": "minha api_key=sk-ant-abc"}]
        with self.assertRaises(ValidationError):
            self.v.validate_remote_call(messages, "system prompt", "anthropic")

    def test_blocks_financial(self):
        messages = [{"role": "user", "content": "meu CPF é 123.456.789-00"}]
        with self.assertRaises(ValidationError):
            self.v.validate_remote_call(messages, "", "anthropic")

    def test_allows_public(self):
        messages = [{"role": "user", "content": "O que é TriCore?"}]
        # Não deve levantar exceção
        self.v.validate_remote_call(messages, "system", "anthropic")

    def test_allows_local_provider_always(self):
        messages = [{"role": "user", "content": "ANTHROPIC_API_KEY=sk-secret"}]
        # Local nunca bloqueia (dados não saem do PC)
        self.v.validate_remote_call(messages, "", "local")

    def test_personal_in_system_prompt_no_warning(self, capsys=None):
        # System prompt da WIND contém "Claude Code", "Felipe" etc. — não deve gerar falso positivo
        # (personal só é checado em mensagens do usuário, não no system prompt)
        system = "Você é a WIND — sócia técnica do Felipe (REPROTECH). Claude Code e Ghidra são ferramentas."
        messages = [{"role": "user", "content": "O que é TriCore?"}]
        # Não deve levantar exceção
        self.v.validate_remote_call(messages, system, "anthropic")

    def test_personal_in_user_message_warns(self):
        import io, sys as _sys
        # Dados pessoais numa mensagem do usuário devem gerar aviso no stderr
        messages = [{"role": "user", "content": "Cliente João Silva, placa ABC-1234"}]
        captured = io.StringIO()
        orig = _sys.stderr
        _sys.stderr = captured
        try:
            self.v.validate_remote_call(messages, "system prompt limpo", "anthropic")
        finally:
            _sys.stderr = orig
        assert "GUARDIAN AVISO" in captured.getvalue()


if __name__ == "__main__":
    unittest.main(verbosity=2)
