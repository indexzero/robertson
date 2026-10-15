---
name: sandwalk
description: >-
  Harden an individual software or open-source maintainer against credential
  phishing, recovery abuse, session and token theft, and supply-chain
  publication through compromised source control. Use when a maintainer asks
  how to deploy YubiKeys or other physical FIDO security keys, choose and
  store backup keys, protect email, password-manager, Apple, Google, GitHub,
  npm, domain, DNS, cloud, CI, signing, secrets, Slack, or SSO accounts,
  separate daily and release/admin identities, audit recovery paths, or reduce
  Shai-Hulud / Sha1-Hulud-style release risk without making normal work
  onerous. Also use after suspicious MFA prompts when the requested work is
  proactive hardening. Do not use as a substitute for endpoint forensics or
  organization-wide IAM architecture.
metadata:
  tags: security-keys, fido2, webauthn, maintainer-security, npm, supply-chain
---

# Sandwalk

Make one phished prompt, stolen phone number, lost device, or exposed token
insufficient to obtain release authority. Keep the daily path easy enough that
the maintainer will continue using it.

Current first-party provider documentation is required for provider-specific
instructions. Authenticated account access is optional.

If the request is an organization-wide IAM design, hand it to an enterprise
identity or zero-trust assessment. Reuse the phishing-resistant principles,
but do not present this personal key topology as workforce lifecycle,
help-desk recovery, conditional-access, or break-glass architecture.

## Operating rules

- Calibrate to the maintainer's expertise. Skip basic security lectures and
  expose assumptions, bypasses, and tradeoffs.
- Use the current date in the assessment. Check first-party documentation
  before giving provider-specific limits, menu paths, or recovery claims.
- Never ask for a password, OTP, recovery code, security-key PIN, private key,
  session cookie, or token value. An inventory records credential names,
  scopes, locations, expiry, and last use, never secret material.
- Treat inbound calls, texts, emails, and push prompts as untrusted. Navigate
  to the provider through a known URL or app; never authenticate the caller.
- Do not remove the last verified factor, leave a critical account with only a
  carried key, or put every key and recovery artifact in one place.
- Keep a trusted session open during enrollment. Register and test every
  intended backup before removing a weaker factor.
- Do not claim that physical-key enrollment revokes sessions, PATs, OAuth
  grants, SSH keys, deploy keys, app passwords, npm tokens, or cloud keys.
- Keep sensitive posture data out of a public repository. Return the report in
  the conversation unless the user names a safe destination.

## Model five independent paths

Assess each critical account through five paths:

1. **Interactive sign-in** — passwords, passkeys, security keys, TOTP, push,
   SMS, voice, and trusted-device prompts.
2. **Recovery and enrollment** — recovery email/phone/codes, support, trusted
   contacts/devices, and the path used to add another authenticator.
3. **Existing access** — browser sessions, remembered devices, synced
   passkeys, command-line logins, and stolen cookies.
4. **Programmatic authority** — PATs, OAuth and GitHub Apps, SSH/deploy keys,
   package tokens, CI secrets, cloud credentials, and signing material.
5. **Release authority** — protected refs, workflow changes and dispatch,
   environments, trusted publishers, artifact review, and final promotion.

Physical FIDO keys strongly protect the first path and may protect parts of
the second and fifth. The posture is only as strong as the easiest remaining
path to equivalent authority.

## Triage before configuration

Classify the situation without overstating what an unsolicited prompt proves.

- Rejected password-reset prompts, OTP messages, and spoofable phone calls are
  evidence of attempts. Do not infer successful access from those alone.
- Unknown successful logins, new factors or recovery channels, unfamiliar
  sessions, token or OAuth changes, repository writes, workflow changes,
  releases, or package publications are compromise evidence.
- If compromise evidence exists, use a known-good device to contain it while
  planning enrollment: preserve useful logs, map automation and credential
  dependencies, revoke unknown or exposed sessions and machine credentials,
  restore account and release control, and follow the provider's incident
  path. If the endpoint may be infected, do not rotate credentials from it.

