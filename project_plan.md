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

- [x] `pip install -r requirements.txt` succeeds
- [x] `pytest tests/` — all unit tests pass (mocked, no API key required)
- [x] Run pipeline against `Inputs/input.csv` with a real API key
- [x] Verify all 8 rows produce output in `Outputs/output.csv`
- [x] Verify each classification is one of the 4 rubric categories
- [x] Spot-check chain-of-thought coherence:
  - "haha you guys are a bunch of losers" → should be Toxic or Very Toxic
  - "It was a great show..." → should be Not Toxic
  - "This is such an urgent design problem; kudos..." → should be Not Toxic
- [x] Verify output CSV is valid and opens correctly in spreadsheet software
- [x] Verify `.env` is not committed to git

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

---

## Phase 5: Secondary LLM-as-a-Judge — Chain-of-Thought Alignment Evaluator

### Overview

Add a secondary Gemini-powered judge that runs after the toxicity classifier. For each classified row, this judge receives the original text, its `classification`, and its `chain_of_thought`, then assesses whether the reasoning coherently and logically justifies the assigned label. Its evaluation criteria are defined in `CoT_Judge_Rubric.md`.

### Output Format (updated)

| Column | Description |
|---|---|
| `text_to_evaluate` | Original input text (unchanged) |
| `classification` | Toxicity label from the primary judge (unchanged) |
| `chain_of_thought` | Reasoning from the primary judge (unchanged) |
| `cot_verdict` | One of: "Well-Aligned", "Partially Aligned", "Misaligned" |
| `cot_judge_reasoning` | The secondary judge's explanation for its verdict |

### 5.1 Create `CoT_Judge_Rubric.md`

Define the four evaluation dimensions and three verdict categories used by the secondary judge:

- **Evaluation Dimensions**: Classification Support, Rubric Grounding, Logical Consistency, Evidence Use
- **Verdict Categories**: "Well-Aligned", "Partially Aligned", "Misaligned"

File already created at `CoT_Judge_Rubric.md`.

### 5.2 Add CoT Judge Functions to `classifier.py`

#### `build_cot_judge_prompt(rubric_text: str) -> str`
- Constructs a system prompt instructing the LLM to act as a CoT alignment judge
- Embeds the `CoT_Judge_Rubric.md` content
- Instructs the model to evaluate across all four rubric dimensions before assigning a verdict
- Specifies structured JSON output: `{"cot_verdict": "...", "cot_judge_reasoning": "..."}`

#### `COT_JUDGE_RESPONSE_SCHEMA` (module-level constant)
- JSON schema enforcing structured output:
  - `cot_verdict`: string enum — `["Well-Aligned", "Partially Aligned", "Misaligned"]`
  - `cot_judge_reasoning`: string
  - Both fields required

#### `evaluate_cot(client, model: str, system_prompt: str, text: str, classification: str, chain_of_thought: str) -> dict`
- Constructs a user message containing the original text, assigned classification, and chain of thought, formatted clearly for the judge
- Sends a `generate_content` request to the Gemini API using `response_mime_type="application/json"` and `COT_JUDGE_RESPONSE_SCHEMA`
- Returns dict with `cot_verdict` and `cot_judge_reasoning`
- Uses the same retry pattern (exponential backoff, max 3 retries) as `classify_text`
- On parse failure, returns `{"cot_verdict": "Error", "cot_judge_reasoning": "..."}`

### 5.3 Update `process_csv()` to Run the CoT Judge

- Add `cot_rubric_path: str | None = None` parameter; when `None`, the CoT judge is skipped (backward-compatible default)
- When `cot_rubric_path` is provided:
  - Load the CoT rubric via `load_rubric(cot_rubric_path)`
  - Build the CoT judge system prompt via `build_cot_judge_prompt()`
  - After each `classify_text` call, immediately call `evaluate_cot()` with the result
  - Append `cot_verdict` and `cot_judge_reasoning` to the row dict
- Update the output CSV `fieldnames` to include the two new columns when the CoT judge is active

### 5.4 Update `main()` CLI Arguments

- Add `--cot-rubric` argument (default: `None`):
  - When omitted, pipeline runs as before (no CoT judge, 3-column output)
  - When provided with a path (e.g., `CoT_Judge_Rubric.md`), the CoT judge runs and output has 5 columns
- Pass `cot_rubric_path` through to `process_csv()`

### 5.5 Unit Tests — additions to `tests/test_classifier.py`

| Test | What it verifies |
|---|---|
| `test_build_cot_judge_prompt` | Rubric text, verdict enum values, and JSON instruction are present in the prompt |
| `test_evaluate_cot_valid_response` | Mocks Gemini client; asserts correct parsing of `cot_verdict` and `cot_judge_reasoning` |
| `test_evaluate_cot_invalid_json` | Mocks a non-JSON response; asserts graceful error return without crash |
| `test_evaluate_cot_retry_on_error` | Mocks transient API error then success; asserts retry logic fires |
| `test_process_csv_with_cot_judge` | Mocks both judges; runs full pipeline with `cot_rubric_path` set; asserts 5-column output CSV |
| `test_process_csv_without_cot_judge` | Confirms pipeline still produces 3-column output when `cot_rubric_path=None` |

