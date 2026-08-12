# ORBIT — Personal Local AI Computer Agent

ORBIT is a voice-first AI agent for Windows. Core loop:

```
VOICE → UNDERSTAND → PLAN → ACT → VERIFY → LEARN
```

It was built end-to-end inside a browser-based Claude Code session, which has **no
Windows desktop, no microphone, and no display**. Every module that could be built
and tested there was built and tested for real (intent parsing, planning,
permissions, skills, memory, file/PDF/Excel operations, and real Playwright browser
control). Anything that requires an actual Windows desktop — global hotkeys, mouse/
keyboard control, microphone capture, the system tray icon — is implemented with a
real Windows backend plus a **Simulated** backend used for development, and is
explicitly marked **LOCAL WINDOWS TEST NEEDED** below and in the code.

---

## 1. Requirements

- **OS**: Windows 10/11 for real computer control and voice. (Everything else runs
  on Linux/macOS too, for development.)
- **Python**: 3.10–3.12
- **RAM**: 4 GB minimum, 8 GB+ recommended for a better ASR model
- **Disk**: ~2 GB free for dependencies + your chosen ASR model
- **Microphone** for real voice control
- Optional: an Anthropic or OpenAI API key, for higher-quality complex-task planning
  and summarization (ORBIT works fully offline without one, using the rule-based
  planner and the local extractive summarizer)

## 2. Installation

### Windows (real install)

```powershell
git clone <this-repo>
cd Automation
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
```

This creates a virtual environment, installs `requirements/base.txt` +
`requirements/windows.txt`, installs Playwright's Chromium, and copies
`.env.example` → `.env`.

### Linux/macOS (development / testing only — no real computer control)

```bash
./scripts/setup_dev.sh
source .venv/bin/activate
python main.py --text
```

## 3. Environment variables

Copy `.env.example` to `.env` and edit as needed. Nothing is hardcoded — all
configuration is environment-driven (see `orbit/config.py`).

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Optional cloud LLM for complex planning | unset |
| `ORBIT_LLM_PROVIDER` / `ORBIT_LLM_MODEL` | Which cloud LLM to use, if configured | `anthropic` / `claude-sonnet-5` |
| `ORBIT_ASR_ENGINE` | `faster-whisper` or `mock` | `faster-whisper` |
| `ORBIT_ASR_MODEL_SIZE` | `tiny`/`base`/`small`/`medium`/`large-v3` | `small` |
| `ORBIT_ASR_DEVICE` | `cpu` or `cuda` | `cpu` |
| `ORBIT_ASR_LANGUAGE` | `auto`, `en`, `hi`, ... | `auto` |
| `ORBIT_DATA_DIR` | Where memory/skills/history/models live | `./data` |
| `ORBIT_REQUIRE_CONFIRMATION` | Force confirmation on all sensitive actions | `true` (keep this `true`) |
| `ORBIT_FORCE_SIMULATED` | Force the simulated computer-control backend | `false` |
| `ORBIT_HOTKEY` | Push-to-talk global hotkey | `ctrl+shift+space` |

**Secrets are never stored in ORBIT's memory database** — `MemoryStore` actively
rejects any key that looks like a password/token/secret (see
`orbit/memory/store.py`). Use environment variables or Windows Credential Manager
for real secrets.

## 4. ASR setup

ORBIT uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (a fast
CTranslate2 port of OpenAI Whisper) as the default local, offline speech engine. It
supports English, Hindi, and code-switched Hinglish out of the box, and is swappable
via the `ASREngine` interface (`orbit/asr/base.py`) — a mock engine is used for
testing, and a different engine can be dropped in later without touching the rest
of the pipeline.

Nothing downloads automatically. To fetch a model on your Windows PC:

```powershell
python scripts\download_asr_model.py --list          # see recommendation + catalog
python scripts\download_asr_model.py --size small     # downloads with confirmation
```

## 5. Model setup (Model Manager)

`orbit/models/manager.py` tracks the ASR model catalog (name, size, RAM/VRAM
requirement, relative speed, installed/active state) and
`orbit/windows/hardware.py` detects your CPU/RAM/GPU to recommend a model that
actually fits your machine — it will never recommend a model your RAM can't hold.
GPU detection is best-effort (NVIDIA via `nvidia-smi`); CPU-only machines get a
conservative recommendation.

## 6. Running ORBIT

```powershell
# Text mode — works anywhere, no mic/hotkey/tray required. Good smoke test.
python main.py --text

# Real voice mode — Windows only, requires requirements/windows.txt + a mic.
python main.py --voice
```

