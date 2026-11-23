"""Testes da Fase 14 — GitHubClient + check_github no ProactiveMonitor."""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ── GitHubRepo ────────────────────────────────────────────────────────────────

class TestGitHubRepo(unittest.TestCase):

    def _make(self, pushed_at="2026-01-01T00:00:00Z", private=False, issues=0):
        from src.integrations.github import GitHubRepo
        return GitHubRepo(
            name="repo",
            full_name="user/repo",
            description="desc",
            private=private,
            pushed_at=pushed_at,
            open_issues=issues,
            html_url="https://github.com/user/repo",
        )

    def test_from_dict(self):
        from src.integrations.github import GitHubRepo
        d = {
            "name": "myrepo",
            "full_name": "user/myrepo",
            "description": "test repo",
            "private": True,
            "pushed_at": "2026-11-01T12:00:00Z",
            "open_issues_count": 3,
            "html_url": "https://github.com/user/myrepo",
        }
        r = GitHubRepo.from_dict(d)
        self.assertEqual(r.name, "myrepo")
        self.assertEqual(r.full_name, "user/myrepo")
        self.assertTrue(r.private)
        self.assertEqual(r.open_issues, 3)

    def test_from_dict_missing_description(self):
        from src.integrations.github import GitHubRepo
        r = GitHubRepo.from_dict({"name": "x", "full_name": "u/x", "description": None})
        self.assertEqual(r.description, "")

    def test_days_since_push_valid(self):
        from src.integrations.github import GitHubRepo
        r = self._make(pushed_at="2026-10-01T00:00:00Z")
        days = r.days_since_push()
        self.assertIsNotNone(days)
        self.assertGreater(days, 0)

    def test_days_since_push_none_when_missing(self):
        from src.integrations.github import GitHubRepo
        r = self._make(pushed_at=None)
        self.assertIsNone(r.days_since_push())

    def test_summary_line_includes_full_name(self):
        r = self._make()
        self.assertIn("user/repo", r.summary_line())

    def test_summary_line_private_lock_icon(self):
        r = self._make(private=True)
        self.assertIn("🔒", r.summary_line())

    def test_summary_line_issues_count(self):
        r = self._make(issues=5)
        self.assertIn("5 issues", r.summary_line())


# ── GitHubIssue ───────────────────────────────────────────────────────────────

class TestGitHubIssue(unittest.TestCase):

    def test_from_dict(self):
        from src.integrations.github import GitHubIssue
        d = {
            "number": 42,
            "title": "Bug crítico",
            "state": "open",
            "html_url": "https://github.com/u/r/issues/42",
            "created_at": "2026-11-01T10:00:00Z",
            "labels": [{"name": "bug"}, {"name": "priority"}],
        }
        issue = GitHubIssue.from_dict(d)
        self.assertEqual(issue.number, 42)
        self.assertEqual(issue.title, "Bug crítico")
        self.assertEqual(issue.labels, ["bug", "priority"])

    def test_summary_line(self):
        from src.integrations.github import GitHubIssue
        issue = GitHubIssue(
            number=7, title="Falha no ECU", state="open",
            html_url="", created_at="", labels=["bug"],
        )
        line = issue.summary_line()
        self.assertIn("#7", line)
        self.assertIn("Falha no ECU", line)
        self.assertIn("bug", line)


# ── GitHubClient — disponibilidade ───────────────────────────────────────────

class TestGitHubClientAvailability(unittest.TestCase):

    def _env_without_token(self):
        return {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}

    def test_unavailable_without_token(self):
        from src.integrations.github import GitHubClient
        with patch.dict(os.environ, self._env_without_token(), clear=True):
            gh = GitHubClient()
            self.assertFalse(gh.is_available())

    def test_available_with_token(self):
        from src.integrations.github import GitHubClient
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_abc123"}):
            gh = GitHubClient()
            self.assertTrue(gh.is_available())

    def test_available_with_explicit_token(self):
        from src.integrations.github import GitHubClient
        gh = GitHubClient(token="explicit_token")
        self.assertTrue(gh.is_available())

    def test_setup_hint_returns_string(self):
        from src.integrations.github import GitHubClient
        hint = GitHubClient.setup_hint()
        self.assertIsInstance(hint, str)
        self.assertIn("GITHUB_TOKEN", hint)


# ── GitHubClient — API calls (mocked) ────────────────────────────────────────

