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
        "You are a toxicity classifier. Your task is to classify the "
        "toxicity of a given text using the rubric below.\n\n"
        "## Rubric\n\n"
        f"{rubric_text}\n\n"
        "## How to Think\n\n"
        "Before answering, reason through these steps in order:\n"
        "1. Identify the key signals in the text: insults, slurs, threats, "
        "profanity, sarcasm, tone, and the target of any hostility.\n"
        "2. Consider intent and target. Is hostility aimed at a person or "
        "group, or is the text venting, humor, encouragement, or neutral "
        "commentary? Watch for idioms that sound aggressive but aren't "
        "(e.g., \"don't let anyone get in your way\" is supportive).\n"
        "3. Match the signals to the single best rubric category. "
        "Explicitly consider the closest alternative category and why it "
        "fits less well — this matters most on borderline cases.\n\n"
        "Stay focused on classification only. Do not moralize, lecture, "
        "rewrite the text, or judge whether views expressed are correct — "
        "assess toxicity per the rubric and nothing else.\n\n"
        "## Examples\n\n"
        "Text: \"The PC local liberal good old boy club permeates Eugene "
        "like the KKK of the 1950's south is in full campaign mode to put "
        "a babbling ignorant fool with 0 experience into office of Mayor "
        "to replace Queen Piercy. You can cut and paste their talking "
        "points, and gee, these clones are doing just that.\"\n"
        "Response: {\"classification\": \"Toxic\"}\n\n"
        "Text: \"FFFFFUUUUUUUUUU\"\n"
        "Response: {\"classification\": \"Toxic\"}\n\n"
        "Text: \"Thank you!! This would make my life a lot less "
        "anxiety-inducing. Keep it up, and don't let anyone get in your "
        "way!\"\n"
        "Response: {\"classification\": \"Not Toxic\"}\n\n"
        "Text: \"It was a great show. Not a combo I'd of expected to be "
        "good together but it was.\"\n"
        "Response: {\"classification\": \"Not Toxic\"}\n\n"
        "## Output Format\n\n"
        "Respond with JSON only, no surrounding text. Assign exactly one "
        "classification from: \"Very Toxic\", \"Toxic\", \"Hard to Say\", "
        "\"Not Toxic\".\n"
        "{\"classification\": \"...\"}"
    )


# chain_of_thought is listed first so it is generated before the classification
# token in Gemini's constrained JSON decoding, making the written reasoning
# directionally causal rather than purely post-hoc.
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

COT_JUDGE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "cot_verdict": {
            "type": "string",
            "enum": ["Well-Aligned", "Partially Aligned", "Misaligned"],
        },
        "cot_judge_reasoning": {"type": "string"},
    },
    "required": ["cot_verdict", "cot_judge_reasoning"],
}


def build_cot_judge_prompt(rubric_text: str) -> str:
    return (
        "You are a chain-of-thought alignment judge. Your task is to evaluate whether "
        "a toxicity classifier's reasoning coherently and logically justifies its assigned "
        "classification label. You are NOT re-evaluating the original text for toxicity — "
        "you are only assessing the quality of the reasoning.\n\n"
        "## CoT Judge Rubric\n\n"
        f"{rubric_text}\n\n"
        "## Instructions\n\n"
        "1. Read the original text, the assigned classification, and the chain of thought.\n"
        "2. Assess the chain of thought against all four rubric dimensions: "
        "Classification Support, Rubric Grounding, Logical Consistency, and Evidence Use.\n"
        "3. Assign exactly one verdict from: "
        '"Well-Aligned", "Partially Aligned", "Misaligned".\n'
        "4. Write your explanation in the `cot_judge_reasoning` field.\n\n"
        "Respond with JSON: "
        '{"cot_verdict": "...", "cot_judge_reasoning": "..."}'
    )


def extract_thinking_tokens(response) -> str:
    """Return concatenated thinking-token text from a generate_content response.

    Returns an empty string when thinking is disabled or no thought parts exist.
    """
    try:
        parts = response.candidates[0].content.parts
        thought_texts = [p.text for p in parts if p.thought is True and p.text]
        return "\n\n".join(thought_texts)
    except (IndexError, AttributeError):
        return ""


