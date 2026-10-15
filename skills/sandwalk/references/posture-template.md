# Sandwalk posture template

Use this structure for the deliverable. Keep it in the conversation by default;
account names, recovery relationships, and key locations may be sensitive.
Never place secret values, key PINs, OTPs, recovery codes, private keys, or
session cookies in it.

## Status vocabulary

- **Observed** — verified directly in provider settings, logs, or an API.
- **User-reported** — supplied by the maintainer but not independently checked.
- **Recommended** — proposed target state.
- **Verified** — changed and then tested through the documented flow.
- **Unknown** — not yet inspected. Unknown is not equivalent to absent.

## Report

~~~markdown
# Sandwalk posture

Assessment date: YYYY-MM-DD

## Assumptions and active warnings

- ...

## Key topology

| Alias | Role | Interface/model | Serial/fingerprint | Storage | Daily identities | Admin identities | Last tested | Status |
|---|---|---|---|---|---|---|---|---|
| K-A | Daily | USB-C/NFC | private identifier | Carried | ... | — | YYYY-MM-DD | Verified |
| K-B | Home backup | USB-C/NFC | private identifier | Home safe | ... | ... | YYYY-MM-DD | Verified |
| K-C | Off-site backup | USB-C/NFC | private identifier | Separate site | ... | ... | YYYY-MM-DD | Verified |

## Account and recovery map

| Control plane | Tier / authority | Interactive auth | Recovery and enrollment | Sessions/devices | Programmatic authority | Release authority | Keys tested | Gaps / action |
|---|---|---|---|---|---|---|---|---|
| Primary email | Tier 0; recovers ... | ... | ... | ... | ... | — | K-A/K-B/K-C | ... |

## Recovery edges and cycles

- A → B because ...
- B → A because ...
- Break or compensate for the cycle by ...

## Enrollment order

- [ ] Password manager and primary email
- [ ] Apple, Google, carrier, and voicemail
- [ ] GitHub, npm, organization-owner, and release identities
- [ ] Registrar, DNS, cloud, CI/CD, signing, and secrets
- [ ] Slack/SSO and release-approval surfaces

## Machine credentials and live access

| Credential/session name | Owner | Capability | Stored or active where | Expiry / last use | Keep, narrow, rotate, or revoke | Evidence |
|---|---|---|---|---|---|---|

## Release path

Source authority → workflow authority → build identity → registry authority →
artifact review → public promotion

- Independent boundary after CI: ...
- Bypasses: ...
- Provenance claim: ...

## Lost daily key procedure

1. Treat “available” or “worked before” as user-reported until the backup
   succeeds now. Keep any trusted session open and test the home key from a
   known-good device in a separate fresh browser or documented provider flow.
2. Match the lost physical key to its exact private-roster alias and every
   registration. One device may appear more than once if it was enrolled as
   both a passkey and a second-factor security key. Do not guess from an
   ambiguous label.
3. Check the provider's minimum enrolled-key rule. If revocation would violate
   that minimum or leave only one usable route, enroll and test the replacement
   first.
4. Revoke the lost registration from every account in its private registration
   list.
5. Review security activity, sessions, factor/recovery changes, and machine
   credentials for activity after the loss time. Loss does not itself prove
   that another credential was compromised.
6. Enroll and test the spare; restore daily, home, and off-site coverage.
7. Replace recovery material only when exposure or provider behavior warrants.

## Deferred work and review

- [ ] ...
- Next lightweight review: YYYY-MM-DD
~~~

## Completion gate

An account is complete only when:

1. every selected key has been independently enrolled and tested;
2. recovery and authenticator-enrollment paths are understood;
3. trusted devices and active sessions have been reviewed;
4. programmatic credentials have been inventoried;
5. release authority, when present, has an independent final boundary; and
6. the maintainer can revoke a lost key by alias without guessing.
