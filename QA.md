# QA Code Review — classifier.py

**Reviewed:** Phase 1 (Project Setup) & Phase 2 (Core Pipeline Implementation)
**Date:** 2026-04-09

---

## Summary

The implementation is well-structured and faithfully follows the project plan. All five specified functions are present and the overall architecture is sound. A few issues were identified, categorized by severity below.

---

## Issues Found

### HIGH — No issues

No critical bugs or security vulnerabilities detected.

### MEDIUM

| # | Location | Issue | Detail |
|---|---|---|---|
| M1 | `classifier.py:68-72` | `json.JSONDecodeError` / `KeyError` not retried | Parse errors return immediately with `"Error"`. If the API returns a malformed response transiently, the request is not retried — only network/API exceptions trigger retry. Consider moving these into the retry loop or adding a single retry for parse failures. |
| M2 | `classifier.py:84` | `process_csv` signature differs from plan | Plan specifies `process_csv(input_path, output_path, rubric_path, model)` (4 args). Implementation adds `client` as a 5th parameter. This is functionally better (decouples client init from CSV processing), but is a deviation from the spec. Acceptable — just noting it. |

### LOW

| # | Location | Issue | Detail |
|---|---|---|---|
| L1 | `classifier.py` | `if __name__ == "__main__"` guard | Present and correct — no issue. Noted for completeness. |
| L2 | `.gitignore` | Missing `Outputs/output.csv` | Output files are generated artifacts. Consider adding `Outputs/*.csv` to `.gitignore` to avoid committing generated results. Optional — depends on whether outputs should be tracked. |

---

## Checklist vs. Project Plan (Phase 2 Spec)

| Requirement | Status | Notes |
|---|---|---|
| `load_rubric(path) -> str` | PASS | Reads file, returns string |
| `build_system_prompt(rubric_text) -> str` | PASS | Includes rubric, JSON instruction, 4 categories, chain-of-thought instruction |
| `classify_text` uses `response_mime_type="application/json"` | PASS | Set in `GenerateContentConfig` |
| `classify_text` uses `response_schema` | PASS | Schema with enum constraint on classification values |
| `classify_text` retry with exponential backoff (max 3) | PASS | `2^attempt` seconds, 3 attempts |
| `process_csv` reads via `csv` module | PASS | Uses `csv.DictReader` |
| `process_csv` writes output with correct 3 columns | PASS | `text_to_evaluate`, `classification`, `chain_of_thought` |
| `process_csv` logs progress to stdout | PASS | `"Processing row {i}/{total}..."` |
| `main` loads `.env` via `python-dotenv` | PASS | `load_dotenv()` called |
| `main` initializes `genai.Client()` with API key | PASS | `genai.Client(api_key=api_key)` |
| `main` default paths match spec | PASS | `Inputs/input.csv`, `Outputs/output.csv`, `Rubric.md` |
| `main` accepts CLI args via `argparse` | PASS | `--input`, `--output`, `--rubric`, `--model` |
| `main` fails clearly if API key missing | PASS | `raise SystemExit(...)` |
| Output directory created if missing | PASS | `os.makedirs(..., exist_ok=True)` |

---

## Phase 1 Files Check

| File | Status | Notes |
|---|---|---|
| `requirements.txt` | PASS | Contains `google-genai>=1.0`, `python-dotenv`, `pytest` |
| `.env.example` | PASS | Contains `GEMINI_API_KEY=your-api-key-here` |
| `.gitignore` | PASS | Excludes `.env`, `__pycache__/`, `*.pyc`, `.pytest_cache/` |
| `.env` | PASS | Present locally, excluded from git via `.gitignore` |

---

## Security Review

| Check | Status |
|---|---|
| API key not hardcoded | PASS — loaded from `.env` at runtime |
| `.env` excluded from version control | PASS — in `.gitignore` |
| No user input passed to shell/eval | PASS — text only sent to Gemini API |
| No path traversal risk | PASS — paths from CLI args used only with `open()` and `csv` |

---

## Verdict

**PASS** — Implementation is ready for Phase 3 (testing). The M1 issue (parse errors not retried) is a minor robustness gap that is unlikely to trigger given the `response_schema` enforcement, but could be hardened during or after testing.
