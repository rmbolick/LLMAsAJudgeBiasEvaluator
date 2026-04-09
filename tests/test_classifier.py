import csv
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from classifier import build_system_prompt, classify_text, process_csv

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