Continue useful read-only inventory work during containment. State clearly
which conclusions remain provisional.

## 1. Inventory the blast radius

Start with these control planes:

- Primary email and password manager.
- Apple and Google device identities.
- GitHub, npm, and organization-owner accounts.
- Domain registrar and authoritative DNS.
- Cloud, CI/CD, artifact-signing, and secrets-management control planes.
- Slack or SSO identities that can authorize repository or release changes.
- Mobile carrier and voicemail when the phone number is a sign-in or recovery
  factor for any account above.

Classify an account as:

- **Tier 0** when it can recover another critical account, publish software,
  change source/release policy, control domains, or mint privileged access.
- **Tier 1** when it can reach Tier 0 through an integration, session,
  approval, or support/recovery path.
- **Tier 2** when compromise has limited blast radius and cannot escalate.

Map recovery edges explicitly. Look for cycles such as primary email ↔
password manager, Apple/Google ↔ synced passkeys, GitHub ↔ npm recovery, and
carrier number ↔ primary email. Use the schema and output template in
[references/posture-template.md](references/posture-template.md).

## 2. Assign the smallest sound key topology

Default to three keys across every Tier 0 account:

| Key role | Use |
|---|---|
| Daily | Carried and used for ordinary sign-in. |
| Home-safe backup | Enrolled everywhere critical and stored securely at home. |
| Off-site backup | Enrolled everywhere critical and stored at a separate location. |
| Travel/spare | Optional fourth key that replaces the daily key while traveling or restores three-key coverage quickly. |
| Release/admin | Optional key for a separate, rarely used publisher or organization-owner identity. Give that identity its own backup too. |

Two keys are the operational minimum when a provider requires redundancy. They
can be geographically separated, but they cannot simultaneously fill the
daily, local-backup, and separate-site roles. Three are the normal Tier 0
baseline. Add the fourth and fifth roles only where they reduce risk or
downtime enough to justify their inventory cost.

One physical key can safely serve many relying parties: FIDO creates a unique,
origin-scoped credential for each account and service. Every physical key must
still be enrolled separately at every relying party; backup keys are not
clones. Reuse does correlate physical loss and availability across those
accounts, which is why the home and off-site keys plus a revocation roster
matter.

Choose whether a fourth key is an enrolled travel key or an unregistered cold
spare. A travel key is enrolled and tested only on the accounts needed while
traveling, then carried instead of the daily key. A cold spare can quickly
replace a lost key after another valid factor enrolls it, but it is not an
account-recovery route while unregistered.

A release-labelled key registered to the daily account has the same account
authority as its other registered authenticators. A real release boundary
requires a separate identity, browser profile or session, reduced day-to-day
privilege, and preferably a separate device context. Use a primary and backup
key for that identity rather than creating a one-key lockout hazard.

Give service-visible registrations stable opaque aliases such as `K-A`,
`K-B`, and `K-C`. Maintain a private roster that maps each alias to its
role, model/interface, serial or fingerprint when available, physical
location, registered accounts, and last test date. Keep PINs and recovery
codes elsewhere.

## 3. Run one enrollment ceremony

Before touching account settings, confirm each key's connector/NFC support,
FIDO2/WebAuthn capability, local PIN state, and discoverable-credential
capacity for services that create hardware-bound passkeys. A FIDO reset erases
credentials from the authenticator; do not use it as a routine setup step.

Work outward from recovery roots:

1. Password manager and primary email.
2. Apple and Google device identities, plus the carrier if a phone number
   remains a recovery factor.
3. GitHub, npm, organization-owner, and separate release identities.
4. Registrar, DNS, cloud, CI/CD, signing, and secrets systems.
5. Slack/SSO and any approval surface that can authorize repository or release
   changes.

Before enabling Apple Account security keys, confirm compatibility for every
signed-in device and account for Apple's setup-time sign-out of inactive
devices. Do not discover an unsupported device after changing the recovery
model.

For each account:

1. Confirm the official origin and review recent security activity from a
   known-good device.
