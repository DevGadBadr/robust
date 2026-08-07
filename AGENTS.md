# AGENTS.md

## Cursor Cloud specific instructions

### What this project is
"Robust" is a **Windows-targeted PyQt5 desktop app** that manages Selenium Chrome drivers for scraping/automation. Entry point: `robust.py`. Jobs live in `resources/jobs.json`, UI/window settings in `resources/settings.json`. It is a single desktop app (no backend service, no web server).

### Platform reality (important)
The app hard-depends on Windows-only APIs, imported at module load and used at startup:
- `pywin32` (`win32gui`, `win32con`, `win32process`) — Chrome-window embedding.
- `winreg` (stdlib, Windows-only) — dark-mode detection in `ui/manageTheme.py`.
- `ctypes.windll.dwmapi` — native title-bar theming.

`pywin32` cannot be installed on Linux and native Chrome-window embedding / title-bar theming are Windows-only. Full native development is intended for Windows. The Linux setup below exists so the UI and the core Selenium job flow can be run/tested in this cloud VM.

### Environment layout (already provisioned in the snapshot)
- `.venv/` holds the cross-platform deps. The update script (re)creates it and installs `PyQt5 selenium psutil`. `requirements.txt` also lists `pywin32`; do **not** `pip install -r requirements.txt` on Linux — it fails on `pywin32`. That is why the update script installs the subset explicitly.
- Windows-only modules are **shimmed for Linux** in `.venv/lib/python3.12/site-packages/`: `win32gui.py`, `win32con.py`, `win32process.py`, `winreg.py`. Importing `win32gui` also patches `ctypes.windll` with an inert stub. These are no-ops that let the PyQt UI launch; Chrome embedding and title-bar theming stay inert. These live in the venv (not the repo). If they go missing, the app fails at `import win32gui`; recreate the four tiny files (safe no-op functions; `winreg.OpenKey`/`QueryValueEx` should `raise FileNotFoundError`; `win32gui` should set `ctypes.windll` to an object whose attribute chains are callables returning 0).
- System libs `python3.12-venv` and the Qt `xcb` runtime libraries are installed via apt and persist in the snapshot. Google Chrome is preinstalled; `chromedriver` is auto-downloaded by Selenium Manager on first run (needs network egress).

### Running the app
A desktop is available on `DISPLAY=:1`. Run:
```
DISPLAY=:1 .venv/bin/python robust.py
```
On startup it auto-creates 1 non-headless Selenium Chrome driver and applies the default job (`latestJob` in `settings.json`).

### Chrome renderer crash caveat (non-obvious)
With the default 64 MB `/dev/shm`, Chrome renderers crash with **"Aw, Snap! Error code: 4"** mid-job. The app does not pass `--disable-dev-shm-usage`, so enlarge shared memory before running:
```
sudo mount -o remount,size=2g /dev/shm
```
This mount is runtime-only and must be redone after a fresh VM boot.

### Driving a job
In a driver's instance row, the per-driver **next-action arrow** executes the job's actions one at a time (status shows e.g. "Job N executed with result: Done" and a checkmark appears per row). The bottom "Execute All" advances all drivers together. Jobs are sequences of `GetUrl` / `InputField` / `ClickButton` / `ExtractText` / `ExtractLinks` actions.

### Lint / tests / build
There is no configured linter, no automated test suite, and no build step in this repo. Validate syntax with `.venv/bin/python -m compileall .`.
