#!/usr/bin/env bash
#
# audit-worktree.sh — gather deletion evidence for ONE worktree, as JSON.
#
# This script decides nothing. It answers the mechanical questions so the
# judgment (safe / blocked) is made once, by a reader, against a compact
# record — instead of by re-running a dozen git commands per worktree.
#
# Usage: audit-worktree.sh <worktree-path> [--base <ref>] [--primary <path>]
#   --base     ref to prove content against       (default: origin/main)
#   --primary  the retained checkout to compare   (default: the is_main worktree)
#              untracked/ignored files against
#
# Output: one JSON object on stdout. Never prints file CONTENTS — untracked and
# ignored files are hashed, never echoed, so a credential can be reported by
# name without leaking its value.

set -euo pipefail

WT="" BASE="origin/main" PRIMARY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)    BASE="$2"; shift 2 ;;
    --primary) PRIMARY="$2"; shift 2 ;;
    -h|--help) sed -n '3,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)         WT="$1"; shift ;;
  esac
done

[[ -n "$WT" && -d "$WT" ]] || { echo "audit-worktree: need a worktree path" >&2; exit 1; }
command -v jq >/dev/null || { echo "audit-worktree: jq not found" >&2; exit 1; }

WT="$(cd "$WT" && pwd)"
if [[ -z "$PRIMARY" ]]; then
  PRIMARY="$(git -C "$WT" worktree list --porcelain | awk '/^worktree /{print $2; exit}')"
fi

BRANCH="$(git -C "$WT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo DETACHED)"
HEAD_SHA="$(git -C "$WT" rev-parse --short HEAD)"

# ---------------------------------------------------------------- content ----
# Proof 1: ancestor. The cheapest and strongest — `wt list` shows this as ⊂.
ANCESTOR=false
git -C "$WT" merge-base --is-ancestor HEAD "$BASE" 2>/dev/null && ANCESTOR=true

# Proof 2: patch equivalence. `-` means an equivalent commit exists upstream;
# `+` is branch-only content and is the thing that blocks deletion.
CHERRY_PLUS=0 CHERRY_MINUS=0 PLUS_SUBJECTS="[]"
if [[ "$BRANCH" != "DETACHED" ]]; then
  CHERRY="$(git -C "$WT" cherry "$BASE" HEAD 2>/dev/null || true)"
  if [[ -n "$CHERRY" ]]; then
    CHERRY_PLUS=$(grep -c '^+' <<<"$CHERRY" || true)
    CHERRY_MINUS=$(grep -c '^-' <<<"$CHERRY" || true)
    PLUS_SUBJECTS="$(grep '^+' <<<"$CHERRY" | awk '{print $2}' | while read -r sha; do
      git -C "$WT" log -1 --format='%h %s' "$sha"
    done | jq -R . | jq -s .)"
  fi
fi

# Proof 3: squash merge. The commit is not an ancestor but the content landed.
# A merged PR only counts when its merge commit is reachable from the base.
PR_JSON="null"
if [[ "$BRANCH" != "DETACHED" ]] && command -v gh >/dev/null; then
  PR_RAW="$(gh pr list --head "$BRANCH" --state all --limit 1 \
              --json number,state,mergeCommit,title 2>/dev/null || echo '[]')"
  if [[ "$(jq 'length' <<<"$PR_RAW")" -gt 0 ]]; then
    PR_NUM="$(jq -r '.[0].number' <<<"$PR_RAW")"
    PR_STATE="$(jq -r '.[0].state' <<<"$PR_RAW")"
    PR_MERGE="$(jq -r '.[0].mergeCommit.oid // ""' <<<"$PR_RAW")"
    PR_TITLE="$(jq -r '.[0].title' <<<"$PR_RAW")"
    REACHABLE=false
    [[ -n "$PR_MERGE" ]] && git -C "$WT" merge-base --is-ancestor "$PR_MERGE" "$BASE" 2>/dev/null && REACHABLE=true
    PR_JSON="$(jq -n --argjson n "$PR_NUM" --arg s "$PR_STATE" --arg m "${PR_MERGE:0:8}" \
                     --arg t "$PR_TITLE" --argjson r "$REACHABLE" \
                     '{number:$n, state:$s, merge_commit:$m, merge_reachable:$r, title:$t}')"
  fi