def evaluate_cot(client, model: str, system_prompt: str, text: str,
                 classification: str, chain_of_thought: str,
                 thinking: str = "") -> dict:
    reasoning_text = thinking if thinking else chain_of_thought
    reasoning_label = "Thinking Tokens" if thinking else "Chain of Thought"
    user_message = (
        f"## Original Text\n{text}\n\n"
        f"## Assigned Classification\n{classification}\n\n"
        f"## {reasoning_label}\n{reasoning_text}"
    )
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=COT_JUDGE_RESPONSE_SCHEMA,
                ),
            )
            result = json.loads(response.text)
            return {
                "cot_verdict": result["cot_verdict"],
                "cot_judge_reasoning": result["cot_judge_reasoning"],
            }
        except (json.JSONDecodeError, KeyError) as e:
            return {
                "cot_verdict": "Error",
                "cot_judge_reasoning": f"Failed to parse response: {e}",
            }
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  CoT judge retry {attempt + 1}/{max_retries} after error: {e}. "
                      f"Waiting {wait}s...")
                time.sleep(wait)
            else:
                return {
                    "cot_verdict": "Error",
                    "cot_judge_reasoning": f"Failed after {max_retries} retries: {e}",
                }


def classify_text(client, model: str, system_prompt: str, text: str,
                  thinking_budget: int = -1) -> dict:
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
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=thinking_budget,
                        include_thoughts=True,
                    ),
                ),
            )
            thinking = extract_thinking_tokens(response)
            result = json.loads(response.text)
            return {
                "classification": result["classification"],
                "chain_of_thought": result["chain_of_thought"],
                "thinking": thinking,
            }
        except (json.JSONDecodeError, KeyError) as e:
            return {
                "classification": "Error",
                "chain_of_thought": f"Failed to parse response: {e}",
                "thinking": "",
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
                    "thinking": "",
                }


def process_csv(input_path: str, output_path: str, rubric_path: str,
                model: str, client, cot_rubric_path: str | None = None,
                thinking_budget: int = -1) -> None:
    rubric_text = load_rubric(rubric_path)
    system_prompt = build_system_prompt(rubric_text)

    cot_system_prompt = None
    if cot_rubric_path is not None:
        cot_rubric_text = load_rubric(cot_rubric_path)
        cot_system_prompt = build_cot_judge_prompt(cot_rubric_text)

    with open(input_path, "r", newline="") as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)

    total = len(rows)
    results = []

    for i, row in enumerate(rows, start=1):
        unique_id = row["id"]
        text = row["text_to_evaluate"]
        target = row["target"]
        print(f"Processing row {i}/{total}...")
        result = classify_text(client, model, system_prompt, text,
                               thinking_budget=thinking_budget)
        output_row = {
            "id": unique_id,
            "target": target,
            "text_to_evaluate": text,
            "classification": result["classification"],
            "thinking": result["thinking"],
            "chain_of_thought": result["chain_of_thought"],
        }
        if cot_system_prompt is not None:
            cot_result = evaluate_cot(
                client, model, cot_system_prompt,
                text, result["classification"], result["chain_of_thought"],
                thinking=result["thinking"],
            )
            output_row["cot_verdict"] = cot_result["cot_verdict"]
            output_row["cot_judge_reasoning"] = cot_result["cot_judge_reasoning"]
        results.append(output_row)

    fieldnames = ["id", "target", "text_to_evaluate", "classification", "thinking", "chain_of_thought"]
    if cot_system_prompt is not None:
        fieldnames += ["cot_verdict", "cot_judge_reasoning"]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
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
    parser.add_argument("--cot-rubric", default=None,
                        help="Path to CoT judge rubric; enables the secondary judge when set")
    parser.add_argument("--thinking-budget", type=int, default=-1,
                        help=(
                            "Thinking token budget for Gemini extended thinking. "
                            "-1 = AUTOMATIC (model decides), 0 = disabled. "
                            "Positive integer = fixed budget. Default: -1."
                        ))
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set. Create a .env file or export it.")

    client = genai.Client(api_key=api_key)
    process_csv(args.input, args.output, args.rubric, args.model, client,
                cot_rubric_path=args.cot_rubric,
                thinking_budget=args.thinking_budget)


if __name__ == "__main__":
    main()
