import csv
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from classifier import (
    build_cot_judge_prompt,
    build_system_prompt,
    classify_text,
    evaluate_cot,
    process_csv,
)

VALID_CLASSIFICATIONS = {"Very Toxic", "Toxic", "Hard to Say", "Not Toxic"}


# --- Helpers ---

def _make_mock_client(response_text):
    """Return a mock client whose generate_content returns the given text."""
    client = MagicMock()
    response = MagicMock()
    response.text = response_text
    client.models.generate_content.return_value = response
    return client


# --- Tests ---

def test_build_system_prompt():
    rubric = "- Very Toxic: hateful\n- Not Toxic: fine"
    prompt = build_system_prompt(rubric)
    assert "Very Toxic" in prompt
    assert "Not Toxic" in prompt
    assert rubric in prompt
    assert "JSON" in prompt or "json" in prompt.lower()
    assert "chain_of_thought" in prompt


def test_classify_text_valid_response():
    payload = json.dumps({
        "classification": "Toxic",
        "chain_of_thought": "The text contains rude language."
    })
    client = _make_mock_client(payload)

    result = classify_text(client, "gemini-2.5-flash", "system prompt", "some text")

    assert result["classification"] == "Toxic"
    assert result["chain_of_thought"] == "The text contains rude language."


def test_classify_text_invalid_json():
    client = _make_mock_client("This is not JSON at all")

    result = classify_text(client, "gemini-2.5-flash", "system prompt", "some text")

    assert result["classification"] == "Error"
    assert "Failed to parse" in result["chain_of_thought"]


@patch("classifier.time.sleep", return_value=None)
def test_classify_text_retry_on_rate_limit(mock_sleep):
    client = MagicMock()

    success_response = MagicMock()
    success_response.text = json.dumps({
        "classification": "Not Toxic",
        "chain_of_thought": "Nothing harmful here."
    })

    client.models.generate_content.side_effect = [
        Exception("429 Resource exhausted"),
        success_response,
    ]

    result = classify_text(client, "gemini-2.5-flash", "system prompt", "hello")

    assert result["classification"] == "Not Toxic"
    assert client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once()


