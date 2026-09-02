# Demo Mode

Demo Mode exercises the public workflow without connecting to an operational
platform. It requires no URL, browser profile, credentials, private
configuration, network connection, or Microsoft Edge session.

The demo builds valid synthetic XLSX and ZIP downloads in a temporary staging
directory, detects them with the same filename and extension rules used by the
automation engine, and routes timestamped copies to an ignored output folder.

Run the default Excel demo:

```powershell
python -m secure_report_download_rpa --demo
```

Include the experimental archive example:

```powershell
python -m secure_report_download_rpa --demo --include-experimental
```

Choose an output location or a specific demo report:

```powershell
python -m secure_report_download_rpa --demo --demo-output-dir demo_output\my_run
python -m secure_report_download_rpa REPORT_B --demo
```

Generated artifacts are synthetic and `demo_output/` is excluded from Git.
Demo Mode validates task selection, completed-download detection, extension
filtering, destination creation, filename timestamping, and file routing. It
intentionally does not simulate authentication, private selectors, or a real
platform session.
