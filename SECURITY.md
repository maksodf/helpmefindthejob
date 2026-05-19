# Security Policy

**Live security.txt** (RFC 9116):
<https://maksodf.github.io/helpmefindthejob/.well-known/security.txt>
— also served by the app at `/.well-known/security.txt` on any
running deployment. Canonical reporting flow is the GitHub Security
Advisories link in the `security.txt` Contact list.

## Supported Versions

Helpmefindthejob is in active early development. Until a stable 1.0 release, security fixes are applied to the main branch only. Once 1.0 ships, a supported-version table will be added here.

## Reporting a Vulnerability

If you discover a security issue in Helpmefindthejob, please report it privately rather than opening a public issue.

Reports go to the maintainer via the contact information in AUTHORS.md. Once the project domain is registered, a dedicated security reporting address will be added here and at /.well-known/security.txt per RFC 9116.

A PGP key for encrypted reports will be published when the domain is registered.

## Response Commitments

We aim to:

1. Acknowledge receipt within 5 business days
2. Provide an initial assessment within 14 business days
3. Coordinate a fix and disclosure timeline with the reporter
4. Credit the reporter in the release notes for the fix, unless they prefer anonymity

We follow responsible-disclosure practice and ask reporters to do the same: please allow reasonable time for investigation and patching before public disclosure.

## Scope

In scope:
- The Helpmefindthejob codebase in this repository
- The MCP server interface (mcp_server.py)
- Authentication, authorization, and session handling in the web app
- Data-at-rest encryption mechanisms
- The deployed reference instance once live at the public demo domain

Out of scope:
- Vulnerabilities in third-party dependencies (please report those upstream and inform us)
- Issues caused by user-supplied AI provider configurations (BYO-AI; the user controls those credentials)
- Issues requiring physical access to a self-hosted instance

## Acknowledgments

Reporters who help improve Helpmefindthejob's security are listed in ACKNOWLEDGMENTS.md with their consent.
