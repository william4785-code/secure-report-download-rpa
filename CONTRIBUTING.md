# Contributing

## Branch Flow

```text
feature/* -> develop -> main
```

- Branch from `develop` for normal work.
- Keep each feature branch focused on one change.
- Open feature pull requests against `develop`.
- Promote a tested release from `develop` to `main` through a release pull
  request.
- Never push operational configuration to any branch.

## Commit Style

Use small commits with an explicit purpose, for example:

```text
test: cover download completion detection
refactor: extract configuration models
feat: add deterministic demo mode
ci: enforce public safety checks
docs: explain the deployment boundary
```

## Required Checks

Before opening a pull request:

```powershell
python scripts/check_public_safety.py
python -m compileall -q scripts
```

After the test suite is introduced, all pytest and lint checks must also pass.

Run the unit suite with:

```powershell
python -m pytest
```

## Pull Request Scope

A pull request must describe:

- the behavior changed;
- tests or checks performed;
- security and privacy impact;
- whether configuration or output contracts changed.

Generated reports, screenshots, browser profiles, real configurations, and
operational logs are never acceptable pull request artifacts.
