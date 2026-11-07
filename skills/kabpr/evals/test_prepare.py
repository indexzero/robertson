"""Isolated behavioral tests. No live GitHub requests or approval writes."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("prepare", Path(__file__).parents[1] / "scripts/prepare.py")
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)

MESSAGE = """src/client.py: handle missing tokens

Requests with no token previously failed without an explanation.

The client now reports the missing value:

```python
if not token:
    raise ValueError("Missing token")
return token
```

That check enables callers to correct their configuration.

Closes #7

<!-- metadata.txt

Assisted-by: Test Model, test-agent@1.0"""


def pull():
    return {"number": 34, "html_url": "https://github.com/acme/widgets/pull/34",
            "state": "open", "draft": False, "title": "Old title", "body": "Fixes #7",
            "head": {"sha": "a" * 40, "ref": "feature", "repo": {"full_name": "alice/widgets"}},
            "base": {"sha": "b" * 40, "ref": "main"}}


def snapshot(pr=None):
    value = p.snapshot_of("github.com", "acme/widgets", pr or pull())
    value.update({"settings": {"allow_squash_merge": True, "has_pull_requests": True,
                               "squash_merge_commit_title": "PR_TITLE",
                               "squash_merge_commit_message": "PR_BODY", "default_branch": "main"},
                  "files": [{"filename": "src/client.py", "status": "modified"}],
                  "commits": [{"commit": {"message": "Handle tokens"}}],
                  "diff": "diff --git a/src/client.py b/src/client.py\n+if not token:\n",
                  "checks": {"headRefOid": "a" * 40, "mergeable": "MERGEABLE",
                             "mergeStateStatus": "CLEAN", "reviewDecision": "APPROVED",
                             "statusCheckRollup": []}})
    return value


class FakeGitHub(p.GitHub):
    def __init__(self, pr=None):
        self.pr = pr or pull()
        self.writes = []
        self.after_write = None

    def pull(self, host, repo, number):
        return copy.deepcopy(self.pr)

    def api(self, host, endpoint, *, payload=None, pages=False):
        if payload is not None:
            self.writes.append((host, endpoint, payload))
            self.pr.update(payload)
            if self.after_write:
                self.after_write(self.pr)
            return self.pull(host, "acme/widgets", 34)
        if "?state=open&head=" in endpoint:
            return [copy.deepcopy(self.pr)]
        if endpoint.endswith("/files?per_page=100"):
            return snapshot()["files"]
        if endpoint.endswith("/commits?per_page=100"):
            return snapshot()["commits"]
        if endpoint == "repos/acme/widgets":
            return snapshot()["settings"]
        raise AssertionError(endpoint)


class ResolverTests(unittest.TestCase):
    def local_command(self, args, **kwargs):
        known = {
            ("gh", "repo", "view", "--json", "url"): '{"url":"https://github.com/acme/widgets"}',
            ("git", "symbolic-ref", "--quiet", "--short", "HEAD"): "feature\n",
            ("git", "config", "--get", "branch.feature.remote"): "origin\n",
            ("git", "remote", "get-url", "origin"): "git@github.com:alice/widgets.git\n",
        }
        return known[tuple(args)]

    def test_qualified_targets_work_without_any_checkout(self):
        with patch.object(p, "run", side_effect=AssertionError("Must not inspect local git")):
            for target in ("acme/widgets#34", "https://github.com/acme/widgets/pull/34"):
                self.assertEqual(p.GitHub().resolve(target), ("github.com", "acme/widgets", 34))

    def test_both_numeric_forms_use_current_repository(self):
        with patch.object(p, "run", side_effect=self.local_command):
            for target in ("34", "#34"):
                self.assertEqual(p.GitHub().resolve(target), ("github.com", "acme/widgets", 34))

    def test_current_branch_resolves_fork_head_in_upstream_repository(self):
        with patch.object(p, "run", side_effect=self.local_command):
            self.assertEqual(FakeGitHub().resolve(), ("github.com", "acme/widgets", 34))

    def test_wrong_fork_same_branch_is_not_selected(self):
        github = FakeGitHub()
        github.pr["head"]["repo"]["full_name"] = "bob/widgets"
        with patch.object(p, "run", side_effect=self.local_command), self.assertRaisesRegex(p.Error, "found 0"):
            github.resolve()

    def test_multiple_prs_require_an_explicit_choice(self):
        github = FakeGitHub()
        with patch.object(p, "run", side_effect=self.local_command), patch.object(
                github, "api", return_value=[pull(), {**pull(), "number": 35}]), self.assertRaisesRegex(p.Error, "found 2"):
            github.resolve()

    def test_missing_context_and_detached_head_are_explained(self):
        with patch.object(p, "run", side_effect=p.Error("not a repository")):
            with self.assertRaisesRegex(p.Error, "current repository"):
                p.GitHub().resolve("34")
            with self.assertRaisesRegex(p.Error, "detached HEAD"):
                p.GitHub().resolve(repo="acme/widgets")

    def test_conflicting_explicit_repositories_are_rejected(self):
        with self.assertRaisesRegex(p.Error, "conflicts"):
            p.GitHub().resolve("acme/widgets#34", "other/widgets")

    def test_invalid_selector_never_reaches_shell_or_network(self):
        for target in ("0", "#-1", "$(touch bad)", "owner/repo#34; echo bad"):
            with self.subTest(target=target), self.assertRaises(p.Error):
                p.target_parts(target)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = p.Store(self.temp.name)
        self.github = FakeGitHub()
        self.snapshot = snapshot()

    def proposal(self, approve=False):
        proposal = self.store.propose(self.snapshot, MESSAGE)
        if approve:
            self.store.approve(proposal["run"], proposal["message_sha256"])
        return proposal

    def test_full_prepare_requires_approval_writes_only_title_body_and_resumes(self):
        proposal = self.proposal()
        with self.assertRaisesRegex(p.Error, "No approval"):
            self.store.apply(proposal["run"], self.github)
        self.assertEqual(self.github.writes, [])
        self.assertEqual(self.store.resume(self.snapshot)["state"], "awaiting_approval")
        self.store.approve(proposal["run"], proposal["message_sha256"])
        self.assertEqual(self.store.resume(self.snapshot)["state"], "approved")
        self.assertEqual(self.store.apply(proposal["run"], self.github)["state"], "prepared")
        self.assertEqual(set(self.github.writes[0][2]), {"title", "body"})
        self.assertEqual(self.github.writes[0][1], "repos/acme/widgets/pulls/34")
        backup = p.read_json(Path(self.temp.name) / proposal["run"] / "before.json")
        self.assertEqual(backup["title"], "Old title")
        self.assertEqual(self.store.apply(proposal["run"], self.github)["state"], "already_prepared")
        self.assertEqual(len(self.github.writes), 1)
        self.assertEqual(self.store.resume(snapshot(self.github.pr))["state"], "prepared")

    def test_head_base_or_message_changes_prevent_write(self):
        for change in (lambda pr: pr["head"].update(sha="c" * 40),
                       lambda pr: pr["base"].update(sha="d" * 40),
                       lambda pr: pr["base"].update(ref="release"),
                       lambda pr: pr.update(body="User edited this"),
                       lambda pr: pr.update(state="closed")):
            with self.subTest(change=change):
                github = FakeGitHub()
                proposal = self.proposal(approve=True)
                change(github.pr)
                with self.assertRaisesRegex(p.Error, "changed"):
                    self.store.apply(proposal["run"], github)
                self.assertEqual(github.writes, [])

    def test_other_pr_cannot_reuse_approval(self):
        self.proposal(approve=True)
        another = snapshot()
        another["number"] = 35
        self.assertEqual(self.store.resume(another)["state"], "new")

    def test_edited_proposal_or_wrong_hash_requires_new_approval(self):
        proposal = self.proposal(approve=True)
        with self.assertRaisesRegex(p.Error, "hash does not match"):
            self.store.approve(proposal["run"], "0" * 64)
        (Path(self.temp.name) / proposal["run"] / "message.msg").write_text(MESSAGE.replace("missing", "empty"))
        with self.assertRaisesRegex(p.Error, "proposal changed"):
            self.store.apply(proposal["run"], self.github)
        self.assertEqual(self.github.writes, [])

    def test_lost_write_response_recovers_without_a_second_write(self):
        proposal = self.proposal(approve=True)
        self.github.pr.update(zip(("title", "body"), MESSAGE.split("\n\n", 1)))
        self.assertEqual(self.store.apply(proposal["run"], self.github)["state"], "already_prepared")
        self.assertEqual(self.github.writes, [])

    def test_readback_race_is_reported_without_rollback(self):
        proposal = self.proposal(approve=True)
        self.github.after_write = lambda pr: pr.update(body="Concurrent edit")
        with self.assertRaisesRegex(p.Error, "readback differs"):
            self.store.apply(proposal["run"], self.github)
        self.assertEqual(len(self.github.writes), 1)
        self.assertEqual(self.github.pr["body"], "Concurrent edit")
        self.assertEqual(self.store.events()[-1]["event"], "verify_failed")

    def test_blocked_merge_does_not_prevent_description_preparation(self):
        self.snapshot["draft"] = self.github.pr["draft"] = True
        self.snapshot["settings"]["squash_merge_commit_message"] = "COMMIT_MESSAGES"
        self.snapshot["checks"].update(mergeable="CONFLICTING", mergeStateStatus="DIRTY",
                                       statusCheckRollup=[{"name": "tests", "conclusion": "FAILURE"}])
        self.assertFalse(p.merge_status(self.snapshot)["ready"])
        proposal = self.proposal(approve=True)
        self.store.apply(proposal["run"], self.github)
        self.assertTrue(self.github.pr["draft"])
        self.assertEqual(set(self.github.writes[0][2]), {"title", "body"})
        self.assertIsNone(proposal["prediction"]["message"])

    def test_unknown_settings_and_check_access_never_report_ready(self):
        self.snapshot["settings"] = {"error": "403"}
        self.snapshot["checks"] = {"error": "no access"}
        self.assertFalse(p.merge_status(self.snapshot)["ready"])
        self.assertTrue(p.merge_status(self.snapshot)["unknown"])
        self.proposal()

    def test_closing_references_and_attribution_survive_validation(self):
        self.assertEqual(p.lint(self.snapshot, MESSAGE), [])
        for text in (MESSAGE.replace("Closes #7", ""), MESSAGE + "\n-->",
                     MESSAGE.replace("src/client.py:", "src/other.py:"),
                     MESSAGE.replace("handle missing tokens", "handle missing tokens (#34)")):
            with self.subTest(text=text):
                self.assertTrue(p.lint(self.snapshot, text))

    def test_prediction_deduplicates_coauthors_and_reports_append(self):
        self.snapshot["commits"] = [
            {"commit": {"message": "Co-authored-by: First <a@example.com>"}},
            {"commit": {"message": "Co-authored-by: Second <a@example.com>"}}]
        predicted = p.prediction(self.snapshot, MESSAGE)
        self.assertEqual(predicted["message"].count("<a@example.com>"), 1)
        self.assertIn("First", predicted["message"])
        self.assertTrue(predicted["coauthor_append"])

    def test_inspect_reads_remote_source_and_does_not_mutate(self):
        def command(args, **kwargs):
            return snapshot()["diff"] if args[1:3] == ["pr", "diff"] else json.dumps(snapshot()["checks"])
        with patch.object(p, "run", side_effect=command):
            result = self.github.inspect("github.com", "acme/widgets", 34)
        self.assertIn("diff --git", result["diff"])
        self.assertEqual(self.github.writes, [])

    def test_closed_pr_stops_inspection(self):
        self.github.pr["state"] = "closed"
        with self.assertRaisesRegex(p.Error, "closed"):
            self.github.inspect("github.com", "acme/widgets", 34)

    def test_incomplete_source_lists_are_not_silently_accepted(self):
        self.github.pr["changed_files"] = 3001
        with self.assertRaisesRegex(p.Error, "incomplete file or commit list"):
            self.github.inspect("github.com", "acme/widgets", 34)
    def test_head_race_stops_inspection(self):
        moved = pull()
        moved["head"]["sha"] = "c" * 40
        with patch.object(self.github, "pull", side_effect=[pull(), moved]), patch.object(
                p, "run", side_effect=[snapshot()["diff"], json.dumps(snapshot()["checks"])]), self.assertRaisesRegex(p.Error, "changed during inspection"):
            self.github.inspect("github.com", "acme/widgets", 34)


if __name__ == "__main__":
    unittest.main()
