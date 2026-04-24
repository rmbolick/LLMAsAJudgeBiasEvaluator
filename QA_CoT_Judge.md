# Manual QA Guide: CoT Alignment Judge (Phase 5.6)

## Prerequisites

- `GEMINI_API_KEY` set in a `.env` file at the project root
- Dependencies installed: `pip install -r requirements.txt`
- All unit tests passing: `pytest tests/ -v`

Run all steps from the project root (`LLMAsAJudgeBiasEvaluator/`).

---

## Step 1 — Confirm unit tests still pass

```bash
pytest tests/ -v
```

Expected: `12 passed` with no failures or warnings.

---

## Step 2 — Run the pipeline WITH the CoT judge

```bash
python classifier.py \
  --input Inputs/input.csv \
  --output Outputs/output_with_cot.csv \
  --cot-rubric CoT_Judge_Rubric.md
```

Expected console output: 8 lines of `Processing row N/8...` followed by `Done. Output written to Outputs/output_with_cot.csv`.

---

## Step 3 — Verify output structure

Open `Outputs/output_with_cot.csv` in a spreadsheet or run:

```bash
python3 -c "
import csv
with open('Outputs/output_with_cot.csv') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    print('Columns:', reader.fieldnames)
    print('Row count:', len(rows))
"
```

Expected:
- **Columns**: `text_to_evaluate`, `classification`, `chain_of_thought`, `cot_verdict`, `cot_judge_reasoning`
- **Row count**: 8

---

## Step 4 — Verify verdict values are valid

```bash
python3 -c "
import csv
valid = {'Well-Aligned', 'Partially Aligned', 'Misaligned'}
with open('Outputs/output_with_cot.csv') as f:
    for i, row in enumerate(csv.DictReader(f), 1):
        v = row['cot_verdict']
        status = 'OK' if v in valid else 'INVALID'
        print(f'Row {i}: {v} [{status}]')
"
```

Expected: all 8 rows print `OK`.

---

## Step 5 — Spot-check known cases

Review these rows in `Outputs/output_with_cot.csv` and assess whether the CoT judge's verdict is reasonable:

| Text | Expected classification | Expected verdict |
|---|---|---|
| `haha you guys are a bunch of losers.` | Toxic | Well-Aligned (CoT cites "losers" as a direct insult) |
| `ur a sh*tty comment.` | Toxic | Well-Aligned (CoT cites derogatory term) |
| `FFFFUUUUUUUUUUUUUUU` | Not Toxic | Well-Aligned (CoT notes no personal attack) |
| `It was a great show...` | Not Toxic | Well-Aligned (CoT notes positive sentiment) |

If any verdict is `Misaligned` or `Partially Aligned` on the above, read the `cot_judge_reasoning` column to assess whether the secondary judge's explanation is coherent and defensible.

---

## Step 6 — Confirm backward compatibility (no CoT flag)

```bash
python classifier.py \
  --input Inputs/input.csv \
  --output Outputs/output_no_cot.csv
```

Then verify the output has only 3 columns:

```bash
python3 -c "
import csv
with open('Outputs/output_no_cot.csv') as f:
    reader = csv.DictReader(f)
    list(reader)
    print('Columns:', reader.fieldnames)
"
```

Expected: `['text_to_evaluate', 'classification', 'chain_of_thought']` — no `cot_verdict` or `cot_judge_reasoning`.

---

## Step 7 — Confirm `.env` is not committed

```bash
git status
```

Verify `.env` does not appear in the output. If it does, do not commit and add it to `.gitignore`.

---

## Pass Criteria

| Check | Pass condition |
|---|---|
| Unit tests | 12 passed, 0 failed |
| Output file created | `Outputs/output_with_cot.csv` exists |
| Column count | 5 columns present |
| Row count | 8 data rows |
| Verdict values | All 8 are one of: Well-Aligned, Partially Aligned, Misaligned |
| Spot-check coherence | Judge reasoning is logical and references rubric criteria |
| Backward compatibility | No-flag run produces 3-column output only |
| Secret hygiene | `.env` not staged or committed |