In `--voice` mode: hold the configured hotkey (`ORBIT_HOTKEY`, default
`ctrl+shift+space`) to talk, release to send. Say **"Orbit, stop"** or press `Esc`
(tray icon, when running) to interrupt at any time.

### The critical demo (spec section 20)

All of these work today in `--text` mode (ASR mocked, everything below it real):

```
you> Orbit, open Chrome.
you> Orbit, create a folder called Buyer Leads.
you> Orbit, open this PDF and summarize it.
you> Orbit, create an Excel sheet from this information.
you> Orbit, open Gmail and draft an email.
you> Orbit, don't send it.
you> Orbit, send it.        <- always asks for confirmation first
```

`tests/test_brain.py` runs this exact sequence as an automated test.

## 7. Windows permissions

- **Microphone**: Windows Settings → Privacy & security → Microphone → allow
  desktop apps.
- **Accessibility / UI Automation**: `pywinauto` and `pyautogui` may prompt for
  accessibility permissions the first time they control another window.
- **Global hotkey**: the `keyboard` library can require running the terminal as
  Administrator to capture hotkeys system-wide (outside the focused window).
- **Browser automation uses your real Chrome, not a separate one**: on Windows,
  ORBIT launches your actual installed Google Chrome pointed at your actual
  profiles — the same ones you already use, already signed into Gmail. With
  `ORBIT_CHROME_PROFILE` unset, Chrome shows its own "Who's using Chrome?"
  picker (see below) so you pick which profile ORBIT drives that run; set it
  in `.env` to skip the picker and go straight into that profile every time.
  Run `scripts\list_chrome_profiles.ps1` to see the exact profile names
  Chrome knows about on your PC. Default in `.env.example` is
  `Vrindavan Organics`. You can also change the active profile any time
  just by saying it, e.g. *"switch to Rahul Soni profile"* — no `.env`
  edit or restart needed, it takes effect on the next browser/Gmail action.
- **A profile can only be open in one place at a time**: Chrome locks a
  profile to whichever process opened it. If "Vrindavan Organics" is already
  open in your normal Chrome window, ORBIT can't also drive it — close that
  window first (other profiles/windows can stay open; only the one ORBIT
  needs has to be free).

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: faster_whisper` | `pip install -r requirements/windows.txt` |
| Hotkey doesn't fire globally | Run PowerShell/terminal as Administrator |
| `RuntimeError: RealWindowsController can only run on Windows` | Expected on Linux/macOS — use `--text` mode or set `ORBIT_FORCE_SIMULATED=true` |
| Playwright browser fails to launch | `python -m playwright install chromium` |
| Gmail draft/send automation breaks | Gmail's DOM changes over time — `orbit/email/sender.py`'s `BrowserGmailSender` selectors may need updating; this is the one piece of code in the repo that cannot be verified until you test it against a real, logged-in Gmail session. `EmailTool.do_draft`'s response tells you honestly whether the live Gmail action succeeded ("opened in Gmail") or only the local record was kept ("local draft only" / an error) |
| Email drafts locally but Gmail shows nothing | You aren't logged into Google in the Chrome profile ORBIT used — pick (or configure via `ORBIT_CHROME_PROFILE`) a profile that's already signed into that Gmail account |
| Browser action does nothing / errors about profile in use | The Chrome profile ORBIT is trying to use is already open in one of your normal Chrome windows — close that window first, then retry |
| Memory database locked | Only one ORBIT process should hold `data/memory/orbit.db` at a time |

## 9. Local testing commands

```bash
# Full test suite (99 tests, all pass in this workspace — no Windows needed)
pytest -q

# Lint
ruff check orbit tests main.py

# Just the critical-demo end-to-end tests
pytest -q tests/test_brain.py -v

# Hardware detection + model recommendation on this machine
python -c "from orbit.windows.hardware import detect_hardware, recommend_asr_model; hw = detect_hardware(); print(hw); print('recommend:', recommend_asr_model(hw))"