fi

# Uncommitted tracked edits are content no commit proof covers. Deletions are
# the exception: a file main still has is not lost by deleting this directory.
declare -a MOD=() ADD=() DEL=()
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  code="${line:0:2}"; path="${line:3}"
  case "$code" in
    *D*) DEL+=("$path") ;;
    *A*) ADD+=("$path") ;;
    *)   MOD+=("$path") ;;
  esac
done < <(git -C "$WT" status --porcelain -uno 2>/dev/null || true)

arr() { if [[ ${#@} -eq 0 ]]; then echo '[]'; else printf '%s\n' "$@" | jq -R . | jq -s .; fi; }

# ------------------------------------------------------------- filesystem ----
# The question for every local file is one thing: does an identical copy
# survive somewhere else? Same relative path in the primary checkout, same
# hash. Filename alone proves nothing.
sha_of() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; }
size_of() {
  if [[ -d "$1" ]]; then echo $(( $(du -sk "$1" 2>/dev/null | awk '{print $1}') * 1024 ))
  else stat -f %z "$1" 2>/dev/null || stat -c %s "$1" 2>/dev/null || echo 0; fi
}

# Three honest answers, not two. A file can be PROVEN safe by hash. A
# directory that also exists in the retained checkout is bootstrap material
# (vendored deps, re-fetchable raw sources) — strong evidence, not proof, so
# it is labelled differently rather than silently promoted to "identical".
survival() { # $1 = repo-relative path -> "<state>\t<twin>"
  local rel="$1" twin="$PRIMARY/$1"
  if [[ -f "$WT/$rel" && -f "$twin" ]]; then
    if [[ "$(sha_of "$WT/$rel")" == "$(sha_of "$twin")" ]]; then
      printf 'identical\t%s' "$twin"; return 0
    fi
  elif [[ -d "$WT/$rel" && -d "$twin" ]]; then
    printf 'dir_present\t%s' "$twin"; return 0
  fi
  printf 'none\t'
}

REGENERABLE_RE='(^|/)(node_modules|dist|dist-canvas|build|coverage|\.turbo|\.cache|\.vite|test-results|playwright-report|\.playwright|pnpm-store)(/|$)|\.tsbuildinfo$|\.last-run\.json$'
CREDENTIAL_RE='(accesskey|secret|credential|token|\.env|\.pem$|\.p12$|id_rsa|\.netrc)'

REGEN_COUNT=0
TSV="$(mktemp)"; trap 'rm -f "$TSV"' EXIT

# One status pass, not two. Directory-collapsing modes are deliberate: an
# untracked `sslop/` is one decision, not four thousand, and walking into
# ignored dependency trees is what made this slow.
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  kind="${line:0:2}"; rel="${line:3}"
  rel="${rel%\"}"; rel="${rel#\"}"; rel="${rel%/}"
  [[ -z "$rel" ]] && continue

  if [[ "$kind" == '!!' && "$rel" =~ $REGENERABLE_RE ]]; then
    REGEN_COUNT=$((REGEN_COUNT + 1)); continue
  fi

  IFS=$'\t' read -r state twin < <(survival "$rel") || true

  # A same-named UNTRACKED directory proves nothing. Ignored dirs are vendored
  # or re-fetchable, so a name match there is real evidence; an untracked dir
  # is your own new work, and `drafts/03/` existing in both checkouts says
  # nothing about the draft inside it. Demote to "none" so it stays counted.
  if [[ "$kind" == '??' && "$state" == dir_present ]]; then state=none twin=""; fi

  # Size only what a human may have to rescue. A hash-identical file is proven
  # safe and needs no size. A same-named DIRECTORY is not proof — `.tmp` exists
  # in most checkouts and holds different things in each — so carry both sizes
  # and let the reader see whether they plausibly hold the same bytes.
  bytes=0 twin_bytes=0
  case "$state" in
    none)       bytes="$(size_of "$WT/$rel")" ;;
    dir_present) bytes="$(size_of "$WT/$rel")"; twin_bytes="$(size_of "$twin")" ;;
  esac
  cred=false; [[ "$rel" =~ $CREDENTIAL_RE ]] && cred=true

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$kind" "$rel" "$bytes" "$state" "${twin:-}" "$cred" "$twin_bytes" >>"$TSV"
done < <(git -C "$WT" status --porcelain --ignored=traditional 2>/dev/null || true)

ENTRIES="$(jq -R -s 'split("\n") | map(select(length > 0)) | map(split("\t")) | map({
  kind: .[0], path: .[1], bytes: (.[2] | tonumber), survival: .[3],
  twin: (if .[4] == "" then null else .[4] end),
  credential: (.[5] == "true"), twin_bytes: (.[6] | tonumber)
} | . + (if .survival == "dir_present"
         then {size_ratio: (if .twin_bytes == 0 then null
                            else ((.bytes / .twin_bytes) * 100 | round / 100) end)}
         else {} end))' <"$TSV")"

