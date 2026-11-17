# GitHub & Website Submission Checklist

## Current repository state (verified 2026-11-04)
| Item | Status | Evidence |
|---|---|---|
| Professional README | Present | `README.md` |
| Install instructions (Windows) | Present | README PowerShell blocks |
| `requirements.txt` | Present | Root file |
| Organized source | Present | `app.py`, `src/`, `tests/`, `benchmarks/`, `pages/` |
| Automated tests | Present | 39 tests OK |
| Dataset documentation | Present | `docs/DATASET_METHODOLOGY.md` + README caveat |
| OSM attribution | Present | README |
| Screenshots | Missing | No project screenshots in repo |
| LICENSE file | Missing | Not found |
| Git repository (`.git`) | **Missing** | `Test-Path .git` → False |
| `git` CLI on PATH | **Missing** | Shell reports git not recognized |
| Meaningful commit history | Cannot verify / Missing | No git repo |
| GitHub remote | Missing | No remotes |
| GitHub Issues / project board | Cannot verify | No remote |
| GitHub Pages site | Missing | Not deployed; no verified live URL |
| Published website claim | **Do not claim** | Not verified |

## If GitHub is required (typical steps)
1. Install Git for Windows and restart the terminal.
2. `git init` in the project (exclude `.venv/`, caches, large graph pickles if policy requires).
3. Commit in logical units (algorithms, UI, docs, tests).
4. Create a GitHub (or Cursor Origin) remote and push.
5. Add 2–4 screenshots under `docs/screenshots/` and link them from README.
6. Add a LICENSE only if the team/course chooses one; keep OSM ODbL attribution regardless.

## If GitHub Pages is required
- Build a **static** mini-site (for example `site/index.html`) describing the project, algorithms, and screenshots.
- Do **not** break the Streamlit app.
- Pages cannot host the live Streamlit solver unless a separate hosting service is used.
- Only mark “published” after opening the real Pages URL in a browser.

## Suggested `.gitignore` essentials
```
.venv/
__pycache__/
*.pyc
.streamlit/secrets.toml
data/graphs/*.pkl
cache/
```
(Decide with the team whether cached graphs should be committed for offline grading.)
