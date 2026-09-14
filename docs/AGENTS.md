# Project Agent Instructions

## Source and regression entrypoints

This directory is the source checkout. See `README.md` for the pipeline, data locations and commands; `pyproject.toml` owns test and coverage configuration.

- Focused formatting/safety regression: `python3 scripts/check.py`.
- Full Python suite with the existing coverage gate: `python3 scripts/check.py --full`.
- Each run writes fresh logs and `result.json` under `artifacts/checks/`; `--report-dir` selects a new output directory. A failed preflight identifies missing dependencies or an editable install pointing at an old checkout; inspect it before retrying.
- For formatting discrepancies, check actual output units, explicit false/zero values, inherited styles, protected content and second-pass idempotence. A report's compliance percentage alone is insufficient.
- Actual document plans still require Web approval. Test-fixture approvals do not authorize changes to user jobs or documents. Source-only maintenance does not require installing or restarting the desktop App.

## macOS desktop App delivery

The installed desktop App is an AppKit shell containing a WKWebView. A successful frontend build or a matching HTTP response is not sufficient evidence that the desktop App has been updated.

Whenever a request changes or synchronizes the installed desktop App, first resolve the user's actual launch path and any symlink to the bundle. Complete all of the following before reporting desktop-delivery success:

1. Identify whether the change affects web source, native Swift source, packaging metadata, or more than one layer.
2. Build the production web assets and sync them to the installed project directory.
3. If native behavior, caching, downloads, startup, or packaging is involved, compile `packaging/macos/PaperSettingApp.swift` into the installed App bundle and copy the current `Info.plist`.
4. Increment `CFBundleShortVersionString` or `CFBundleVersion` for a user-visible desktop release.
5. Stop the exact running App process and its `scripts/start_local.py` service. Confirm port 8765 is no longer owned before relaunching.
6. Sign and verify the exact installed App bundle.
7. Launch using the exact user-facing path, not a development bundle.
8. Verify the new App owns the fresh service process and that the service returns the expected hashed assets.
9. Inspect the actual native App window. Do not substitute Chrome, Playwright, source hashes, file timestamps, or server HTML for native-window proof.
10. Exercise the changed interaction in the native App when automation permits. If it cannot be exercised, state that limitation instead of claiming full verification.

For WKWebView UI updates, account for disk cache, memory cache, and Service Worker registrations. Preserve Local Storage unless the requested change explicitly requires clearing user state.

The historical `.learnings/LEARNINGS.md` reference is no longer present in this checkout. The requirements above remain in force: web-only checks previously failed to prove native delivery. Do not block source work on locating that historical file.
