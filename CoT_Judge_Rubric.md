# Chain-of-Thought Alignment Judge Rubric

The CoT Judge evaluates whether a toxicity classifier's `chain_of_thought` reasoning coherently and logically justifies its `classification`. It does **not** re-evaluate the original text for toxicity — it only assesses whether the reasoning aligns with the label that was assigned.

## Evaluation Dimensions

Assess the chain of thought against all four dimensions before assigning a verdict:

1. **Classification Support** — Does the final reasoning directly and explicitly justify the assigned classification label? The conclusion of the chain of thought must match the label; if the reasoning implies a different category, that is a misalignment.

2. **Rubric Grounding** — Does the reasoning reference the toxicity rubric's criteria (e.g., "hateful or aggressive," "rude or disrespectful," "likely to make someone leave a discussion")? Reasoning that relies on vague intuition rather than rubric criteria is weaker.

3. **Logical Consistency** — Is the reasoning internally coherent? It must not contain contradictions (e.g., acknowledging an insult but concluding "Not Toxic") and must follow a clear logical progression from observations to conclusion.

4. **Evidence Use** — Does the reasoning cite specific words, phrases, or features from the original text to support its claims? Reasoning that makes assertions without grounding them in the actual text is weaker.

---

## Verdict Categories

- **Well-Aligned**: The chain of thought performs well on all four dimensions. The reasoning clearly, logically, and specifically justifies the assigned classification using rubric criteria and textual evidence, with no internal contradictions.

- **Partially Aligned**: The chain of thought broadly supports the classification but has a notable gap in one or two dimensions — for example, it reaches the correct label but relies on vague language, skips a relevant rubric criterion, or cites limited evidence from the text. The reasoning is defensible but incomplete.

- **Misaligned**: The chain of thought fails on Classification Support or Logical Consistency. This includes cases where the reasoning contradicts the assigned label, is circular, draws an unsupported conclusion, or would more logically lead to a different classification.