# Interactive text-mode REPL
python main.py --text
```

---

## What's built, tested, and what needs a real Windows PC

| Area | Status |
|---|---|
| Voice hotkey / recorder / VAD abstractions | Built and tested here against a fake `keyboard` module (hold-to-talk press/release logic). Simulated backends tested here too. Real hardware I/O (`keyboard`, `sounddevice`, `webrtcvad`) is **LOCAL WINDOWS TEST NEEDED**. |
| ASR (faster-whisper) | Built, swappable via `ASREngine`, download/load path now consistent (tested against a fake `faster_whisper` module). **LOCAL WINDOWS TEST NEEDED** for real transcription (no mic here) — pipeline logic tested with `MockASREngine`. |
| Personal vocabulary + corrections | Built and tested (fuzzy correction, raw-vs-interpreted transcript, corrections stored but never auto-applied). |
| Intent parsing (EN/HI/Hinglish) | Built and tested with real mixed-language examples. |
| Task planner (single-step + 8-step bulk-outreach plan) | Built and tested. |
| Permission engine (SAFE/SENSITIVE + confirmation) | Built and tested — sensitive actions default-deny without an explicit confirm. |
| Verification framework | Built and tested (file-exists, text-present, window-open checks). |
| Windows computer control | Built: `SimulatedController` fully tested here; `RealWindowsController` (pyautogui/pywinauto) is **LOCAL WINDOWS TEST NEEDED**. |
| App registry + hardware detection | Built and tested (detection of *installed* apps only works on Windows — **LOCAL WINDOWS TEST NEEDED** for that part specifically). |
| Files / PDF / Excel / Word tools | Built and tested with real files (real PDFs via a test fixture, real .xlsx round-trips). |
| Browser control (Playwright) | Built and **actually tested** in this workspace — real headless Chromium navigation, text extraction, screenshots. |
| Email (draft/send/cancel, permission-gated) | Built and tested against a mock sender, plus a browser-double test of `BrowserGmailSender`'s draft-then-send sequencing logic. On real Windows, `bootstrap.py` wires the real `BrowserGmailSender` (persistent, logged-in browser profile) automatically. Gmail's actual DOM/selectors are **LOCAL WINDOWS TEST NEEDED** — this workspace has no Google account to log into. |
| Skills / Teach Mode engine | Built and tested (variables, loops, conditions, approval gates, retries, verification). |
| Model Manager | Built and tested. |
| ASR training pipeline | Built: clean/normalize/split/evaluate(WER/CER)/version are real and tested; download/train correctly refuse to run automatically (require network/GPU + explicit local execution). |
| Memory (SQLite, secret-rejecting) | Built and tested. |
| Activity history | Built and tested. |
| Desktop UI | Text-mode REPL built and tested here. `python main.py --voice` now runs the system tray icon (status dot, current task, Stop/History/Settings menu, Esc-to-stop) as the real voice-mode UI, with menu wiring tested against a fake icon here. Actual on-screen rendering is **LOCAL WINDOWS TEST NEEDED** — no display in this workspace. |

---

## Architecture

```
orbit/
  voice/        hotkey, mic recorder, VAD          (Simulated + real backends)
  asr/          ASR engine interface, faster-whisper + mock, vocabulary
  agent/        intent parsing, task planner, brain (orchestrator)
  tools/        Tool interface + registry; one module per capability
  windows/      computer-control abstraction, app registry, hardware detection
  browser/      Playwright wrapper
  files/        real file/PDF/Excel/Word operations
  email/        draft store, sender abstraction (mock + browser-based Gmail)
  memory/       SQLite-backed persistent memory
  skills/       Skill schema + Teach Mode engine
  permissions/  SAFE/SENSITIVE classification + confirmation gate
  verification/ post-action verification checks
  models/       ASR Model Manager
  training/     optional ASR fine-tuning pipeline + dataset registry
  ui/           text-mode CLI, tray UI
main.py         entrypoint: --text or --voice
```

`orbit/bootstrap.py` is the single place that wires all of this together into an
`OrbitSystem` — used by `main.py`, the CLI, and the test suite, so there's exactly
one way the pieces fit.

## Safety model

- **SAFE** actions (open an app, search, read a file, create a draft) run
  immediately.
- **SENSITIVE** actions (send email/WhatsApp, delete files, purchases, form
  submission, bulk actions, account/password changes) always go through
  `PermissionEngine`, which defaults to **deny** unless a confirmation callback
  explicitly approves — there is no bypass for "it's just a small bulk action."
- A skill step can force a confirmation checkpoint even for an otherwise-SAFE
  action (`requires_approval=True` on a `SkillStep`).
- "Orbit, stop" halts the current plan before its next step executes.

## Not built in this pass (intentionally, per scope)

Mobile app, cloud SaaS/billing, multi-user accounts, a from-scratch ASR model,
plugin marketplace, fully autonomous financial actions, unlimited bulk messaging.
The architecture (tool registry, permission engine, skills engine) is built so
these can be added later without a rewrite.
