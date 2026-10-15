# Provider baselines

These facts were checked against first-party sources on **2026-10-15**. Recheck
the linked documentation before giving click-by-click guidance or asserting a
limit. Product details age; the five-path model in the main skill is the
durable part.

## FIDO security keys

- A FIDO authenticator creates a distinct keypair for each relying party. The
  same physical key can cover many services without reusing one website's
  credential at another.
- Backup keys are separately enrolled authenticators, not clones. Register and
  test each one with every account before storing it.
- A device-bound hardware credential protects against origin phishing. It
  cannot revoke a session cookie or a bearer token already copied from an
  endpoint.

Sources: [FIDO Alliance on per-service keypairs](https://fidoalliance.org/fido-technotes-the-truth-about-attestation/),
[FIDO security reference](https://fidoalliance.org/specs/common-specs/fido-security-ref-v2.1-ps-20220523.html).

## Apple Account

- Apple uses third-party FIDO Certified keys; there is no special Apple-made
  key. Choose connectors that work with every regularly used Apple device.
- Apple requires at least two keys and supports up to six.
- New-device or web sign-in uses the account password plus either a physical
  key or a nearby already trusted Apple device.
- The key or a trusted device participates in password reset, account unlock,
  and key enrollment changes.
- Losing every trusted device and every enrolled key can permanently lock the
  account. Incompatible older devices may also lose sign-in capability after
  security keys are enabled.
- Setup signs out devices associated with the account that have not been used
  or unlocked for more than 90 days. Review the device list before enrollment.
- Removing all security keys returns the account to six-digit verification
  codes, so removal changes the threat model.

Source: [Apple, About Security Keys for Apple Account](https://support.apple.com/en-us/102637).

## Google Account

- Advanced Protection requires a passkey or security key for sign-in, tightens
  recovery, restricts third-party access, and is intended for people exposed to
  targeted attacks.
- Google recommends a primary and backup key. It also recommends recovery
  email and phone, so inventory and harden those paths rather than assuming
  enrollment removes them.
- A hardware-key passkey can satisfy sign-in without a password. The account
  can disable “Skip password when possible” if the maintainer wants an
  explicit password-then-key ceremony.
- A newly added key may take up to seven days to become trusted unless an
  already trusted authenticator accelerates it.
- Google warns that an iCloud restore can carry Google sessions, passwords,
  and passkeys to a new device and recommends security keys on the Apple
  Account for iCloud users.

Sources: [Advanced Protection FAQ](https://support.google.com/accounts/answer/7539956),
[security-key setup](https://support.google.com/accounts/answer/6103523),
[passkeys](https://support.google.com/accounts/answer/13548313).

## GitHub

- GitHub distinguishes a security key used after a password from a passkey
  that can satisfy password and 2FA requirements. Verify which mode each
  physical key registration is using.
- Personal-account enrollment currently starts with TOTP or SMS before adding
  security keys or passkeys. Do not report a physical-only posture if another
  configured path can still authenticate.
- Recovery can involve codes, passkeys, security keys, verified devices, SSH
  keys, or PATs. GitHub Support cannot simply restore access after all
  configured recovery routes are lost.
- Enabling 2FA does not revoke existing PATs or OAuth tokens.
- Review active sessions, PATs, OAuth and GitHub Apps, SSH keys, deploy keys,
  collaborators, organization roles, ruleset bypasses, workflow permissions,
  environments, tags, and releases.

Sources: [GitHub 2FA configuration](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication),
[mandatory 2FA and token behavior](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/about-mandatory-two-factor-authentication),
[recovery methods](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication-recovery-methods),
[PAT guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

## npm

- npm WebAuthn security keys work for website and CLI authentication but are
  enrolled through the website.
- npm describes recovery codes as the only way to ensure recovery after losing
  the second factor. Using one currently triggers a 72-hour hold on publishing,
  token creation, and settings changes.
- npm may use linked GitHub identity as an additional recovery signal, making
  GitHub part of the npm recovery map.
- For packages, inspect account 2FA, organization membership, maintainers,
  package publishing access, tokens, trusted publishers, allowed publisher
  actions, and dist-tag authority separately.

Sources: [npm 2FA configuration](https://docs.npmjs.com/configuring-two-factor-authentication/),
[npm 2FA model](https://docs.npmjs.com/about-two-factor-authentication/).

For npm release controls, read
[npm-trusted-publishing.md](npm-trusted-publishing.md).

## Password managers

Do not generalize across products. Inspect:

- whether a hardware key is a primary sign-in credential or an additional
  factor;
- whether TOTP, email, a recovery code, an emergency kit, an authorized
  device, family/team recovery, or vendor support can bypass it;
- whether existing clients remain authorized; and
- whether passkeys or vault data sync through Apple, Google, or another
  identity.

Current examples: [1Password security keys](https://support.1password.com/security-key/),
[1Password recovery codes](https://support.1password.com/recovery-codes/),
[Bitwarden FIDO2 WebAuthn](https://bitwarden.com/help/setup-two-step-login-fido/).

## Registrar, DNS, cloud, and secrets

Provider support varies. Prefer direct FIDO or a FIDO-protected IdP; list every
fallback and support recovery path. For high-impact domains, consider registry
lock as a separate control from account authentication. For cloud roots, enroll
multiple hardware devices where supported and store a backup securely.

Sources: [ICANN registrant protection guide](https://www.icann.org/en/groups/ssac/documents/sac-044-en.pdf),
[Cloudflare 2FA](https://developers.cloudflare.com/fundamentals/user-profiles/2fa/),
[AWS MFA guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html).

## Slack and SSO

Verify current native support. If a workspace uses SSO, put phishing-resistant
MFA at the identity provider and inspect owner/admin paths that can bypass SSO
or reset member 2FA. A communication account able to approve access or social-
engineer another maintainer belongs in the recovery graph even if it cannot
publish directly.

Sources: [Slack 2FA](https://slack.com/help/articles/204509068-Set-up-two-factor-authentication),
[Slack mandatory 2FA and SSO](https://slack.com/help/articles/212221668-Mandatory-workspace-two-factor-authentication).

## Carrier and voicemail

When a phone number remains a recovery or notification channel, use a unique
carrier-account password and PIN, enable carrier MFA and port/SIM protections,
and set a unique voicemail PIN. Remove SMS/voice authentication only after
tested stronger factors exist and the provider supports safe removal.

Source: [CISA mobile communications guidance](https://www.cisa.gov/sites/default/files/2024-12/guidance-mobile-communications-best-practices.pdf).
