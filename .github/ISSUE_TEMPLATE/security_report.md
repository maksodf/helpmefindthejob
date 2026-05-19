---
name: Security issue (public placeholder)
about: Read this before filing. Most security reports should NOT be public.
title: "[security] DO NOT FILE PUBLICLY — see SECURITY.md"
labels: ["security"]
---

## ⚠ Stop and read

If you have discovered a security vulnerability in Helpmefindthejob, **please do not file a public issue**. Follow the private process documented in [SECURITY.md](../../SECURITY.md):

- Contact the maintainer privately via the channel listed in
  [AUTHORS.md](../../AUTHORS.md). Once the project domain is registered,
  a dedicated security reporting address will be published in
  `SECURITY.md` and at `/.well-known/security.txt`.
- Responsible-disclosure practice applies. We commit to acknowledging
  within 5 business days and providing an initial assessment within
  14 business days.
- Public disclosure should be coordinated with us; please give us
  reasonable time to investigate and patch before publishing.

## When a public security issue is appropriate

Open a public issue here only if:

- The vulnerability is already publicly disclosed elsewhere with a
  CVE, advisory, or upstream patch, and you are tracking the
  remediation status in Helpmefindthejob.
- The issue is a general security hardening request (a missing header,
  a deprecated dependency, a feature improvement) rather than an
  exploitable vulnerability.
- The maintainer has explicitly asked you to move a previously private
  report into the public tracker.

In those cases, please replace the title prefix with your own clear
title, remove this placeholder text, and describe the issue in plain
language with steps to reproduce and proposed mitigation.

## If in doubt

Default to **private disclosure** via the SECURITY.md process. We would
rather receive a private report we do not strictly need than miss an
urgent one because the reporter was unsure.
