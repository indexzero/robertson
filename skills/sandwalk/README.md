# Sandwalk

[![Keyv and Cacheable — ChainDrop Worm artwork](assets/chaindrop-worm.png)](https://jaredwray.com/blog/keyv-and-cacheable-chaindrop-worm)

_Artwork from [Jared Wray's ChainDrop incident report](https://jaredwray.com/blog/keyv-and-cacheable-chaindrop-worm)._

**Avoid Sha1-Hulud.**

Sandwalk is a Codex skill for hardening one software maintainer's identity and
release authority with physical FIDO security keys. It aims for a short
enrollment ceremony, low daily friction, independent recovery, and an explicit
human boundary before a package becomes public.

Invoke it with a concrete request:

~~~text
Use $sandwalk to map my Google, Apple, password-manager, GitHub, npm,
Cloudflare, AWS, and Slack/SSO recovery paths and turn these five YubiKeys into
a tested rollout plan.
~~~

The skill examines five separate paths: interactive sign-in, account recovery,
existing sessions, programmatic credentials, and release authority. A hardware
key can make sign-in phishing-resistant. It does not revoke an old session,
PAT, OAuth grant, SSH key, npm token, cloud key, or compromised workflow.

## Default key topology

The default is three physical keys registered on every Tier 0 account. The
same set can cover many services because FIDO creates a different,
origin-scoped credential for each service. Losing one key affects availability
across those services, so the two stored backups and registration roster are
part of the design.

| Role | Normal placement and use |
|---|---|
| Daily key | Carried and used for normal authentication. |
| Home-safe backup | Enrolled everywhere critical and stored securely at home. |
| Off-site backup | Enrolled everywhere critical and stored in a separate location. |
| Travel or cold-spare key | Optional fourth key: either enroll it for travel and carry it instead of the daily key, or leave it unregistered for quick replacement after another valid factor authorizes enrollment. |
| Release/admin key | Optional key for a separate publisher or organization-owner identity, with its own backup. |

A release-labelled key on the same daily account is another equally powerful
authenticator. Real separation needs a different identity, session or browser
profile, and reduced daily privilege.

## Accounts in scope

- Primary email and password manager.
- Apple and Google device identities.
- GitHub, npm, and organization-owner accounts.
- Domain registrar and authoritative DNS.
- Cloud, CI/CD, artifact-signing, and secrets-management control planes.
- Slack or SSO identities that can authorize repository or release changes.
- Mobile carrier and voicemail when the number participates in recovery.

Sandwalk inventories recovery links, trusted devices, live sessions, and
machine credentials as well as the visible MFA setting. It never puts
passwords, OTPs, key PINs, token values, private keys, or recovery codes in its
report.

## What ChainDrop showed about npm Trusted Publishing

npm Trusted Publishing removes a long-lived npm publishing secret from CI. It
also makes GitHub repository and workflow authority part of the publishing
trust boundary.

Jared Wray's account of the August 4, 2026 ChainDrop incident says an old,
more-than-two-year-old, full-access GitHub personal access token remained on an
infected machine. He believes that credential was used, while noting that the
acquisition path could not be proved with complete certainty. The attacker
used PAT-authenticated Git and API access to place poisoned source in the real
repositories and operate their release path. The legitimate GitHub Actions
workflow then obtained a genuine OIDC identity and published through npm:

~~~text
stale full-access GitHub PAT
        ↓
poisoned source and release state
        ↓
legitimate GitHub Actions workflow
        ↓
npm Trusted Publishing through OIDC
        ↓
malicious package with valid provenance
~~~

This was an exploitation of the GitHub authority upstream of the trusted
publisher, rather than a forged provenance statement or an OIDC bypass. Every
cryptographic claim in the provenance could be true while the package was
malicious. npm's own documentation says provenance establishes a verifiable
link to source and build instructions; it does not guarantee an absence of
malicious code.

A stale GitHub API token with sufficient source, workflow, or release
authority can therefore drive a malicious publication through the authentic
workflow and produce valid provenance. Provenance authenticates the release
path. It cannot certify maintainer intent or source safety.

The practical target state is:

1. Revoke obsolete write-capable GitHub PATs and long-lived npm publishing
   tokens; narrowly scope and expire any credential that must remain.
2. Protect source, workflow files, tags, releases, and deployment environments
   according to their publishing authority.
3. Configure npm Trusted Publishing as **stage-only**: allow
   **npm stage publish**, and withhold direct **npm publish** and dist-tag
   authority unless there is a documented need.
4. Set npm publishing access to **Require 2FA and disallow tokens**.
5. Inspect the exact staged tarball, then approve it with interactive 2FA. npm
   WebAuthn works with a physical security key on both the website and CLI.

That final key-backed promotion adds a boundary that a compromised GitHub
workflow cannot cross by itself: npm does not allow OIDC credentials to run
the stage-approval commands, which require interactive proof of presence.

Sources:

- [Jared Wray, “Keyv and Cacheable — ChainDrop Worm”](https://jaredwray.com/blog/keyv-and-cacheable-chaindrop-worm)
- [npm Trusted Publishing](https://docs.npmjs.com/trusted-publishers/)
- [npm staged publishing](https://docs.npmjs.com/staged-publishing/)
- [npm provenance limitations](https://docs.npmjs.com/generating-provenance-statements/#provenance-limitations)
- [npm security-key 2FA](https://docs.npmjs.com/configuring-two-factor-authentication/)

The provider facts in this skill were checked on **2026-10-15**. Sandwalk
rechecks first-party documentation when used because authentication, recovery,
and publishing controls change.