def test_process_csv_end_to_end():
    payload = json.dumps({
        "classification": "Not Toxic",
        "chain_of_thought": "Seems fine."
    })
    client = _make_mock_client(payload)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.csv")
        output_path = os.path.join(tmpdir, "output.csv")
        rubric_path = os.path.join(tmpdir, "rubric.md")

        with open(input_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["text_to_evaluate"])
            writer.writerow(["This is nice."])
            writer.writerow(["You are terrible."])

        with open(rubric_path, "w") as f:
            f.write("- Not Toxic: fine\n- Very Toxic: hateful\n")

        process_csv(input_path, output_path, rubric_path, "gemini-2.5-flash", client)

        assert os.path.exists(output_path)

        with open(output_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert set(reader.fieldnames) == {
            "text_to_evaluate", "classification", "chain_of_thought"
        }
        for row in rows:
            assert row["classification"] == "Not Toxic"
            assert row["chain_of_thought"] == "Seems fine."


def test_classification_values():
    """Verify every valid enum value is accepted and returned correctly."""
    for label in VALID_CLASSIFICATIONS:
        payload = json.dumps({
            "classification": label,
            "chain_of_thought": f"Classified as {label}."
        })
        client = _make_mock_client(payload)
        result = classify_text(client, "gemini-2.5-flash", "system prompt", "text")
        assert result["classification"] == label
        assert result["classification"] in VALID_CLASSIFICATIONS


VALID_COT_VERDICTS = {"Well-Aligned", "Partially Aligned", "Misaligned"}


# --- CoT Judge Tests ---

def test_build_cot_judge_prompt():
    rubric = "- Well-Aligned: clear reasoning\n- Misaligned: contradicts label"
    prompt = build_cot_judge_prompt(rubric)
    assert rubric in prompt
    assert "Well-Aligned" in prompt
    assert "Partially Aligned" in prompt
    assert "Misaligned" in prompt
    assert "JSON" in prompt or "json" in prompt.lower()
    assert "cot_judge_reasoning" in prompt


def test_evaluate_cot_valid_response():
    payload = json.dumps({
        "cot_verdict": "Well-Aligned",
        "cot_judge_reasoning": "The reasoning clearly supports the label."
    })
    client = _make_mock_client(payload)

    result = evaluate_cot(
        client, "gemini-2.5-flash", "system prompt",
        "some text", "Toxic", "The text is rude."
    )

    assert result["cot_verdict"] == "Well-Aligned"
    assert result["cot_judge_reasoning"] == "The reasoning clearly supports the label."


def test_evaluate_cot_invalid_json():
    client = _make_mock_client("This is not JSON at all")

    result = evaluate_cot(
        client, "gemini-2.5-flash", "system prompt",
        "some text", "Toxic", "The text is rude."
    )

    assert result["cot_verdict"] == "Error"
    assert "Failed to parse" in result["cot_judge_reasoning"]


@patch("classifier.time.sleep", return_value=None)
def test_evaluate_cot_retry_on_error(mock_sleep):
    client = MagicMock()

    success_response = MagicMock()
    success_response.text = json.dumps({
        "cot_verdict": "Partially Aligned",
        "cot_judge_reasoning": "Reasoning is mostly sound but vague."
    })

    client.models.generate_content.side_effect = [
        Exception("503 Service unavailable"),
        success_response,
    ]

    result = evaluate_cot(
        client, "gemini-2.5-flash", "system prompt",
        "some text", "Not Toxic", "Nothing harmful here."
    )

    assert result["cot_verdict"] == "Partially Aligned"
    assert client.models.generate_content.call_count == 2
    mock_sleep.assert_called_once()


def test_process_csv_with_cot_judge():
    tox_payload = json.dumps({
        "classification": "Toxic",
        "chain_of_thought": "Contains an insult."
    })
    cot_payload = json.dumps({
        "cot_verdict": "Well-Aligned",
        "cot_judge_reasoning": "Reasoning directly supports the Toxic label."
    })

    client = MagicMock()
    tox_response = MagicMock()
    tox_response.text = tox_payload
    cot_response = MagicMock()
    cot_response.text = cot_payload
    client.models.generate_content.side_effect = [
        tox_response, cot_response,
        tox_response, cot_response,
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.csv")
        output_path = os.path.join(tmpdir, "output.csv")
        rubric_path = os.path.join(tmpdir, "rubric.md")
        cot_rubric_path = os.path.join(tmpdir, "cot_rubric.md")

        with open(input_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["text_to_evaluate"])
            writer.writerow(["You are a loser."])
            writer.writerow(["Suck it."])

        with open(rubric_path, "w") as f:
            f.write("- Toxic: rude\n- Not Toxic: fine\n")

        with open(cot_rubric_path, "w") as f:
            f.write("- Well-Aligned: clear reasoning\n- Misaligned: contradicts label\n")

        process_csv(input_path, output_path, rubric_path, "gemini-2.5-flash",
                    client, cot_rubric_path=cot_rubric_path)

        with open(output_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

    assert len(rows) == 2
    assert set(fieldnames) == {
        "text_to_evaluate", "classification", "chain_of_thought",
        "cot_verdict", "cot_judge_reasoning",
    }
    for row in rows:
        assert row["classification"] == "Toxic"
        assert row["cot_verdict"] == "Well-Aligned"
        assert row["cot_judge_reasoning"] == "Reasoning directly supports the Toxic label."


def test_process_csv_without_cot_judge():
    payload = json.dumps({
        "classification": "Not Toxic",
        "chain_of_thought": "Seems fine."
    })
    client = _make_mock_client(payload)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.csv")
        output_path = os.path.join(tmpdir, "output.csv")
        rubric_path = os.path.join(tmpdir, "rubric.md")

        with open(input_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["text_to_evaluate"])
            writer.writerow(["This is nice."])

        with open(rubric_path, "w") as f:
            f.write("- Not Toxic: fine\n")

        process_csv(input_path, output_path, rubric_path, "gemini-2.5-flash", client)

        with open(output_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

    assert len(rows) == 1
    assert set(fieldnames) == {"text_to_evaluate", "classification", "chain_of_thought"}
    assert "cot_verdict" not in fieldnames
    assert "cot_judge_reasoning" not in fieldnames