2. Record existing factors, recovery paths, trusted devices/sessions, and
   programmatic credentials.
3. Check the provider's current key limit, then register the daily, home-safe,
   and off-site keys where supported. If it supports fewer, document the limit
   and a compensating recovery control. Register the travel key only if it has
   a defined operational role.
4. Test each key in a signed-out fresh browser or the provider's documented
   verification flow. Record the date and result.
5. Generate or verify recovery material. Store it separately from carried
   keys and omit it from the posture report.
6. Remove phishable fallback such as SMS, voice, approval push, or TOTP where
   the provider permits and only after stronger factors and recovery have
   passed their tests. Record any required or deliberately retained fallback
   as an accepted gap. If a phone number must remain, add carrier port/SIM
   controls and a unique voicemail PIN.
7. Revoke unknown or unnecessary sessions, devices, applications, and
   credentials. Reduce remaining credentials to minimum scope and lifetime.

Read [references/provider-baselines.md](references/provider-baselines.md) for
known provider constraints and the official sources that must be rechecked.

## 4. Close the machine-credential gap

For GitHub, npm, cloud, CI, and secrets systems, inventory every non-interactive
credential with its owner, exact capability, storage location, expiry, last
use, and replacement path.

- Revoke unknown, unused, unbounded, or superseded credentials.
- Prefer short-lived federation, provider-native CLI authentication, workload
  identity, and narrowly installed apps over human-owned bearer tokens.
- Where a PAT is unavoidable, use the smallest repository set and permissions,
  set an expiry, and keep it off ordinary development hosts when practical.
- Audit OAuth grants, GitHub Apps, SSH and deploy keys, workflow secrets,
  package tokens, cloud access keys, service accounts, and signing access.
- Review active sessions after enrollment. FIDO does not invalidate a stolen
  authenticated session.

## 5. Put a human boundary before publication

When npm and GitHub are in scope, read
[references/npm-trusted-publishing.md](references/npm-trusted-publishing.md).
The minimum target is:

- GitHub source, workflow, tag, release, and environment changes are protected
  in proportion to their publishing authority.
- Old write-capable PATs and long-lived npm publishing tokens are gone.
- npm Trusted Publishing uses OIDC and is restricted to `npm stage publish`;
  direct `npm publish` and dist-tag authority are disabled unless required.
- Package publishing access requires 2FA and disallows traditional tokens.
- A maintainer reviews the exact staged tarball, then approves promotion with
  an independently authenticated physical key.
- Provenance is treated as traceability for source and build path, not as a
  claim that the source is benign or that the maintainer intended the release.

## 6. Verify the system

Finish with evidence, not enrollment screenshots:

- Every Tier 0 account has a tested daily, home-safe, and off-site route, or a
  documented provider limitation and compensating control.
- Each lost key can be identified by alias and revoked across its account list.
- Recovery does not silently fall back to a weaker path with equivalent
  authority.
- Existing sessions and programmatic credentials have been reviewed.
- The release path needs an independent action after CI builds the artifact.
- A lost-daily-key drill works using the home backup without retrieving the
  off-site key.

Schedule a lightweight review roughly every 90 days and after a lost device,
travel incident, identity change, provider migration, or recovery change.
Review key locations and test status, recovery edges, active sessions, machine
credentials, trusted-publisher permissions, and release bypasses.

## Deliverable

For a full audit, return a compact **Sandwalk posture** containing:

1. Assumptions and active warnings.
2. Key topology and storage roles.
3. Account/recovery map with all five paths.
4. Ordered enrollment checklist with safe removal gates.
5. Session and machine-credential findings.
6. Release-path findings and the final human boundary.
7. Lost-key procedure, deferred work, and review date.

Distinguish `observed`, `user-reported`, `recommended`, and `verified`
facts. Do not mark an account complete until every selected backup key has been
tested and its non-interactive authority has been reviewed.

For a narrow question, answer it directly and include only the affected paths,
mandatory safety gates, and any finding that changes the user's premise. For
an urgent loss or compromise, lead with the containment sequence and produce
the broader posture after access is stable.