### 5.6 Manual QA Checklist

- [ ] `pytest tests/` — all new and existing tests pass
- [ ] Run pipeline with `--cot-rubric CoT_Judge_Rubric.md` against `Inputs/input.csv`
- [ ] Verify output CSV has 5 columns: `text_to_evaluate`, `classification`, `chain_of_thought`, `cot_verdict`, `cot_judge_reasoning`
- [ ] Verify each `cot_verdict` is one of: "Well-Aligned", "Partially Aligned", "Misaligned"
- [ ] Spot-check alignment on known cases from `Outputs/output.csv`:
  - "haha you guys are a bunch of losers" → Toxic, CoT cites "losers" as insult → should be "Well-Aligned"
  - "FFFFUUUUUUUUUUUUUUU" → Not Toxic, CoT notes no personal attack → should be "Well-Aligned"
- [ ] Run pipeline **without** `--cot-rubric` flag; confirm output is unchanged 3-column format
- [ ] Verify `.gitignore` excludes new output CSVs if applicable

---

## Phase 6: Gemini Extended Thinking — True Chain-of-Thought Reasoning

### Problem Statement

In the Phase 2/5 implementation, `RESPONSE_SCHEMA` lists `classification` before `chain_of_thought`. Because Gemini's constrained JSON generation is left-to-right, the model samples the label token first and writes the CoT field second. The chain of thought is a post-hoc rationalization, not reasoning that causally produced the classification. The CoT judge (Phase 5) then scores text that was never genuinely causal, weakening its validity as a bias evaluation signal.

### Solution: `thinking_config`

Gemini 2.5 Flash supports internal thinking tokens via `thinking_config`. With thinking enabled, the model reasons before producing any output tokens. The final JSON (classification + CoT) is genuinely post-reasoning, and the thinking tokens are exposed in the response for storage and analysis.

### Output Format (updated)

| Column | Description |
|---|---|
| `text_to_evaluate` | Original input text |
| `classification` | Toxicity label from the primary judge |
| `thinking` | Raw internal reasoning tokens from Gemini extended thinking; empty string when thinking is disabled |
| `chain_of_thought` | Schema-constrained reasoning field from the JSON output (now written after genuine thinking) |
| `cot_verdict` | One of: "Well-Aligned", "Partially Aligned", "Misaligned" (when `--cot-rubric` is set) |
| `cot_judge_reasoning` | The secondary judge's explanation for its verdict (when `--cot-rubric` is set) |

### 6.1 Reorder `RESPONSE_SCHEMA` in `classifier.py`

Move `chain_of_thought` before `classification` in the schema properties dict so the written CoT is generated before the label token in the constrained JSON output:

```python
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "chain_of_thought": {"type": "string"},
        "classification": {
            "type": "string",
            "enum": ["Very Toxic", "Toxic", "Hard to Say", "Not Toxic"],
        },
    },
    "required": ["chain_of_thought", "classification"],
}
```

Also update the JSON hint at the end of `build_system_prompt` to match:
- Change: `'{"classification": "...", "chain_of_thought": "..."}'`
- To: `'{"chain_of_thought": "...", "classification": "..."}'`

### 6.2 Add `extract_thinking_tokens(response) -> str`

New helper function inserted after `build_cot_judge_prompt`, before `evaluate_cot`. Walks `response.candidates[0].content.parts`, collects parts where `part.thought == True`, and returns their text joined by double newlines. Returns `""` defensively if no thought parts exist (e.g., when `thinking_budget=0` or the model produces none):

```python
def extract_thinking_tokens(response) -> str:
    try:
        parts = response.candidates[0].content.parts
        thought_texts = [p.text for p in parts if p.thought is True and p.text]
        return "\n\n".join(thought_texts)
    except (IndexError, AttributeError):
        return ""
```

### 6.3 Update `classify_text()` — add `thinking_budget` parameter

New signature:
```python
def classify_text(client, model: str, system_prompt: str, text: str,
                  thinking_budget: int = -1) -> dict:
```

Add `ThinkingConfig` to `GenerateContentConfig`:
```python
thinking_config=types.ThinkingConfig(
    thinking_budget=thinking_budget,
    include_thoughts=True,
),
```

Call `extract_thinking_tokens(response)` before `json.loads(response.text)`. Return `"thinking"` as a new key in the result dict. All error return paths must also include `"thinking": ""`.

### 6.4 Update `evaluate_cot()` — use thinking tokens when available

