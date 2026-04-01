# Project Plan: LLM-as-a-Judge Toxicity Classification Pipeline

## Overview

Build a Python batch inference pipeline that reads prompts from `Inputs/input.csv`, sends each to the Google Gemini API (gemini-2.5-flash) with a system prompt encoding the toxicity rubric from `Rubric.md`, and writes classification + chain-of-thought justification to `Outputs/output.csv`.

### Output Format

| Column | Description |
|---|---|
| `text_to_evaluate` | Original input text |
| `classification` | One of: "Very Toxic", "Toxic", "Hard to Say", "Not Toxic" |
| `chain_of_thought` | Step-by-step reasoning justifying the classification |

---

## Phase 1: Project Setup

### 1.1 Create `requirements.txt`
- `google-genai>=1.0`
- `python-dotenv`
- `pytest`

### 1.2 Create `.env.example` and `.gitignore`
- `.env.example` with placeholder: `GEMINI_API_KEY=your-api-key-here`
- `.gitignore` entry for `.env` to prevent committing secrets

---

## Phase 2: Core Pipeline Implementation

### 2.1 Create `classifier.py`

#### `load_rubric(path) -> str`
- Reads `Rubric.md` and returns its content as a string
- Rubric is loaded dynamically so edits to the markdown are picked up without code changes

#### `build_system_prompt(rubric_text) -> str`
- Constructs a system prompt instructing the LLM to:
  - Act as a toxicity classifier
  - Use the 4 rubric categories exactly: "Very Toxic", "Toxic", "Hard to Say", "Not Toxic"
  - Think step-by-step in a `chain_of_thought` field before deciding
  - Output structured JSON: `{"classification": "...", "chain_of_thought": "..."}`

#### `classify_text(client, model, system_prompt, text) -> dict`
- Sends a single `generateContent` request via the Gemini SDK
- Uses `response_mime_type="application/json"` with a `response_schema` to enforce structured JSON output
- Parses and returns dict with `classification` and `chain_of_thought`
- Implements retry logic with exponential backoff (max 3 retries) for transient errors (rate limits, timeouts)

#### `process_csv(input_path, output_path, rubric_path, model) -> None`
- Reads input CSV via Python `csv` module (stdlib)
- Iterates rows, calls `classify_text` for each
- Writes results to output CSV with columns: `text_to_evaluate`, `classification`, `chain_of_thought`
- Logs progress to stdout (e.g., "Processing row 3/8...")

#### `main() -> None`
- Loads `.env` via `python-dotenv`
- Initializes `google.genai.Client()` with the `GEMINI_API_KEY`
- Calls `process_csv` with default paths (`Inputs/input.csv`, `Outputs/output.csv`, `Rubric.md`)
- Accepts optional CLI arguments via `argparse` for custom input/output/rubric paths and model selection

---

## Phase 3: Testing & Quality Assurance

### 3.1 Unit Tests — `tests/test_classifier.py`

| Test | What it verifies |
|---|---|
| `test_build_system_prompt` | Rubric text and JSON output instruction are present in the system prompt |
| `test_classify_text_valid_response` | Mocks Gemini client with known JSON; asserts correct parsing of classification and chain_of_thought |
| `test_classify_text_invalid_json` | Mocks a non-JSON response; asserts graceful error handling (no crash) |
| `test_classify_text_retry_on_rate_limit` | Mocks rate limit error then success; asserts retry logic works |
| `test_process_csv_end_to_end` | Mocks Gemini client; runs full pipeline on a 2-row temp CSV; asserts output CSV has correct columns and row count |
| `test_classification_values` | Asserts every classification value is one of the 4 valid rubric categories |

### 3.2 Manual QA Checklist

- [ ] `pip install -r requirements.txt` succeeds
- [ ] `pytest tests/` — all unit tests pass (mocked, no API key required)
- [ ] Run pipeline against `Inputs/input.csv` with a real API key
- [ ] Verify all 8 rows produce output in `Outputs/output.csv`
- [ ] Verify each classification is one of the 4 rubric categories
- [ ] Spot-check chain-of-thought coherence:
  - "haha you guys are a bunch of losers" → should be Toxic or Very Toxic
  - "It was a great show..." → should be Not Toxic
  - "This is such an urgent design problem; kudos..." → should be Not Toxic
- [ ] Verify output CSV is valid and opens correctly in spreadsheet software
- [ ] Verify `.env` is not committed to git

---

## Phase 4: Documentation

### 4.1 Create `README.md`
- Project description
- Setup instructions (install dependencies, set API key)
- Usage: `python classifier.py [--input PATH] [--output PATH] [--rubric PATH] [--model MODEL]`
- Output format description
- How to run tests

---

## File Inventory

| File | Action | Purpose |
|---|---|---|
| `Rubric.md` | No changes | Source rubric, read dynamically by pipeline |
| `Inputs/input.csv` | No changes | Input data (single column: `text_to_evaluate`) |
| `Outpus/` → `Outputs/` | Rename | Fix typo; pipeline writes `output.csv` here |
| `classifier.py` | Create | Main pipeline script |
| `requirements.txt` | Create | Python dependencies |
| `.env.example` | Create | API key placeholder for onboarding |
| `.gitignore` | Create | Exclude `.env` and other artifacts |
| `tests/test_classifier.py` | Create | Unit tests (all mocked, no API key needed) |
| `project_plan.md` | Create | This plan document |
| `README.md` | Create | Usage documentation |

---

## Verification Criteria

1. `pip install -r requirements.txt` completes without errors
2. `pytest tests/` — all unit tests pass
3. `python classifier.py` with `GEMINI_API_KEY` set produces `Outputs/output.csv`
4. Output CSV contains exactly 8 data rows plus header
5. Output CSV columns: `text_to_evaluate`, `classification`, `chain_of_thought`
6. Every `classification` value is one of: "Very Toxic", "Toxic", "Hard to Say", "Not Toxic"
7. Every `chain_of_thought` value is non-empty and references rubric reasoning

---

## Future Considerations

- **Concurrency**: Current design is sequential (one API call at a time). Sufficient for small inputs. For larger datasets, add `asyncio` with a semaphore for parallel requests.
- **Cost tracking**: Log token usage from API responses to monitor spend.
- **Batch API migration**: Gemini's Batch API supports async processing for large-scale runs — viable for non-urgent bulk classification.
