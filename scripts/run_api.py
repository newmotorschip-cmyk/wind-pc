"""
Inicia apenas o servidor HTTP da WIND na porta 8765, sem CLI interativo.
Usado pelo start_wind_tunnel.ps1 e por outros launchers externos.

Uso: python scripts/run_api.py [--port 8765]
"""
from __future__ import annotations

import os
import sys
import time
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.orchestrator import Orchestrator


def main() -> None:
    port = 8765
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        try:
            port = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            pass

    api_key = os.getenv("WIND_API_KEY", "")
    if not api_key:
        print("[WIND] Aviso: WIND_API_KEY não configurada. Qualquer cliente pode acessar a API.", flush=True)

    print(f"[WIND] Iniciando Orchestrator...", flush=True)
    orc = Orchestrator()

    effective_port = orc.start_api(port=port, api_key=api_key)
    url = orc.api_status().get("url", f"http://0.0.0.0:{effective_port}")
    print(f"[WIND] API rodando: {url}", flush=True)
    print("[WIND] Pressione Ctrl+C para encerrar.", flush=True)

    def _shutdown(signum, frame):
        print("\n[WIND] Sinal recebido. Encerrando API...", flush=True)
        orc.stop_api()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