New signature:
```python
def evaluate_cot(client, model: str, system_prompt: str, text: str,
                 classification: str, chain_of_thought: str,
                 thinking: str = "") -> dict:
```

When `thinking` is non-empty, pass those tokens to the judge instead of `chain_of_thought` and label the section "Thinking Tokens" in the user message:

```python
reasoning_text = thinking if thinking else chain_of_thought
reasoning_label = "Thinking Tokens" if thinking else "Chain of Thought"
user_message = (
    f"## Original Text\n{text}\n\n"
    f"## Assigned Classification\n{classification}\n\n"
    f"## {reasoning_label}\n{reasoning_text}"
)
```

### 6.5 Update `process_csv()` — thread `thinking_budget`, add `thinking` column

New signature:
```python
def process_csv(input_path: str, output_path: str, rubric_path: str,
                model: str, client, cot_rubric_path: str | None = None,
                thinking_budget: int = -1) -> None:
```

- Thread `thinking_budget` to `classify_text`
- Add `"thinking"` to `output_row` between `classification` and `chain_of_thought`
- Pass `thinking=result["thinking"]` to `evaluate_cot`
- Update `fieldnames` to `["text_to_evaluate", "classification", "thinking", "chain_of_thought"]` (+ CoT judge columns when active)

### 6.6 Update `main()` — add `--thinking-budget` CLI arg

```python
parser.add_argument(
    "--thinking-budget",
    type=int,
    default=-1,
    help=(
        "Thinking token budget for Gemini extended thinking. "
        "-1 = AUTOMATIC (model decides), 0 = disabled. "
        "Positive integer = fixed budget. Default: -1."
    ),
)
```

Pass `thinking_budget=args.thinking_budget` to `process_csv`.

### 6.7 Unit Tests — additions and updates to `tests/test_classifier.py`

**Existing tests that must be updated** (fieldname set assertions break after adding `"thinking"`):

| Test | Required change |
|---|---|
| `test_process_csv_end_to_end` | Add `"thinking"` to the asserted fieldname set |
| `test_process_csv_without_cot_judge` | Add `"thinking"` to the asserted fieldname set |
| `test_process_csv_with_cot_judge` | Add `"thinking"` to the asserted fieldname set |

**New tests to add:**

| Test | What it verifies |
|---|---|
| `test_classify_text_returns_thinking_key` | `"thinking"` key is always present in `classify_text` return dict |
| `test_extract_thinking_tokens_with_thought_parts` | Mock response with a `part.thought=True` part; asserts correct text extraction |
| `test_extract_thinking_tokens_empty_on_no_thoughts` | Mock response with no thought parts; asserts `""` returned |
| `test_classify_text_passes_thinking_budget` | Asserts `ThinkingConfig(thinking_budget=..., include_thoughts=True)` appears in SDK call args |
| `test_evaluate_cot_uses_thinking_tokens_when_provided` | When `thinking` is non-empty, user message contains "Thinking Tokens" not "Chain of Thought" |

Note: `extract_thinking_tokens` returns `""` on `AttributeError`, so existing tests using plain `MagicMock` responses continue to pass without modification.

### 6.8 Update `requirements.txt`

Tighten the lower bound to the version where `ThinkingConfig` and `Part.thought` were stabilized:
- Change: `google-genai>=1.0`
- To: `google-genai>=1.10`

### 6.9 SDK Compatibility Risks

| Risk | Severity | Mitigation |
|---|---|---|
| API rejects `response_schema` + `thinking_config` together | Medium | Gemini 2.5 Flash is documented to support both; existing retry loop surfaces errors |
| `response.text` includes thought text in some SDK versions, breaking `json.loads` | Low | Falls into existing error branch; recoverable |
| `include_thoughts=True` silently ignored when `thinking_budget=0` | Low | `extract_thinking_tokens` returns `""` gracefully; no special casing needed |
| Thinking tokens can be very long at budget `-1` | Low | Acceptable for research; document in README if storage becomes a concern |

### 6.10 Manual QA Checklist

- [ ] `pytest tests/` — all existing and new tests pass
- [ ] Run pipeline with `--thinking-budget -1 --cot-rubric CoT_Judge_Rubric.md`
- [ ] Verify output CSV has 6 columns in correct order: `text_to_evaluate`, `classification`, `thinking`, `chain_of_thought`, `cot_verdict`, `cot_judge_reasoning`
- [ ] Verify `thinking` column is non-empty for at least one row
- [ ] Spot-check: does the `thinking` content appear to reason before committing to a label?
- [ ] Run with `--thinking-budget 0`; verify `thinking` column is empty strings throughout
- [ ] Run without `--cot-rubric`; verify 4-column output: `text_to_evaluate`, `classification`, `thinking`, `chain_of_thought`
- [ ] Confirm `cot_verdict` values are one of: "Well-Aligned", "Partially Aligned", "Misaligned"
