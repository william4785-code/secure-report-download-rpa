# Security Policy

## Public Repository Boundary

This repository contains only a sanitized, reusable report-download engine.
Every branch, tag, pull request, workflow artifact, issue, and release must be
safe for public disclosure.

Never commit or upload:

- operational platform URLs, hostnames, page hints, selectors, or navigation
  scripts;
- usernames, passwords, tokens, authorization headers, cookies, browser
  profiles, or session storage;
- personal or company filesystem paths and destination mappings;
- SQL, database connection details, internal schemas, or infrastructure names;
- downloaded reports, screenshots, HTML dumps, HAR files, logs, or business
  data;
- real report codes, filenames, organizational mappings, or schedules.

Do not use a private-looking branch in this public repository as an internal
deployment store. Operational configuration belongs in a separate access-
controlled system and is supplied to the public engine only at runtime.

## Before Every Commit

Run:

```powershell
python scripts/check_public_safety.py
```

Also inspect staged files explicitly:

```powershell
git diff --cached --name-status
git diff --cached --check
```

Never bypass a security failure by force-adding an ignored file. Remove the
sensitive content and rotate any credential that may have been exposed.

## Reporting a Vulnerability

Do not open a public issue containing a vulnerability, credential, internal
URL, selector, or operational detail. Contact the repository owner privately
through an established trusted channel and provide only the minimum information
needed to reproduce the problem.
