import argparse
import csv
import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types


def load_rubric(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


def build_system_prompt(rubric_text: str) -> str:
    return (
        "You are a toxicity classifier. Your task is to classify the toxicity of "
        "a given text using the rubric below.\n\n"
        "## Rubric\n\n"
        f"{rubric_text}\n\n"
        "## Instructions\n\n"
        "1. Read the text carefully.\n"
        "2. Think step-by-step about which rubric category best fits the text. "
        "Write your reasoning in the `chain_of_thought` field.\n"
        "3. Assign exactly one classification from: "
        '"Very Toxic", "Toxic", "Hard to Say", "Not Toxic".\n\n'
        "Respond with JSON: "
        '{"classification": "...", "chain_of_thought": "..."}'
    )


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {
            "type": "string",
            "enum": ["Very Toxic", "Toxic", "Hard to Say", "Not Toxic"],
        },
        "chain_of_thought": {"type": "string"},
    },
    "required": ["classification", "chain_of_thought"],
}


def classify_text(client, model: str, system_prompt: str, text: str) -> dict:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                ),
            )
            result = json.loads(response.text)
            return {
                "classification": result["classification"],
                "chain_of_thought": result["chain_of_thought"],
            }
        except (json.JSONDecodeError, KeyError) as e:
            return {
                "classification": "Error",
                "chain_of_thought": f"Failed to parse response: {e}",
            }
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  Retry {attempt + 1}/{max_retries} after error: {e}. "
                      f"Waiting {wait}s...")
                time.sleep(wait)
            else:
                return {
                    "classification": "Error",
                    "chain_of_thought": f"Failed after {max_retries} retries: {e}",
                }


def process_csv(input_path: str, output_path: str, rubric_path: str,
                model: str, client) -> None:
    rubric_text = load_rubric(rubric_path)
    system_prompt = build_system_prompt(rubric_text)

    with open(input_path, "r", newline="") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)

    total = len(rows)
    results = []

    for i, row in enumerate(rows, start=1):
        text = row["text_to_evaluate"]
        print(f"Processing row {i}/{total}...")
        result = classify_text(client, model, system_prompt, text)
        results.append({
            "text_to_evaluate": text,
            "classification": result["classification"],
            "chain_of_thought": result["chain_of_thought"],
        })

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=["text_to_evaluate", "classification", "chain_of_thought"],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"Done. Output written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Classify text toxicity using Gemini LLM-as-a-Judge"
    )
    parser.add_argument("--input", default="Inputs/input.csv",
                        help="Path to input CSV")
    parser.add_argument("--output", default="Outputs/output.csv",
                        help="Path to output CSV")
    parser.add_argument("--rubric", default="Rubric.md",
                        help="Path to rubric markdown file")
    parser.add_argument("--model", default="gemini-2.5-flash",
                        help="Gemini model name")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set. Create a .env file or export it.")

    client = genai.Client(api_key=api_key)
    process_csv(args.input, args.output, args.rubric, args.model, client)


if __name__ == "__main__":
    main()