UNTRACKED="$(jq '[.[] | select(.kind == "??") | del(.kind, .credential)]' <<<"$ENTRIES")"
IGNORED_UNIQUE="$(jq '[.[] | select(.kind == "!!" and .survival == "none")
                        | {path, bytes}]' <<<"$ENTRIES")"
PROPAGATED="$(jq '[.[] | select(.kind == "!!" and .survival == "identical") | .path]' <<<"$ENTRIES")"
BOOTSTRAP="$(jq '[.[] | select(.survival == "dir_present")
                   | {path, bytes, twin_bytes, size_ratio}]' <<<"$ENTRIES")"
CRED="$(jq '[.[] | select(.credential) | .path]' <<<"$ENTRIES")"

# ------------------------------------------------------------------ emit ----
jq -n \
  --arg branch "$BRANCH" --arg path "$WT" --arg head "$HEAD_SHA" --arg base "$BASE" \
  --argjson ancestor "$ANCESTOR" \
  --argjson cplus "$CHERRY_PLUS" --argjson cminus "$CHERRY_MINUS" \
  --argjson plus_subjects "$PLUS_SUBJECTS" \
  --argjson pr "$PR_JSON" \
  --argjson mod "$(arr ${MOD[@]+"${MOD[@]}"})" \
  --argjson add "$(arr ${ADD[@]+"${ADD[@]}"})" \
  --argjson del "$(arr ${DEL[@]+"${DEL[@]}"})" \
  --argjson untracked "$UNTRACKED" \
  --argjson ignored_unique "$IGNORED_UNIQUE" \
  --argjson propagated "$PROPAGATED" \
  --argjson bootstrap "$BOOTSTRAP" \
  --argjson regen "$REGEN_COUNT" \
  --argjson cred "$CRED" \
'{
  branch: $branch, path: $path, head: $head, base: $base,
  content: {
    ancestor: $ancestor,
    cherry: { branch_only: $cplus, equivalent_upstream: $cminus, branch_only_commits: $plus_subjects },
    pr: $pr,
    uncommitted_tracked: { modified: $mod, added: $add, deleted: $del }
  },
  filesystem: {
    untracked: $untracked,
    ignored_unique: $ignored_unique,
    ignored_propagated_identical: $propagated,
    bootstrap_dirs_present_in_primary: $bootstrap,
    ignored_regenerable_entries: $regen,
    credential_candidates: $cred
  },
  signals: {
    content_proven:
      ($ancestor
       or ($cplus == 0 and $cminus > 0)
       or ($pr != null and $pr.state == "MERGED" and $pr.merge_reachable)),
    open_pr: ($pr != null and $pr.state == "OPEN"),
    unmerged_local_edits: (($mod | length) > 0 or ($add | length) > 0),
    unsaved_local_files:
      (([$untracked[] | select(.survival == "none")] | length)
       + ($ignored_unique | length)),
    # A same-named directory whose size differs a lot from its twin is not the
    # same content. Worth a look before anyone calls it bootstrap material.
    suspicious_bootstrap_dirs:
      [$bootstrap[] | select(.size_ratio == null or .size_ratio < 0.9 or .size_ratio > 1.1) | .path]
  }
}'
