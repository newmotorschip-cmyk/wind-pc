"""
Orquestrador central da WIND.
Coordena: Guardian → Memória → Router → Memória → Resposta.
Fase 2: integra ProjectManager e MissionEngine.
Fase 3: integra CaseManager (aprendizado por serviço).
Fase 4: integra REPipeline e ArchMatrix (engenharia reversa).
Fase 5: integra CalibrationManager e FlashInterfaces.
Fase 6: integra NotificationManager, WindAPIServer, MorningSummary, TTSEngine.
Fase 7: integra FinanceAnalyzer (somente leitura; dados financeiros nunca ao modelo bruto).
Fase 8: integra DecisionEngine (autonomia A0-A4), NoteManager e Curriculum (aprendizado contínuo).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from .context import ContextManager
from .identity import SYSTEM_PROMPT
from .session import Session
from ..guardian.audit import AuditLog
from ..guardian.validator import GuardianValidator, ValidationError
from ..memory.episodic import EpisodicMemory
from ..memory.semantic import SemanticMemory
from ..memory.session_mem import SessionMemory
from ..memory.store import MemoryStore
from ..router.models import TaskType
from ..router.router import ModelRouter
from ..projects.store import ProjectStore
from ..projects.manager import ProjectManager
from ..missions.queue import MissionQueue
from ..missions.engine import MissionEngine
from ..cases.store import CaseStore
from ..cases.manager import CaseManager
from ..rev_eng.arch_matrix import build_matrix, matrix_report, GHIDRA_PATH
from ..rev_eng.pipeline import REPipeline, IdentifiedArch
from ..rev_eng.repro_native import ReproNativeConnectors
from ..calibration.store import CalibrationStore
from ..calibration.manager import CalibrationManager
from ..firmware.interfaces import FlashInterfaces
from ..notifications.manager import NotificationManager
from ..voice.tts import TTSEngine, get_best_engine
from ..voice.stt import STTStub
from ..finance.analyzer import FinanceAnalyzer
from ..finance.store import FinanceStore
from ..autonomy.decision import DecisionStore
from ..autonomy.level import AutonomyProfile
from ..autonomy.engine import DecisionEngine
from ..learning.notes import NoteStore, NoteManager
from ..learning.curriculum import Curriculum
from ..learning.retrospective import RetrospectiveGenerator


def _infer_task_type(text: str) -> TaskType:
    """Heurística simples para inferir o tipo de tarefa a partir do texto."""
    t = text.lower()
    if any(w in t for w in ("código", "script", "função", "bug", "implementar", "escreva o código")):
        return TaskType.CODING
    if any(w in t for w in ("analise", "diagnose", "por que", "explique em detalhes", "compare")):
        return TaskType.REASONING
    if any(w in t for w in ("resuma", "liste", "classifique", "extraia", "quais são")):
        return TaskType.TRIAGE
    return TaskType.CONVERSATION


class Orchestrator:
    def __init__(self, db_path: Path | None = None, audit_path: Path | None = None) -> None:
        self._ctx = ContextManager()
        self._router = ModelRouter(self._ctx)
        self._store = MemoryStore(**({"path": db_path} if db_path else {}))
        self._episodic = EpisodicMemory(self._store)
        self._semantic = SemanticMemory(self._store)
        self._guardian = GuardianValidator()
        self._audit = AuditLog(**({"path": audit_path} if audit_path else {}))
        self._session = Session()
        self._session_mem = SessionMemory(self._session)

        # Fase 2: Projetos e Missões
        _db = db_path or Path("data/wind.db")
        self._project_store = ProjectStore(_db)
        self._projects = ProjectManager(self._project_store)
        self._mission_queue = MissionQueue(_db)
        self._missions = MissionEngine(self._mission_queue, session_id=self._session.id)

        # Fase 3: Casos de serviço
        self._case_store = CaseStore(_db)
        self._cases = CaseManager(self._case_store)

        # Fase 4: Engenharia reversa
        self._re_pipeline  = REPipeline(work_root=_db.parent / "re_workspace")
        self._repro_native = ReproNativeConnectors()

        # Fase 5: Calibração e firmware
        self._cal_store   = CalibrationStore(_db)
        self._calibration = CalibrationManager(self._cal_store)
        self._flash_ifaces = FlashInterfaces()

        # Fase 6: Notificações, voz e API
        self._notifications = NotificationManager(db_path=_db)
        self._tts: TTSEngine = get_best_engine()
        self._stt = STTStub()
        self._api_server = None  # iniciado sob demanda via /api-start

        # Fase 7: Finanças (somente leitura)
        self._finance_store   = FinanceStore(_db)
        self._finance         = FinanceAnalyzer(store=self._finance_store)

        # Fase 8: Autonomia graduada e aprendizado contínuo
        self._autonomy_profile = AutonomyProfile.load(_db.parent / "autonomy_profile.json")
        self._decision_store   = DecisionStore(_db)
        self._decision_engine  = DecisionEngine(self._decision_store, self._autonomy_profile)
        self._note_store       = NoteStore(_db)
        self._note_manager     = NoteManager(self._note_store)
        self._curriculum       = Curriculum(_db.parent / "curriculum.json")
        self._retrospective    = RetrospectiveGenerator(
            db_path=_db,
            autonomy_engine=self._decision_engine,
            note_manager=self._note_manager,
            curriculum=self._curriculum,
        )

    @property
    def session_id(self) -> str:
        return self._session.id

    @property
    def projects(self) -> ProjectManager:
        return self._projects

    @property
    def missions(self) -> MissionEngine:
        return self._missions

    @property
    def cases(self) -> CaseManager:
        return self._cases

    @property
    def re_pipeline(self) -> REPipeline:
        return self._re_pipeline

    @property
    def repro_native(self) -> ReproNativeConnectors:
        return self._repro_native

    @property
    def calibration(self) -> CalibrationManager:
        return self._calibration

    @property
    def flash_interfaces(self) -> FlashInterfaces:
        return self._flash_ifaces

    @property
    def notifications(self) -> NotificationManager:
        return self._notifications

    @property
    def tts(self) -> TTSEngine:
        return self._tts

    def start_api(self, port: int = 8765, api_key: str = "") -> int:
        """Inicia o servidor HTTP da WIND. Retorna a porta efetiva."""
        from ..api.server import WindAPIServer
        if self._api_server and self._api_server.is_running():
            return self._api_server._server.server_address[1]
        self._api_server = WindAPIServer(port=port, api_key=api_key, orchestrator=self)
        return self._api_server.start()

    def stop_api(self) -> None:
        if self._api_server:
            self._api_server.stop()
            self._api_server = None

    @property
    def finance(self) -> FinanceAnalyzer:
        return self._finance

    @property
    def decision_engine(self) -> DecisionEngine:
        return self._decision_engine

    @property
    def note_manager(self) -> NoteManager:
        return self._note_manager

    @property
    def curriculum(self) -> Curriculum:
        return self._curriculum

    def api_status(self) -> dict:
        if self._api_server and self._api_server.is_running():
            return {"running": True, "url": self._api_server.url}
        return {"running": False, "url": ""}

    def _get_autonomy_context(self, user_input: str) -> Optional[str]:
        """
        Injeta contexto de autonomia e notas validadas quando relevante.
        Nunca expõe dados sensíveis — apenas nível, decisões pendentes e conhecimento validado.
        """
        lower = user_input.lower()
        keywords = ("autonomia", "decisão", "decisao", "aprendi", "nota", "validar",
                    "nível", "nivel", "envelope", "permissão", "permissao")
        try:
            engine_ctx = self._decision_engine.context_for_orchestrator()
            note_ctx   = self._note_manager.context_for_topic(user_input[:80])
            parts = []
            if engine_ctx:
                parts.append(engine_ctx)
            if note_ctx and any(k in lower for k in keywords):
                parts.append(note_ctx)
            return "\n".join(parts) if parts else None
        except Exception:
            return None

    def _get_finance_context(self, user_input: str) -> Optional[str]:
        """
        Detecta perguntas sobre finanças e injeta resumo agregado.
        NUNCA envia dados financeiros brutos — apenas totais e categorias.
        """
        lower = user_input.lower()
        keywords = ("finanças", "financas", "extrato", "saldo", "receita", "despesa",
                    "gasto", "custo mensal", "faturamento", "resultado", "conta", "pagamento",
                    "quanto gastei", "quanto recebi", "quanto tenho")
        if not any(k in lower for k in keywords):
            return None
        try:
            return self._finance.context_for_orchestrator()
        except Exception:
            return None

    def _get_calibration_context(self, user_input: str) -> Optional[str]:
        """Detecta menção a calibração/ECU e injeta contexto relevante."""
        lower = user_input.lower()
        keywords = ("calibra", "mapa", "ecu", "chiptuning", "reprog", "checksum",
                    "injeção", "injecao", "turbo", "boost", "ignição", "ignição",
                    "lambda", "torque", "med17", "edc17", "edc16", "me9")
        if not any(k in lower for k in keywords):
            return None
        # Detectar família mencionada
        for family in self._calibration.families():
            if family.id.lower() in lower or family.series.lower() in lower:
                ctx = self._calibration.context_for_ecu(family.id)
                if ctx:
                    return ctx
        return None

    def _get_case_context(self, user_input: str) -> Optional[str]:
        """Detecta abertura de serviço e injeta casos similares no contexto."""
        lower = user_input.lower()
        keywords = ("serviço", "servico", "defeito", "problema", "queixa", "sintoma",
                    "dtc", "diagnóstico", "diagnose", "falha", "luz acesa")
        if not any(k in lower for k in keywords):
            return None
        similar = self._cases.find_similar(user_input)
        if not similar:
            return None
        return self._cases.similar_context(similar)

    def _get_project_context(self, user_input: str) -> Optional[str]:
        """Detecta menção a projeto e retorna contexto de retomada."""
        lower = user_input.lower()
        keywords = ("continue", "continua", "projeto", "retoma", "resumir projeto")
        if not any(k in lower for k in keywords):
            return None

        # Extrai nome do projeto da mensagem
        for word in lower.split():
            if len(word) > 3 and word not in keywords:
                project = self._projects.find(word)
                if project:
                    return self._projects.continuation_context(project)
        return None

    def process(self, user_input: str, task_type: TaskType | None = None) -> str:
        """
        Processa uma mensagem do Felipe e retorna a resposta da WIND.
        Pipeline: Guardian → Memória → Router → Memória → resposta
        """
        # 1. Adicionar à sessão
        self._session_mem.add_user(user_input)

        # 2. Recuperar contexto semântico relevante
        sem_results = self._semantic.search(user_input, limit=3)
        sem_context = self._semantic.format_results(sem_results)

        # 2b. Detectar contexto de projeto (Fase 2)
        project_context = self._get_project_context(user_input)

        # 2c. Detectar contexto de serviço / casos similares (Fase 3)
        case_context = self._get_case_context(user_input)

        # 2d. Detectar contexto de calibração ECU (Fase 5)
        cal_context = self._get_calibration_context(user_input)

        # 2e. Detectar contexto financeiro (Fase 7) — apenas texto agregado
        fin_context = self._get_finance_context(user_input)

        # 2f. Contexto de autonomia e notas validadas (Fase 8)
        autonomy_context = self._get_autonomy_context(user_input)

        # 3. Montar system prompt com contexto
        system = SYSTEM_PROMPT
        if sem_context:
            system = f"{system}\n\n{sem_context}"
        if project_context:
            system = f"{system}\n\n{project_context}"
        if case_context:
            system = f"{system}\n\n{case_context}"
        if cal_context:
            system = f"{system}\n\n{cal_context}"
        if fin_context:
            system = f"{system}\n\n{fin_context}"
        if autonomy_context:
            system = f"{system}\n\n{autonomy_context}"

        # 4. Montar mensagens para o modelo
        messages = self._session_mem.get_history()

        # 5. Guardian: validar antes de enviar ao modelo remoto
        inferred_type = task_type or _infer_task_type(user_input)
        try:
            # Descobrir qual provider seria usado
            from ..router.models import ROUTING, MODELS
            candidates = ROUTING.get(inferred_type, ["claude-sonnet-5-5"])
            provider = "anthropic"
            for cid in candidates:
                spec = MODELS.get(cid)
                if spec and spec.available():
                    provider = spec.provider
                    break
            self._guardian.validate_remote_call(messages, system, provider, purpose="chat")
        except ValidationError as e:
            self._audit.log_guardian_block(self._session.id, str(e))
            error_msg = f"⚠️  {e}"
            self._session_mem.add_assistant(error_msg)
            return error_msg

        # 6. Chamar o modelo
        try:
            response_text, model_used, cost = self._router.call(
                messages=messages,
                system=system,
                task_type=inferred_type,
            )
        except Exception as e:
            error_msg = f"Erro ao chamar modelo: {e}"
            print(f"[WIND ERROR] {e}", file=sys.stderr)
            self._session_mem.add_assistant(error_msg)
            return error_msg

        # 7. Registrar na sessão e na memória episódica
        self._session_mem.add_assistant(response_text, model=model_used, cost_usd=cost)
        self._episodic.record_interaction(
            user_text=user_input,
            wind_text=response_text,
            session_id=self._session.id,
            model=model_used,
        )

        # 8. Auditoria
        self._audit.log_call(
            session_id=self._session.id,
            model=model_used,
            task_type=inferred_type.value,
            input_tokens=0,  # preenchido pela telemetria futura
            output_tokens=0,
            cost_usd=cost,
        )

        return response_text

    def status(self) -> dict:
        active_missions = self._mission_queue.list_active()
        active_projects = self._projects.list_active()
        return {
            "session_id": self._session.id,
            "messages": len(self._session.messages),
            "session_cost_usd": round(self._session.total_cost(), 5),
            "router": self._router.status(),
            "active_projects": len(active_projects),
            "active_missions": len(active_missions),
            "open_cases": len(self._cases.list_open()),
            "api": self.api_status(),
            "tts": self._tts.name(),
            "notifications": self._notifications.available_channels(),
            "autonomy_level": self._autonomy_profile.current_level.value,
            "pending_decisions": len(self._decision_store.list_pending()),
            "note_stats": self._note_manager.stats(),
        }
