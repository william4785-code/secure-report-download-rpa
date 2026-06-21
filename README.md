# Secure Report Download RPA

A configurable Selenium platform for automating authenticated browser reports,
detecting completed downloads, and routing files to designated destinations.

This is a sanitized portfolio version of an internal report automation system.
All private URLs, hostnames, navigation parameters, account identifiers,
branch mappings, selectors, and destination folders have been removed from the
repository.

## Key Features

- Reuses an authenticated Microsoft Edge profile
- Waits for a configurable login-ready browser state
- Recursively searches nested frames and iframes
- Runs multiple reports through a registry-driven workflow
- Supports command-line report selection
- Passes dates and other runtime values into private JavaScript actions
- Detects completed browser downloads while ignoring partial files
- Routes and timestamps Excel or archive files
- Isolates report failures and produces a final failure summary
- Keeps private platform automation in an untracked configuration file

## Security Design

Operational browser automation often exposes more than passwords. Internal
URLs, server names, menu parameters, DOM selectors, account IDs, and saved
browser profiles can all reveal sensitive system details.

For that reason:

- The entry URL is supplied through `PLATFORM_ENTRY_URL`.
- The Edge profile path is supplied through `EDGE_PROFILE_DIR`.
- Report navigation and download JavaScript live in `config/private_reports.json`.
- The private configuration, browser profile, downloads, and output files are
  excluded by `.gitignore`.
- `config/reports.example.json` contains placeholders only and does not operate
  any real system.

## Project Structure

```text
.
├── config/
│   └── reports.example.json
├── scripts/
│   └── report_download_rpa.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Microsoft Edge must be installed. Modern Selenium versions can obtain a
compatible driver automatically when network and policy settings allow it.

## Private Configuration

Copy the example file:

```powershell
Copy-Item config\reports.example.json config\private_reports.json
```

Then configure each authorized report with:

- A report code
- A non-secret page hint
- A JavaScript readiness expression
- Private JavaScript for opening the report
- Private JavaScript for triggering the export
- Runtime arguments such as `{month_start}`, `{today}`, and `{yyyymm}`
- The destination directory and expected download filename prefix

Never commit the real configuration.

## Running

Run every enabled non-experimental report:

```powershell
python scripts\report_download_rpa.py
```

Run selected reports:

```powershell
python scripts\report_download_rpa.py REPORT_A REPORT_B
```

Include experimental tasks:

```powershell
python scripts\report_download_rpa.py --include-experimental
```

## Configuration

See `.env.example` for:

- Platform entry URL
- Edge profile directory
- Private report configuration path
- Download timeout

## Responsible Use

Use this project only with systems and data you are authorized to access.
Respect access controls, rate limits, audit requirements, terms of service, and
data-retention policies. Do not use browser automation to bypass security
controls or authentication requirements.
