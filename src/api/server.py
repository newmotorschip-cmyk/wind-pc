"""
HTTP REST API da WIND — acesso via iOS Shortcuts ou qualquer cliente HTTP.
Autenticação: header X-API-Key = env WIND_API_KEY.
Uso: WindAPIServer(port=8765, api_key=..., orchestrator=orc).start()
Rotas:
  GET  /status      — health + status da sessão
  GET  /summary     — resumo da manhã
  GET  /cases       — casos em aberto
  GET  /missions    — missões ativas
  GET  /proposals   — propostas de calibração pendentes
  POST /chat        — {"message": "..."} → {"response": "..."}
  POST /notify      — {"text": "..."} → registra notificação
"""
from __future__ import annotations

import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional


class WindRequestHandler(BaseHTTPRequestHandler):
    # Shared state — definido antes de iniciar o servidor
    _orchestrator: Any = None
    _api_key: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _auth(self) -> bool:
        expected = self.__class__._api_key
        if not expected:
            self._send_json({"error": "WIND_API_KEY não configurada. Defina via setx WIND_API_KEY <chave>."}, 503)
            return False
        provided = self.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided, expected):
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    # ── HTTP dispatch ─────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        if not self._auth():
            return
        path = self.path.split("?")[0]
        handlers = {
            "/status":    self._handle_status,
            "/summary":   self._handle_summary,
            "/cases":     self._handle_cases,
            "/missions":  self._handle_missions,
            "/proposals": self._handle_proposals,
        }
        handler = handlers.get(path)
        if handler:
            handler()
        else:
            self._send_json({"error": f"rota '{path}' não encontrada"}, 404)

    def do_POST(self) -> None:
        if not self._auth():
            return
        path = self.path.split("?")[0]
        handlers = {
            "/chat":   self._handle_chat,
            "/notify": self._handle_notify,
        }
        handler = handlers.get(path)
        if handler:
            handler()
        else:
            self._send_json({"error": f"rota '{path}' não encontrada"}, 404)

    # ── Route handlers ────────────────────────────────────────────────────────

    def _handle_status(self) -> None:
        orc = self.__class__._orchestrator
        if orc is None:
            self._send_json({"ok": False, "error": "orquestrador não inicializado"}, 503)
            return
        self._send_json({"ok": True, "status": orc.status()})

    def _handle_summary(self) -> None:
        orc = self.__class__._orchestrator
        if orc is None:
            self._send_json({"error": "orquestrador não inicializado"}, 503)
            return
        from ..routines.morning import MorningSummary
        summary = MorningSummary(orc).generate()
        self._send_json({"summary": summary})

    def _handle_cases(self) -> None:
        orc = self.__class__._orchestrator
        cases = orc.cases.list_open()
        self._send_json({
            "total": len(cases),
            "cases": [
                {"id": c.id[:8], "queixa": c.queixa,
                 "vehicle": f"{c.vehicle.marca} {c.vehicle.modelo}".strip()}
                for c in cases
            ],
        })

    def _handle_missions(self) -> None:
        orc = self.__class__._orchestrator
        missions = orc.missions._queue.list_active()
        self._send_json({
            "total": len(missions),
            "missions": [
                {"id": m.id[:8], "title": m.title, "status": m.status.value,
                 "progress": m.progress}
                for m in missions
            ],
        })

    def _handle_proposals(self) -> None:
        orc = self.__class__._orchestrator
        proposals = orc.calibration.list_pending()
        self._send_json({
            "total": len(proposals),
            "proposals": [
                {"id": p.id[:8], "ecu": p.ecu_family_id,
                 "vehicle": p.vehicle_description,
                 "guardian_level": p.guardian_level,
                 "legal": p.requires_legal_note}
                for p in proposals
            ],
        })

    def _handle_chat(self) -> None:
        orc = self.__class__._orchestrator
        body = self._read_body()
        message = body.get("message", "").strip()
        if not message:
            self._send_json({"error": "campo 'message' obrigatório"}, 400)
            return
        try:
            response = orc.process(message)
            self._send_json({"response": response})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_notify(self) -> None:
        body = self._read_body()
        text = body.get("text", "").strip()
        if not text:
            self._send_json({"error": "campo 'text' obrigatório"}, 400)
            return
        self._send_json({"ok": True, "notified": text})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            return {}

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # silencia logs do servidor HTTP


class WindAPIServer:
    """
    Servidor HTTP da WIND. Roda em thread daemon para não bloquear o processo.
    Exemplo de uso no iOS Shortcuts:
      URL: http://<IP>:8765/chat
      Method: POST
      Headers: X-API-Key: <WIND_API_KEY>
      Body: {"message": "quais casos estão abertos?"}
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        api_key: str = "",
        orchestrator: Any = None,
    ) -> None:
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        WindRequestHandler._api_key = api_key or os.getenv("WIND_API_KEY", "")
        WindRequestHandler._orchestrator = orchestrator

    def start(self) -> int:
        """Inicia em background. Retorna a porta efetiva (útil quando port=0)."""
        self._server = HTTPServer((self._host, self._port), WindRequestHandler)
        effective_port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="WIND-API",
        )
        self._thread.start()
        return effective_port

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    def is_running(self) -> bool:
        return (
            self._server is not None
            and self._thread is not None
            and self._thread.is_alive()
        )

    @property
    def url(self) -> str:
        if self._server:
            return f"http://{self._host}:{self._server.server_address[1]}"
        return ""
