# LLM-as-a-Judge Toxicity Classification Pipeline

A Python batch inference pipeline that classifies text toxicity using Google Gemini as an LLM judge. It reads prompts from a CSV, evaluates each against a rubric, and outputs classifications with chain-of-thought reasoning. An optional secondary judge evaluates whether each chain of thought coherently justifies its assigned classification.

Extended thinking is enabled by default, causing Gemini to reason internally before producing any output. The raw thinking tokens are captured and stored alongside the schema-generated chain of thought, giving the CoT judge access to genuine pre-output reasoning rather than post-hoc rationalization.

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API key**

   Copy the example env file and add your Gemini API key:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and replace `your-api-key-here` with your actual key.

## Usage

```bash
python classifier.py [--input PATH] [--output PATH] [--rubric PATH] [--model MODEL] [--cot-rubric PATH] [--thinking-budget N]
```

| Argument | Default | Description |
|---|---|---|
| `--input` | `Inputs/input.csv` | Path to input CSV (must have a `text_to_evaluate` column) |
| `--output` | `Outputs/output.csv` | Path to write the results CSV |
| `--rubric` | `Rubric.md` | Path to the toxicity rubric markdown file |
| `--model` | `gemini-2.5-flash` | Gemini model name |
| `--cot-rubric` | _(none)_ | Path to the CoT judge rubric; enables the secondary judge when set |
| `--thinking-budget` | `-1` | Thinking token budget: `-1` = AUTOMATIC (model decides), `0` = disabled, positive integer = fixed budget |

### Examples

```bash
# Toxicity classification only, thinking enabled automatically (4-column output)
python classifier.py

# With secondary CoT alignment judge (6-column output)
python classifier.py --cot-rubric CoT_Judge_Rubric.md

# Fixed thinking budget for reproducibility
python classifier.py --cot-rubric CoT_Judge_Rubric.md --thinking-budget 8000

# Disable thinking (reverts to single-pass JSON generation)
python classifier.py --thinking-budget 0

# Custom paths
python classifier.py --input data/my_texts.csv --output data/results.csv --cot-rubric CoT_Judge_Rubric.md
```

## Post-Processing: Binary Classification Analysis

After running the classifier, use `process_outputs.py` to transform the raw outputs into binary classification format and generate evaluation metrics:

```bash
python process_outputs.py
```

**What it does:**
- Loads `Outputs/output.csv` and extracts all relevant columns including CoT judge outputs
- Converts to binary classification:
  - **Target (ground truth)**: `0.0` → "Not Toxic", all other values → "Toxic"
  - **Classification (prediction)**: "Not Toxic" stays unchanged, all other values → "Toxic"
- Generates a confusion matrix and computes classification metrics (accuracy, precision, recall, F1-score)
- Creates a CoT verdict distribution visualization showing alignment breakdown

**Outputs:**
- `Output_Analysis/Output_Analysis_Data.csv` — Processed binary classification data with CoT columns (id, target, classification, thinking, cot_verdict, cot_judge_reasoning)
- `Output_Analysis/confusion_matrix.png` — Confusion matrix heatmap visualization
- `Output_Analysis/confusion_matrix_metrics.txt` — Classification metrics and confusion matrix summary
- `Output_Analysis/cot_verdict_distribution.png` — Bar chart showing distribution of CoT verdict categories (Well-Aligned, Partially Aligned, Misaligned)
- `Output_Analysis/cot_verdict_statistics.txt` — CoT verdict distribution statistics with counts and percentages

## Output Format

### Toxicity classifier only

| Column | Description |
|---|---|
| `text_to_evaluate` | Original input text |
| `classification` | One of: "Very Toxic", "Toxic", "Hard to Say", "Not Toxic" |
| `thinking` | Raw internal reasoning tokens from Gemini extended thinking; empty string when `--thinking-budget 0` |
| `chain_of_thought` | Schema-constrained reasoning field from the JSON output |

### With `--cot-rubric` (secondary judge enabled)

Two additional columns are appended:

| Column | Description |
|---|---|
| `cot_verdict` | One of: "Well-Aligned", "Partially Aligned", "Misaligned" |
| `cot_judge_reasoning` | The secondary judge's explanation for its verdict |

The CoT judge evaluates the `thinking` tokens (when present) rather than the `chain_of_thought` field, since thinking tokens represent genuine pre-output reasoning. It assesses reasoning across four dimensions: Classification Support, Rubric Grounding, Logical Consistency, and Evidence Use. It does not re-evaluate the original text for toxicity.

## Binary Classification Output Format

After post-processing, `Output_Analysis/Output_Analysis_Data.csv` contains the binary classification dataset with the following columns:

| Column | Description |
|---|---|
| `id` | Record identifier |
| `target` | Binary ground truth: "Not Toxic" or "Toxic" |
| `classification` | Binary prediction: "Not Toxic" or "Toxic" |
| `thinking` | Raw internal reasoning tokens from Gemini extended thinking |
| `cot_verdict` | CoT judge verdict: "Well-Aligned", "Partially Aligned", or "Misaligned" |
| `cot_judge_reasoning` | The secondary judge's explanation for its verdict |

**Visualizations generated:**
- **Confusion Matrix** (`confusion_matrix.png`) — Heatmap comparing target vs. classification predictions
- **CoT Verdict Distribution** (`cot_verdict_distribution.png`) — Bar chart showing alignment verdict breakdown across the dataset

## How Extended Thinking Works

Without extended thinking, `classification` and `chain_of_thought` are co-generated in a single constrained JSON pass. Because `classification` appeared first in the schema, the label was sampled before any reasoning was written — making the chain of thought a post-hoc rationalization.

With `thinking_config` enabled, Gemini reasons internally via thinking tokens before producing any output tokens. The JSON output (and the CoT judge's evaluation) is then genuinely post-reasoning. The `thinking` column captures these tokens verbatim for transparency and analysis.

## Running Tests

All tests are mocked and do not require an API key:

```bash
python -m pytest tests/ -v
```

## Project Structure

```
├── classifier.py          # Main pipeline script
├── process_outputs.py     # Binary classification output mapper and confusion matrix generator
├── Rubric.md              # Toxicity classification rubric
├── CoT_Judge_Rubric.md    # Chain-of-thought alignment judge rubric
├── requirements.txt       # Python dependencies
├── .env.example           # API key placeholder
├── .gitignore             # Excludes .env and build artifacts
├── Inputs/
│   └── input.csv          # Input texts to classify
├── Outputs/
│   └── output.csv         # Generated classifications (raw outputs)
├── Output_Analysis/       # Binary classification analysis outputs
│   ├── Output_Analysis_Data.csv      # Processed binary classification data (with CoT columns)
│   ├── confusion_matrix.png          # Confusion matrix visualization
│   ├── confusion_matrix_metrics.txt  # Classification metrics summary
│   ├── cot_verdict_distribution.png  # CoT verdict distribution visualization
│   └── cot_verdict_statistics.txt    # CoT verdict statistics and percentages
└── tests/
    └── test_classifier.py # Unit tests (mocked)
```
