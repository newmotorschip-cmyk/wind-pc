"""
Framework de avaliação de compreensão em Português do Brasil.
Conjunto de perguntas: a ser criado pelo Felipe na Fase 1.

Uso:
  python tests/eval/portuguese_eval.py --questions tests/eval/ptbr_questions.json
"""
from __future__ import annotations

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


SCHEMA = {
    "description": "Conjunto de perguntas para avaliação de Português BR",
    "example": [
        {
            "id": "ptbr-001",
            "question": "O que é o protocolo UDS e para que é usado em diagnóstico automotivo?",
            "expected_keywords": ["diagnóstico", "ECU", "ISO 14229"],
            "domain": "firmware",
            "difficulty": "medium",
            "evaluator_notes": "Resposta correta deve mencionar ISO 14229 e aplicação em comunicação com ECUs",
        }
    ],
}


def run_eval(questions_path: str, output_path: str | None = None) -> dict:
    """
    Executa a avaliação com as perguntas carregadas.
    Requer ANTHROPIC_API_KEY configurada.
    """
    from src.core.orchestrator import Orchestrator
    from src.router.models import TaskType

    with open(questions_path, encoding="utf-8") as f:
        questions = json.load(f)

    orc = Orchestrator()
    results = []
    total = len(questions)

    print(f"\nAvaliação PT-BR — {total} perguntas\n{'='*40}")
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{total}] {q['id']}: {q['question'][:60]}...")
        t0 = time.time()
        response = orc.process(q["question"], task_type=TaskType.CONVERSATION)
        elapsed = time.time() - t0

        # Verificação automática de keywords (heurística; avaliação humana é a definitiva)
        keywords_found = [
            kw for kw in q.get("expected_keywords", [])
            if kw.lower() in response.lower()
        ]
        keyword_score = len(keywords_found) / max(len(q.get("expected_keywords", [1])), 1)

        result = {
            "id": q["id"],
            "question": q["question"],
            "response": response,
            "elapsed_s": round(elapsed, 2),
            "keywords_found": keywords_found,
            "keyword_score": round(keyword_score, 2),
            "human_score": None,  # a preencher manualmente
            "notes": "",
        }
        results.append(result)
        print(f"   Score keywords: {keyword_score:.0%} | {elapsed:.1f}s")

    summary = {
        "total": total,
        "avg_keyword_score": sum(r["keyword_score"] for r in results) / total,
        "results": results,
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\nResultados salvos em: {output_path}")

    print(f"\nScore médio (keywords): {summary['avg_keyword_score']:.0%}")
    print("Avaliação humana pendente — preencher 'human_score' de 1 a 5 no JSON de resultados.")
    return summary


def print_schema():
    print("Schema esperado para o arquivo de perguntas:")
    print(json.dumps(SCHEMA, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avaliação PT-BR da WIND")
    parser.add_argument("--questions", help="Arquivo JSON com as perguntas")
    parser.add_argument("--output", help="Arquivo JSON para salvar resultados")
    parser.add_argument("--schema", action="store_true", help="Mostrar schema esperado do JSON")
    args = parser.parse_args()

    if args.schema:
        print_schema()
    elif args.questions:
        run_eval(args.questions, args.output)
    else:
        print("Use --questions <arquivo.json> para rodar a avaliação.")
        print("Use --schema para ver o formato esperado.")
