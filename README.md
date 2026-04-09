# LLM-as-a-Judge Toxicity Classification Pipeline

A Python batch inference pipeline that classifies text toxicity using Google Gemini as an LLM judge. It reads prompts from a CSV, evaluates each against a rubric, and outputs classifications with chain-of-thought reasoning.

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
python classifier.py [--input PATH] [--output PATH] [--rubric PATH] [--model MODEL]
```

| Argument | Default | Description |
|---|---|---|
| `--input` | `Inputs/input.csv` | Path to input CSV (must have a `text_to_evaluate` column) |
| `--output` | `Outputs/output.csv` | Path to write the results CSV |
| `--rubric` | `Rubric.md` | Path to the toxicity rubric markdown file |
| `--model` | `gemini-2.5-flash` | Gemini model name |

### Example

```bash
python classifier.py
python classifier.py --input data/my_texts.csv --output data/results.csv
```

## Output Format

The pipeline writes a CSV with three columns:

| Column | Description |
|---|---|
| `text_to_evaluate` | Original input text |
| `classification` | One of: "Very Toxic", "Toxic", "Hard to Say", "Not Toxic" |
| `chain_of_thought` | Step-by-step reasoning justifying the classification |

## Running Tests

All tests are mocked and do not require an API key:

```bash
python -m pytest tests/ -v
```

## Project Structure

```
├── classifier.py          # Main pipeline script
├── Rubric.md              # Toxicity classification rubric
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
