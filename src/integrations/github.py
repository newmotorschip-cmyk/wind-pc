"""
Integração com GitHub REST API.
Requer: GITHUB_TOKEN (personal access token com scope repo/read:user).
Usa apenas stdlib + requests (já instalado na Fase 9).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlencode


@dataclass
class GitHubRepo:
    name: str
    full_name: str
    description: str
    private: bool
    pushed_at: Optional[str]
    open_issues: int
    html_url: str

    @classmethod
    def from_dict(cls, d: dict) -> "GitHubRepo":
        return cls(
            name=d.get("name", ""),
            full_name=d.get("full_name", ""),
            description=d.get("description") or "",
            private=d.get("private", False),
            pushed_at=d.get("pushed_at"),
            open_issues=d.get("open_issues_count", 0),
            html_url=d.get("html_url", ""),
        )

    def days_since_push(self) -> Optional[int]:
        if not self.pushed_at:
            return None
        try:
            dt = datetime.fromisoformat(self.pushed_at.replace("Z", "+00:00"))
            delta = datetime.now(dt.tzinfo) - dt
            return delta.days
        except (ValueError, TypeError):
            return None

    def summary_line(self) -> str:
        age = self.days_since_push()
        age_str = f" ({age}d sem push)" if age is not None else ""
        priv = " 🔒" if self.private else ""
        issues = f" [{self.open_issues} issues]" if self.open_issues else ""
        return f"{self.full_name}{priv}{issues}{age_str}"


@dataclass
class GitHubIssue:
    number: int
    title: str
    state: str
    html_url: str
    created_at: str
    labels: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "GitHubIssue":
        return cls(
            number=d.get("number", 0),
            title=d.get("title", ""),
            state=d.get("state", ""),
            html_url=d.get("html_url", ""),
            created_at=d.get("created_at", ""),
            labels=[lb["name"] for lb in d.get("labels", [])],
        )

    def summary_line(self) -> str:
        labels_str = f" [{', '.join(self.labels)}]" if self.labels else ""
        return f"#{self.number} {self.title}{labels_str}"


class GitHubClient:
    """
    Cliente da GitHub REST API.
    Requer GITHUB_TOKEN no ambiente — personal access token com scope
    repo (repositórios privados) ou public_repo (somente públicos).
    """

    _BASE = "https://api.github.com"

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token or os.getenv("GITHUB_TOKEN", "")

    def is_available(self) -> bool:
        return bool(self._token)

    # ── internos ──────────────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None) -> dict | list:
        url = f"{self._BASE}{path}"
        if params:
            url += "?" + urlencode(params)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError):
            return {}

    def _post(self, path: str, body: dict) -> dict:
        url = f"{self._BASE}{path}"
        data = json.dumps(body).encode("utf-8")
        headers = {
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = Request(url, data=data, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError):
            return {}

    # ── API pública ───────────────────────────────────────────────────────────

    def me(self) -> dict:
        """Retorna dados do usuário autenticado."""
        result = self._get("/user")
        return result if isinstance(result, dict) else {}

    def list_repos(self, limit: int = 20) -> list[GitHubRepo]:
        """Lista repositórios do usuário autenticado (mais recentemente modificados)."""
        raw = self._get("/user/repos", {
            "sort": "pushed",
            "direction": "desc",
            "per_page": min(limit, 100),
        })
        if not isinstance(raw, list):
            return []
        return [GitHubRepo.from_dict(r) for r in raw[:limit]]

    def list_issues(self, repo: str, state: str = "open", limit: int = 20) -> list[GitHubIssue]:
        """Lista issues de <owner/repo>."""
        raw = self._get(f"/repos/{repo}/issues", {
            "state": state,
            "per_page": min(limit, 100),
        })
        if not isinstance(raw, list):
            return []
        # GitHub retorna PRs junto com issues — filtra pull requests
        return [
            GitHubIssue.from_dict(i) for i in raw[:limit]
            if "pull_request" not in i
        ]

    def list_prs(self, repo: str, state: str = "open", limit: int = 20) -> list[GitHubIssue]:
        """Lista pull requests de <owner/repo>."""
        raw = self._get(f"/repos/{repo}/pulls", {
            "state": state,
            "per_page": min(limit, 100),
        })
        if not isinstance(raw, list):
            return []
        return [GitHubIssue.from_dict(p) for p in raw[:limit]]

    def create_issue(self, repo: str, title: str, body: str = "") -> dict:
        """Cria issue em <owner/repo>. Retorna dict com 'number' e 'html_url'."""
        result = self._post(f"/repos/{repo}/issues", {"title": title, "body": body})
        return result if isinstance(result, dict) else {}

    def stale_repos(self, days: int = 30, limit: int = 50) -> list[GitHubRepo]:
        """Retorna repositórios sem push há mais de `days` dias."""
        repos = self.list_repos(limit=limit)
        return [r for r in repos if (r.days_since_push() or 0) >= days]

    @staticmethod
    def setup_hint() -> str:
        return (
            "Para ativar a integração GitHub:\n"
            "1. github.com → Settings → Developer settings → Personal access tokens\n"
            "2. Gere um token com scope: repo (ou public_repo para só públicos)\n"
            "3. Configure no Windows:\n"
            "   setx GITHUB_TOKEN <seu-token>"
        )