class TestGitHubClientAPI(unittest.TestCase):

    def _mock_response(self, payload):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_me_returns_dict(self):
        from src.integrations.github import GitHubClient
        gh = GitHubClient(token="tok")
        payload = {"login": "felipe", "id": 1, "name": "Felipe"}
        with patch("src.integrations.github.urlopen", return_value=self._mock_response(payload)):
            result = gh.me()
        self.assertEqual(result["login"], "felipe")

    def test_list_repos_returns_list(self):
        from src.integrations.github import GitHubClient
        gh = GitHubClient(token="tok")
        payload = [
            {"name": "wind-pc", "full_name": "felipe/wind-pc", "description": "",
             "private": False, "pushed_at": "2026-11-23T00:00:00Z",
             "open_issues_count": 0, "html_url": "https://github.com/felipe/wind-pc"},
        ]
        with patch("src.integrations.github.urlopen", return_value=self._mock_response(payload)):
            repos = gh.list_repos(limit=10)
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0].name, "wind-pc")

    def test_list_repos_network_error_returns_empty(self):
        from src.integrations.github import GitHubClient
        from urllib.error import URLError
        gh = GitHubClient(token="tok")
        with patch("src.integrations.github.urlopen", side_effect=URLError("network")):
            repos = gh.list_repos()
        self.assertEqual(repos, [])

    def test_list_issues_filters_prs(self):
        from src.integrations.github import GitHubClient
        gh = GitHubClient(token="tok")
        payload = [
            {"number": 1, "title": "Issue real", "state": "open",
             "html_url": "", "created_at": "", "labels": []},
            {"number": 2, "title": "PR", "state": "open",
             "html_url": "", "created_at": "", "labels": [],
             "pull_request": {"url": "..."}},  # deve ser filtrado
        ]
        with patch("src.integrations.github.urlopen", return_value=self._mock_response(payload)):
            issues = gh.list_issues("user/repo")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].number, 1)

    def test_list_prs_returns_list(self):
        from src.integrations.github import GitHubClient
        gh = GitHubClient(token="tok")
        payload = [
            {"number": 5, "title": "Fix ECU", "state": "open",
             "html_url": "", "created_at": "", "labels": []},
        ]
        with patch("src.integrations.github.urlopen", return_value=self._mock_response(payload)):
            prs = gh.list_prs("user/repo")
        self.assertEqual(len(prs), 1)
        self.assertEqual(prs[0].number, 5)

    def test_create_issue_returns_dict(self):
        from src.integrations.github import GitHubClient
        gh = GitHubClient(token="tok")
        payload = {"number": 10, "html_url": "https://github.com/u/r/issues/10", "title": "Novo"}
        with patch("src.integrations.github.urlopen", return_value=self._mock_response(payload)):
            result = gh.create_issue("user/repo", "Novo", "descrição")
        self.assertEqual(result["number"], 10)

    def test_stale_repos_filters_by_age(self):
        from src.integrations.github import GitHubClient
        gh = GitHubClient(token="tok")
        # Um repo com push antigo (simulado via days_since_push mock)
        from src.integrations.github import GitHubRepo
        old_repo = GitHubRepo(
            name="old", full_name="u/old", description="",
            private=False, pushed_at="2020-01-01T00:00:00Z",
            open_issues=0, html_url="",
        )
        new_repo = GitHubRepo(
            name="new", full_name="u/new", description="",
            private=False, pushed_at="2026-11-23T00:00:00Z",
            open_issues=0, html_url="",
        )
        with patch.object(gh, "list_repos", return_value=[old_repo, new_repo]):
            stale = gh.stale_repos(days=30)
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].name, "old")


# ── ProactiveMonitor.check_github ─────────────────────────────────────────────

class TestProactiveMonitorGitHub(unittest.TestCase):

    def test_check_github_unavailable_returns_empty(self):
        from src.scheduler.proactive import ProactiveMonitor
        monitor = ProactiveMonitor()
        env_without = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env_without, clear=True):
            alerts = monitor.check_github()
        self.assertEqual(alerts, [])

    def test_check_github_stale_repos_generate_alerts(self):
        from src.scheduler.proactive import ProactiveMonitor
        from src.integrations.github import GitHubRepo
        monitor = ProactiveMonitor()
        stale_repo = GitHubRepo(
            name="old", full_name="u/old", description="",
            private=False, pushed_at="2020-01-01T00:00:00Z",
            open_issues=0, html_url="",
        )
        with patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}):
            with patch("src.integrations.github.GitHubClient") as MockGH:
                instance = MockGH.return_value
                instance.is_available.return_value = True
                instance.stale_repos.return_value = [stale_repo]
                alerts = monitor.check_github(stale_days=30)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].type, "github_stale")
        self.assertIn("old", alerts[0].message)

    def test_check_github_no_stale_repos_no_alerts(self):
        from src.scheduler.proactive import ProactiveMonitor
        monitor = ProactiveMonitor()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}):
            with patch("src.integrations.github.GitHubClient") as MockGH:
                instance = MockGH.return_value
                instance.is_available.return_value = True
                instance.stale_repos.return_value = []
                alerts = monitor.check_github(stale_days=30)
        self.assertEqual(alerts, [])

    def test_check_github_exception_returns_empty(self):
        from src.scheduler.proactive import ProactiveMonitor
        monitor = ProactiveMonitor()
        with patch.dict(os.environ, {"GITHUB_TOKEN": "tok"}):
            with patch("src.integrations.github.GitHubClient", side_effect=RuntimeError("fail")):
                alerts = monitor.check_github()
        self.assertEqual(alerts, [])

    def test_check_all_includes_github(self):
        from src.scheduler.proactive import ProactiveMonitor
        monitor = ProactiveMonitor()
        with patch.object(monitor, "check_github", return_value=[]) as mock_gh:
            monitor.check_all()
            mock_gh.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
