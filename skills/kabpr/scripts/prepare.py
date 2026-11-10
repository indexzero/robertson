#!/usr/bin/env python3
"""Mechanical support for /kabpr prepare. Requires Python 3.10+ and gh."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote, urlparse
import uuid


class Error(Exception):
    pass


def run(args, *, stdin=None, allowed=(0,)):
    result = subprocess.run(args, input=stdin, capture_output=True, text=True)
    if result.returncode not in allowed:
        raise Error(result.stderr.strip() or result.stdout.strip() or
                    f"{args[0]} exited {result.returncode}")
    return result.stdout


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def message(title, body):
    return title + "\n\n" + (body or "").removesuffix("\n")


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def parse_repo(value):
    parts = value.split("/")
    if len(parts) == 2:
        host = os.environ.get("GH_HOST", "github.com")
        repo = value
    elif len(parts) == 3:
        host, repo = parts[0], "/".join(parts[1:])
    else:
        raise Error("Repository must be [HOST/]OWNER/REPO")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise Error("Invalid repository")
    return host.lower(), repo


def repo_from_url(value):
    # Both GitHub web URLs and git remote URLs, including SSH aliases.
    if re.match(r"[^/@]+@[^:]+:", value):
        host, path = value.split("@", 1)[1].split(":", 1)
    else:
        url = urlparse(value)
        host, path = url.hostname, url.path.lstrip("/")
    if not host:
        raise Error("Cannot determine a GitHub repository from the remote URL")
    return parse_repo(host + "/" + path.removesuffix(".git").rstrip("/"))


def target_parts(target):
    if not target:
        return None, None
    if re.fullmatch(r"#?[1-9][0-9]*", target):
        return None, int(target.lstrip("#"))
    match = re.fullmatch(r"([^#\s]+)#([1-9][0-9]*)", target)
    if match:
        return parse_repo(match[1]), int(match[2])
    url = urlparse(target)
    match = re.fullmatch(r"/([^/]+/[^/]+)/pull/([1-9][0-9]*)/?", url.path)
    if url.scheme == "https" and url.hostname and match and not url.username:
        return parse_repo(url.hostname + "/" + match[1]), int(match[2])
    raise Error("Use OWNER/REPO#N, #N, N, a PR URL, or omit the target")


class GitHub:
    def api(self, host, endpoint, *, payload=None, pages=False):
        args = ["gh", "api", "--hostname", host, endpoint]
        if pages:
            args += ["--paginate", "--slurp"]
        if payload is not None:
            args += ["--method", "PATCH", "--input", "-"]
        value = json.loads(run(args, stdin=json.dumps(payload) if payload is not None else None))
        return [item for page in value for item in page] if pages else value

    def resolve(self, target=None, repo=None):
        explicit, number = target_parts(target)
        override = parse_repo(repo) if repo else None
        if explicit and override and explicit != override:
            raise Error("The target repository conflicts with --repo")
        if explicit or override:
            host, name = explicit or override
        else:
            try:
                local = json.loads(run(["gh", "repo", "view", "--json", "url"]))
                host, name = repo_from_url(local["url"])
            except Error as exc:
                raise Error("Cannot resolve the current repository; use OWNER/REPO#N or --repo. " + str(exc)) from exc
        if number is not None:
            return host, name, number
        try:
            branch = run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"]).strip()
        except Error as exc:
            raise Error("No current branch (or detached HEAD); specify a PR") from exc
        remote = run(["git", "config", "--get", f"branch.{branch}.remote"], allowed=(0, 1)).strip()
        if not remote or remote == ".":
            remote = run(["git", "config", "--get", "remote.pushDefault"], allowed=(0, 1)).strip() or "origin"
        head_host, head_repo = repo_from_url(run(["git", "remote", "get-url", remote]).strip())
        if head_host != host:
            raise Error("The branch remote and target use different hosts; specify the PR")
        owner = head_repo.split("/")[0]
        endpoint = f"repos/{name}/pulls?state=open&head={quote(owner + ':' + branch, safe='')}&per_page=100"
        matches = [pr for pr in self.api(host, endpoint, pages=True)
                   if (pr["head"].get("repo") or {}).get("full_name", "").lower() == head_repo.lower()
                   and pr["head"]["ref"] == branch]
        if len(matches) != 1:
            candidates = ", ".join(pr["html_url"] for pr in matches)
            raise Error(f"Expected one open PR for {head_repo}:{branch}; found {len(matches)}. " +
                        ("Choose one: " + candidates if matches else "Specify a PR or open one separately."))
        return host, name, matches[0]["number"]

    def pull(self, host, repo, number):
        return self.api(host, f"repos/{repo}/pulls/{number}")

    def inspect(self, host, repo, number):
        pr = self.pull(host, repo, number)
        if pr["state"] != "open":
            raise Error(f"{repo}#{number} is {'merged' if pr.get('merged') else pr['state']}; no preparation needed")
        snapshot = snapshot_of(host, repo, pr)
        try:
            settings = self.api(host, f"repos/{repo}")
            snapshot["settings"] = {key: settings.get(key) for key in (
                "allow_squash_merge", "has_pull_requests", "squash_merge_commit_title",
                "squash_merge_commit_message", "default_branch")}
        except Error as exc:
            snapshot["settings"] = {"error": str(exc)}
        snapshot["files"] = self.api(host, f"repos/{repo}/pulls/{number}/files?per_page=100", pages=True)
        snapshot["commits"] = self.api(host, f"repos/{repo}/pulls/{number}/commits?per_page=100", pages=True)
        if len(snapshot["files"]) != pr.get("changed_files", len(snapshot["files"])) or len(snapshot["commits"]) != pr.get("commits", len(snapshot["commits"])):
            raise Error("GitHub returned an incomplete file or commit list; inspect this large PR manually")
        ref = host + "/" + repo
        snapshot["diff"] = run(["gh", "pr", "diff", str(number), "-R", ref])
        fields = "headRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,closingIssuesReferences"
        try:
            checks = json.loads(run(["gh", "pr", "view", str(number), "-R", ref, "--json", fields]))
        except Error as exc:
            checks = {"error": str(exc)}
        if checks.get("headRefOid", snapshot["head"]) != snapshot["head"]:
            raise Error("The PR head changed during inspection; inspect it again")
        snapshot["checks"] = checks
        final = snapshot_of(host, repo, self.pull(host, repo, number))
        if identity(final) != identity(snapshot) or current_message(final) != current_message(snapshot) or final["state"] != "open":
            raise Error("The PR changed during inspection; inspect it again")
        snapshot["merge_status"] = merge_status(snapshot)
        return snapshot


def snapshot_of(host, repo, pr):
    return {"schema": 1, "host": host, "repo": repo, "number": pr["number"],
            "url": pr["html_url"], "state": pr["state"], "draft": pr["draft"],
            "title": pr["title"], "body": pr.get("body") or "",
            "head": pr["head"]["sha"], "head_ref": pr["head"]["ref"],
            "head_repo": (pr["head"].get("repo") or {}).get("full_name"),
            "base": pr["base"]["sha"], "base_ref": pr["base"]["ref"]}


def identity(snapshot):
    return {key: snapshot[key] for key in (
        "host", "repo", "number", "head", "head_ref", "head_repo", "base", "base_ref")}


def current_message(snapshot):
    return message(snapshot["title"], snapshot["body"])


def merge_status(snapshot):
    blockers, unknown = [], []
    if snapshot["draft"]:
        blockers.append("PR is a draft")
    settings = snapshot.get("settings", {})
    for key, wanted in {"allow_squash_merge": True, "has_pull_requests": True,
                        "squash_merge_commit_title": "PR_TITLE",
                        "squash_merge_commit_message": "PR_BODY"}.items():
        if settings.get(key) is None:
            unknown.append(f"Repository setting {key} is unavailable")
        elif settings[key] != wanted:
            blockers.append(f"{key} is {settings[key]!r}; expected {wanted!r}")
    checks = snapshot.get("checks", {})
    state = checks.get("mergeStateStatus", "UNKNOWN")
    if checks.get("mergeable") == "CONFLICTING":
        blockers.append("PR has merge conflicts")
    elif checks.get("mergeable") != "MERGEABLE":
        unknown.append("Mergeability is unknown")
    if state == "UNKNOWN":
        unknown.append("GitHub merge status is unknown")
    elif state != "CLEAN":
        blockers.append(f"GitHub merge status is {state}")
    if checks.get("reviewDecision") in ("REVIEW_REQUIRED", "CHANGES_REQUESTED"):
        blockers.append("Review: " + checks["reviewDecision"])
    rollup = checks.get("statusCheckRollup") or []
    for check in rollup:
        status = check.get("conclusion") or check.get("state") or check.get("status")
        if status not in ("SUCCESS", "NEUTRAL", "SKIPPED"):
            blockers.append(f"Check {check.get('name') or check.get('context')}: {status}")
    return {"ready": not blockers and not unknown, "blockers": blockers,
            "unknown": unknown, "checks_reported": len(rollup)}


def closing_refs(text, repo):
    pattern = r"\b(?:close[sd]?|fix(?:es|ed)?|resolve[sd]?)\s+((?:[\w.-]+/[\w.-]+)?#\d+|https://[^\s/]+/[^\s/]+/[^\s/]+/issues/\d+)"
    refs = set()
    for ref in re.findall(pattern, text, re.IGNORECASE):
        if ref.startswith("https://"):
            url = urlparse(ref)
            path = url.path.split("/")
            ref = "/".join(path[1:3]) + "#" + path[-1]
        refs.add((repo + ref if ref.startswith("#") else ref).lower())
    return refs


def lint(snapshot, text):
    errors = []
    if "\r" in text or "\x00" in text:
        errors.append("Use UTF-8 text with LF line endings")
    title, separator, body = text.partition("\n\n")
    if not separator or "\n" in title or not body.strip():
        return ["Use <title>, one blank line, then <body>"]
    subject = re.fullmatch(r"([^\s:]+): ([a-z].*)", title)
    paths = {f["filename"] for f in snapshot["files"] if f["status"] != "removed"}
    if not subject or subject[1] not in paths:
        errors.append("Subject must name an exact changed file, then ': ' and a lowercase verb")
    if title.endswith(".") or re.search(r"\(#\d+\)", title):
        errors.append("Subject must have no final period or PR-number suffix")
    for index, line in enumerate(text.splitlines(), 1):
        if len(line) > 72:
            errors.append(f"Line {index} exceeds 72 columns")
        if line != line.rstrip():
            errors.append(f"Line {index} has trailing whitespace")
    blocks = re.findall(r"^```[^\n]*\n(.*?)^```[ \t]*$", body, re.MULTILINE | re.DOTALL)
    if len(blocks) != 1 or not 3 <= len(blocks[0].splitlines()) <= 10:
        errors.append("Include one fenced block of 3 to 10 source or usage lines")
    if body.lstrip().startswith("```"):
        errors.append("Open with the problem paragraph")
    outside = re.sub(r"^```[^\n]*\n.*?^```[ \t]*$", "", body, flags=re.MULTILINE | re.DOTALL)
    if any(line.startswith((" ", "\t")) for line in outside.splitlines()):
        errors.append("Do not indent prose outside the code fence")
    after_block = re.split(r"^```[ \t]*$", body, flags=re.MULTILINE)[-1]
    if not re.search(r"\bThat\s+\w+(?:\s+\w+){0,4}\s+(?:enables|allows|unblocks)\b", after_block):
        errors.append("Include the house-style value sentence after the code block")
    expected = closing_refs(snapshot["body"], snapshot["repo"])
    for issue in snapshot.get("checks", {}).get("closingIssuesReferences", []):
        if issue.get("url"):
            expected |= closing_refs("Closes " + issue["url"], snapshot["repo"])
    missing = expected - closing_refs(body, snapshot["repo"])
    if missing:
        errors.append("Preserve closing references: " + ", ".join(sorted(missing)))
    if not re.search(r"\n<!-- metadata\.txt\n\nAssisted-by: [^\n]+\Z", body):
        errors.append("End with the open metadata.txt comment and current-agent Assisted-by trailer")
    return errors


def prediction(snapshot, text):
    title, body = text.split("\n\n", 1)
    settings = snapshot["settings"]
    if settings.get("squash_merge_commit_title") != "PR_TITLE" or settings.get("squash_merge_commit_message") != "PR_BODY":
        return {"message": None, "differences": ["Repository defaults do not use the PR title and body"]}
    trailers, seen = [], set()
    for commit in snapshot["commits"]:
        for line in commit["commit"]["message"].splitlines():
            match = re.fullmatch(r"Co-authored-by:\s*(.*?)\s*<([^>]+)>", line, re.IGNORECASE)
            if match and match[2].lower() not in seen:
                seen.add(match[2].lower())
                trailers.append(line)
    differences = [f"GitHub adds (#{snapshot['number']}) to the subject"]
    predicted = message(title + f" (#{snapshot['number']})", body)
    if trailers:
        differences.append("GitHub may append co-author trailers after Assisted-by; inspect seal before claiming exact attribution")
        predicted += "\n\n---------\n\n" + "\n".join(trailers)
    return {"message": predicted, "differences": differences, "coauthor_append": bool(trailers)}


class Store:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("KABPR_STATE_DIR") or
                         Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "kabpr")
        self.ledger = self.root / "ledger.jsonl"

    def events(self):
        if not self.ledger.exists():
            return []
        return [json.loads(line) for line in self.ledger.read_text().splitlines() if line.strip()]

    def event(self, event, proposal, **extra):
        self.root.mkdir(parents=True, exist_ok=True)
        value = {"event": event, "at": datetime.now(timezone.utc).isoformat(),
                 "run": proposal["run"], **proposal["identity"],
                 "message_sha256": proposal["message_sha256"], **extra}
        with self.ledger.open("a") as output:
            output.write(json.dumps(value) + "\n")
            output.flush()
            os.fsync(output.fileno())

    def load(self, run_id):
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise Error("Use the proposal ID printed by propose or inspect")
        directory = self.root / run_id
        proposal = read_json(directory / "proposal.json")
        text = (directory / "message.msg").read_bytes().decode("utf-8").removesuffix("\n")
        snapshot = read_json(directory / "snapshot.json")
        if proposal["run"] != run_id or digest(text) != proposal["message_sha256"] or identity(snapshot) != proposal["identity"]:
            raise Error("Saved proposal changed; create a new proposal and obtain approval")
        if digest(current_message(snapshot)) != proposal["original_sha256"]:
            raise Error("Saved snapshot changed; inspect again")
        return proposal, snapshot, text

    def approved(self, proposal):
        return any(e["event"] == "approved" and e["run"] == proposal["run"] and
                   e["message_sha256"] == proposal["message_sha256"] and
                   all(e.get(k) == v for k, v in proposal["identity"].items()) for e in self.events())

    def resume(self, snapshot):
        for event in reversed(self.events()):
            if event["event"] != "drafted" or any(event.get(k) != v for k, v in identity(snapshot).items()):
                continue
            proposal, _, text = self.load(event["run"])
            approved = self.approved(proposal)
            current = digest(current_message(snapshot))
            if approved and current == proposal["message_sha256"]:
                return {"state": "prepared", "run": proposal["run"]}
            if current == proposal["original_sha256"]:
                return {"state": "approved" if approved else "awaiting_approval", "run": proposal["run"]}
        return {"state": "new"}

    def propose(self, snapshot, text):
        errors = lint(snapshot, text)
        if errors:
            raise Error("\n".join(errors))
        proposal = {"run": uuid.uuid4().hex, "identity": identity(snapshot),
                    "message_sha256": digest(text), "original_sha256": digest(current_message(snapshot)),
                    "prediction": prediction(snapshot, text)}
        directory = self.root / proposal["run"]
        directory.mkdir(parents=True)
        write_json(directory / "snapshot.json", snapshot)
        (directory / "message.msg").write_text(text + "\n")
        write_json(directory / "proposal.json", proposal)
        self.event("drafted", proposal)
        return {**proposal, "message_file": str(directory / "message.msg"), "message": text}

    def approve(self, run_id, sha):
        proposal, _, _ = self.load(run_id)
        if sha != proposal["message_sha256"]:
            raise Error("Approval hash does not match the displayed message")
        if not self.approved(proposal):
            self.event("approved", proposal)
        return {"state": "approved", "run": run_id}

    def apply(self, run_id, github):
        proposal, snapshot, text = self.load(run_id)
        if not self.approved(proposal):
            raise Error("No approval recorded for this proposal")
        host, repo, number = (snapshot[k] for k in ("host", "repo", "number"))
        live = snapshot_of(host, repo, github.pull(host, repo, number))
        if live["state"] != "open" or identity(live) != proposal["identity"]:
            raise Error("PR state, head, or base changed; inspect again before applying")
        if current_message(live) == text:
            self.event("applied", proposal, recovered=True)
            return {"state": "already_prepared", "url": live["url"]}
        if digest(current_message(live)) != proposal["original_sha256"]:
            raise Error("PR title or description changed; inspect again before applying")
        backup = self.root / run_id / "before.json"
        if not backup.exists():
            write_json(backup, live)
        title, body = text.split("\n\n", 1)
        self.event("applying", proposal)
        github.api(host, f"repos/{repo}/pulls/{number}", payload={"title": title, "body": body})
        verified = snapshot_of(host, repo, github.pull(host, repo, number))
        if verified["state"] != "open" or identity(verified) != proposal["identity"] or current_message(verified) != text:
            self.event("verify_failed", proposal)
            raise Error("PR changed during the write or readback differs. Inspect it; do not overwrite or roll back automatically")
        self.event("applied", proposal)
        return {"state": "prepared", "url": verified["url"], "next": "inspect again for current merge status"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", help="Override agent-neutral state storage (also KABPR_STATE_DIR)")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Read one PR; no GitHub writes")
    inspect.add_argument("target", nargs="?")
    inspect.add_argument("-R", "--repo")
    inspect.add_argument("--out", required=True, help="Write the full pinned snapshot here")
    for name in ("lint", "propose"):
        sub = commands.add_parser(name)
        sub.add_argument("snapshot")
        sub.add_argument("message", help="UTF-8 file: title, blank line, body")
    approve = commands.add_parser("approve", help="Record an explicit user approval; no GitHub writes")
    approve.add_argument("run")
    approve.add_argument("--sha256", required=True)
    apply = commands.add_parser("apply", help="Apply an already approved proposal to its pinned PR")
    apply.add_argument("run")
    args = parser.parse_args()
    try:
        store, github = Store(args.state_dir), GitHub()
        if args.command == "inspect":
            snapshot = github.inspect(*github.resolve(args.target, args.repo))
            write_json(args.out, snapshot)
            result = {"target": snapshot["url"], "snapshot": args.out,
                      "preparation": store.resume(snapshot), "merge_status": snapshot["merge_status"]}
        elif args.command in ("lint", "propose"):
            snapshot = read_json(args.snapshot)
            text = Path(args.message).read_bytes().decode("utf-8").removesuffix("\n")
            if args.command == "lint":
                errors = lint(snapshot, text)
                if errors:
                    raise Error("\n".join(errors))
                result = {"valid": True, "source_verification": "agent must verify snippet and claims against the pinned diff"}
            else:
                result = store.propose(snapshot, text)
        elif args.command == "approve":
            result = store.approve(args.run, args.sha256)
        else:
            result = store.apply(args.run, github)
        print(json.dumps(result, indent=2))
    except (Error, OSError, ValueError, KeyError) as exc:
        print(f"kabpr: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
