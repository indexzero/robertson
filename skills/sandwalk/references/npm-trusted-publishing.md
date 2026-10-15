# npm Trusted Publishing: the upstream-authority problem

Read this whenever the posture includes npm packages published from GitHub
Actions.

## Trust model

Trusted Publishing replaces a long-lived npm token in CI with a short-lived
OIDC exchange. npm authorizes a configured repository and workflow, optionally
an environment, for selected actions.

~~~text
GitHub account and machine credentials
             ↓
repository source, refs, and workflow
             ↓
GitHub-hosted workflow receives OIDC identity
             ↓
npm grants short-lived package authority
             ↓
package publication and provenance
~~~

This removes one valuable secret. It also means that control of the authorized
GitHub source, workflow, release trigger, or environment may become control of
the npm publishing path.

## ChainDrop evidence

In [Jared Wray's August 31, 2026 incident report](https://jaredwray.com/blog/keyv-and-cacheable-chaindrop-worm),
he disclosed that a more-than-two-year-old full-access GitHub PAT remained on
an infected machine. He believes it was the credential used, while stating that
the acquisition path was not proven with complete certainty.

His account records PAT-authenticated Git and API activity that pushed poisoned
source, manipulated releases and tags, and reran workflows. The legitimate
GitHub Actions workflow then published the poisoned source through npm OIDC.
The packages had valid provenance because the authorized workflow really did
build them.

Use precise language:

- The attacker compromised GitHub authority upstream of the trusted publisher.
- OIDC and provenance operated as designed.
- Provenance established where and how the artifact was built.
- It did not establish that the source was safe, reviewed, or intended by the
  maintainer.

Do not describe the incident as forged provenance, a stolen npm OIDC token, or
an npm Trusted Publishing vulnerability.

npm documents the boundary directly: provenance supplies a verifiable link to
source and build instructions and does not guarantee that a package contains
no malicious code. See [npm provenance limitations](https://docs.npmjs.com/generating-provenance-statements/#provenance-limitations).

## Audit the real authority

Inspect all of the following:

1. GitHub classic and fine-grained PATs: owner, repository set, permissions,
   expiry, last use, and storage.
2. OAuth and GitHub Apps, SSH and deploy keys, active web and CLI sessions, and
   authorized devices.
3. Who can push or merge to the publishing ref, change workflow files, create
   or move release tags, create releases, dispatch or rerun workflows, approve
   environments, and bypass rulesets.
4. Workflow token permissions, third-party action pinning, untrusted-code
   execution, and persistence of checkout credentials.
5. Every npm trusted-publisher connection and its repository, workflow,
   environment, direct-publish permission, stage permission, and dist-tag
   permission.
6. npm maintainers, organization owners, package publishing access, legacy
   tokens, recovery routes, and stage approvers.

The presence of hardware keys on GitHub and npm does not settle items 1–5. An
already-issued PAT or active session does not need to repeat interactive MFA.

## Migration gates

Before changing a working publisher, recheck npm's current prerequisites.
Staged publishing presently requires npm 11.15.0 or later and Node 22.14.0 or
later. A new trusted-publisher connection must complete its first successful
publish within two days or it expires. The provider and required identity
fields of an existing connection are fixed; changing them requires deleting
and recreating the connection.

Plan the cutover so a tested publishing route remains available. Validate the
new OIDC and stage path, verify interactive promotion, then disallow
traditional tokens and revoke obsolete automation tokens. Do not delete the
only working publisher first and discover a workflow-name, environment, or
runtime mismatch afterward.

## Target state

1. Revoke old write-capable PATs and npm publishing tokens. Prefer GitHub CLI,
   Git Credential Manager, narrowly installed GitHub Apps, and short-lived
   workload identity. Give any unavoidable PAT minimum repository scope,
   permissions, and lifetime.
2. Protect publishing source, workflow files, release tags, releases, and
   deployment environments. Make workflow changes and bypass use visible.
3. Configure npm Trusted Publishing and then set package publishing access to
   **Require 2FA and disallow tokens**.
4. Restrict the trusted publisher to **stage-only** by allowing
   **npm stage publish** and withholding direct **npm publish** and dist-tag
   permission unless a documented workflow needs them.
5. Have CI pack and stage the exact candidate. Review or download that same
   tarball; do not rebuild a different artifact for approval.
6. Require a maintainer to promote the stage with interactive npm 2FA backed
   by a physical security key.

npm Trusted Publishing configurations created before May 20, 2026 retained
direct-publish behavior, and configurations created before September 3, 2026
did not receive the newer stage-first default automatically. Audit effective
permissions instead of inferring them from the feature name.

npm staged publishing keeps the candidate private until a maintainer approves
it with 2FA. npm WebAuthn security-key authentication works on the website and
CLI, connecting Sandwalk's physical-key topology to the final release gate.
OIDC credentials cannot list, view, approve, or reject stages; npm reserves
those operations for interactive authentication and proof of presence.

## Current official sources

- [npm Trusted Publishing](https://docs.npmjs.com/trusted-publishers/)
- [npm staged publishing](https://docs.npmjs.com/staged-publishing/)
- [npm provenance statements and limitations](https://docs.npmjs.com/generating-provenance-statements/)
- [npm security-key 2FA](https://docs.npmjs.com/configuring-two-factor-authentication/)
- [GitHub PAT guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)

Recheck these pages at execution time. This reference was last verified on
**2026-10-15**.
