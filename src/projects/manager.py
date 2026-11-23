"""
ProjectManager — cria, encontra e atualiza ProjectCards.
Implementa fuzzy matching para "continue projeto X" entre sessões.
"""
from __future__ import annotations

import difflib
from typing import Optional

from .project import ProjectCard, ProjectStatus
from .store import ProjectStore


class ProjectManager:
    def __init__(self, store: ProjectStore | None = None) -> None:
        self._store = store or ProjectStore()

    def create(
        self,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> ProjectCard:
        project = ProjectCard(
            name=name,
            description=description,
            tags=tags or [],
        )
        self._store.save(project)
        return project

    def find(self, query: str) -> Optional[ProjectCard]:
        """
        Busca um projeto pelo nome (exato ou fuzzy).
        Retorna o melhor match com score > 0.5; None se não encontrar.
        """
        all_projects = self._store.list_all()
        if not all_projects:
            return None

        q_lower = query.lower().strip()

        # Exact match primeiro
        for p in all_projects:
            if p.name.lower() == q_lower:
                return p

        # Substring match
        candidates = [p for p in all_projects if q_lower in p.name.lower()]
        if candidates:
            return candidates[0]

        # Fuzzy match
        names = [p.name.lower() for p in all_projects]
        matches = difflib.get_close_matches(q_lower, names, n=1, cutoff=0.5)
        if matches:
            for p in all_projects:
                if p.name.lower() == matches[0]:
                    return p

        return None

    def update_next_action(self, project_id: str, action: str) -> Optional[ProjectCard]:
        project = self._store.get(project_id)
        if project:
            project.next_action = action
            self._store.save(project)
        return project

    def add_decision(self, project_id: str, decision: str, context: str = "") -> Optional[ProjectCard]:
        project = self._store.get(project_id)
        if project:
            project.add_decision(decision, context)
            self._store.save(project)
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> Optional[ProjectCard]:
        project = self._store.get(project_id)
        if project:
            project.status = status
            self._store.save(project)
        return project

    def list_active(self) -> list[ProjectCard]:
        return self._store.list_active()

    def list_all(self) -> list[ProjectCard]:
        return self._store.list_all()

    def continuation_context(self, project: ProjectCard) -> str:
        """
        Gera texto de contexto para retomada de sessão do projeto.
        Usado pelo orquestrador para incluir no system prompt.
        """
        lines = [
            f"=== Projeto: {project.name} ===",
            f"Status: {project.status.value}",
        ]
        if project.description:
            lines.append(f"Descrição: {project.description}")
        if project.next_action:
            lines.append(f"Próximo passo: {project.next_action}")
        if project.decisions:
            lines.append("Últimas decisões:")
            for d in project.decisions[-3:]:
                lines.append(f"  - {d['text']}")
        if project.tags:
            lines.append(f"Tags: {', '.join(project.tags)}")
        return "\n".join(lines)
