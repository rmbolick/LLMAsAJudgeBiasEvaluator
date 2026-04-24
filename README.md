# LLM-as-a-Judge Toxicity Classification Pipeline

A Python batch inference pipeline that classifies text toxicity using Google Gemini as an LLM judge. It reads prompts from a CSV, evaluates each against a rubric, and outputs classifications with chain-of-thought reasoning. An optional secondary judge evaluates whether each chain of thought coherently justifies its assigned classification.

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
python classifier.py [--input PATH] [--output PATH] [--rubric PATH] [--model MODEL] [--cot-rubric PATH]
```

| Argument | Default | Description |
|---|---|---|
| `--input` | `Inputs/input.csv` | Path to input CSV (must have a `text_to_evaluate` column) |
| `--output` | `Outputs/output.csv` | Path to write the results CSV |
| `--rubric` | `Rubric.md` | Path to the toxicity rubric markdown file |
| `--model` | `gemini-2.5-flash` | Gemini model name |
| `--cot-rubric` | _(none)_ | Path to the CoT judge rubric; enables the secondary judge when set |

### Examples

```bash
# Toxicity classification only (3-column output)
python classifier.py

# With secondary CoT alignment judge (5-column output)
python classifier.py --cot-rubric CoT_Judge_Rubric.md

# Custom paths
python classifier.py --input data/my_texts.csv --output data/results.csv --cot-rubric CoT_Judge_Rubric.md
```

## Output Format

### Toxicity classifier only

| Column | Description |
|---|---|
| `text_to_evaluate` | Original input text |
| `classification` | One of: "Very Toxic", "Toxic", "Hard to Say", "Not Toxic" |
| `chain_of_thought` | Step-by-step reasoning justifying the classification |

### With `--cot-rubric` (secondary judge enabled)

Two additional columns are appended:

| Column | Description |
|---|---|
| `cot_verdict` | One of: "Well-Aligned", "Partially Aligned", "Misaligned" |
| `cot_judge_reasoning` | The secondary judge's explanation for its verdict |

The CoT judge evaluates each chain of thought across four dimensions: Classification Support, Rubric Grounding, Logical Consistency, and Evidence Use. It does not re-evaluate the original text for toxicity — it only assesses the quality of the reasoning.

## Running Tests

All tests are mocked and do not require an API key:

```bash
python -m pytest tests/ -v
```

## Project Structure

```
├── classifier.py          # Main pipeline script
├── Rubric.md              # Toxicity classification rubric
├── CoT_Judge_Rubric.md    # Chain-of-thought alignment judge rubric
├── requirements.txt       # Python dependencies
├── .env.example           # API key placeholder
├── .gitignore             # Excludes .env and build artifacts
├── Inputs/
│   └── input.csv          # Input texts to classify
├── Outputs/
│   └── output.csv         # Generated classifications
└── tests/
    └── test_classifier.py # Unit tests (mocked)
```
