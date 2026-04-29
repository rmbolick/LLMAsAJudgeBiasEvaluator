# Annotation Queue System - Quick Start Guide

## Overview

The annotation queue system allows human reviewers to assess AI-generated CoT verdicts against a four-dimension rubric. All tools use only installed packages (pandas, sqlite3, json).

**Three main components:**
- `annotation_queue.py` — Initialize and manage the queue
- `annotate.py` — Interactive CLI for reviewers
- `export_results.py` — Generate reports and analysis

---

## Getting Started

### Step 1: Initialize the Queue

Initialize the annotation queue from your processed data:

```bash
python annotation_queue.py --action init
```

This creates `annotation_queue.db` and loads all records from `sample_for_annotations.csv` (default).

**To use a different input file:**
```bash
python annotation_queue.py --action init --csv "path/to/your/file.csv"
```

**Output example:**
```
✓ Queue initialized with 50 records
  Database: annotation_queue.db
```

### Step 2: Check Queue Status

View current queue statistics at any time:

```bash
python annotation_queue.py --action stats
```

**Output shows:**
- Total records
- Completed / Pending / In-Progress counts
- Number of active reviewers
- Agreement rate (once assessments are complete)

---

## Reviewing Records

### Start an Annotation Session

Begin reviewing records as a specific reviewer:

```bash
python annotate.py --reviewer "jane_doe"
```

**Optional flags:**
- `--reviewer NAME` — Set reviewer name/ID (default: annotator_1)
- `--count N` — Review only N records before exiting (default: unlimited)
- `--db PATH` — Custom database path (default: annotation_queue.db)
- `--csv PATH` — Custom input CSV file (default: sample_for_annotations.csv)

### What Happens During Review

**Persistent Data Context:** At the top of each screen, you'll see a compact summary of the core data:
- **id** — Record identifier
- **target** — Ground truth toxicity label
- **classification** — Model's predicted label
- **thinking** — Full LLM reasoning (untruncated, wrapped to terminal width)
- **text_to_evaluate** — The original text being evaluated
- **cot_verdict** — AI judge's verdict (Well-Aligned / Partially Aligned / Misaligned)

This data context persists throughout all questions so you have full visibility without needing to reference back.

**For each record, you'll assess:**

1. **Classification Support**
   - Does the reasoning justify the label?

2. **Rubric Grounding**
   - Does it reference toxicity criteria?

3. **Logical Consistency**
   - Is reasoning internally coherent?

4. **Evidence Use**
   - Does it cite specific text evidence?

5. **Rubric Assessment** (4 dimensions, enter 1-3 for each)
   - **Classification Support:** Does reasoning justify the label?
   - **Rubric Grounding:** Does it reference toxicity criteria?
   - **Logical Consistency:** Is reasoning internally coherent?
   - **Evidence Use:** Does it cite specific text evidence?

   **Input options:**
   ```
   1 = Weak / Not adequately addressed
   2 = Adequate / Partially addressed
   3 = Strong / Well-addressed
   skip = Use default (adequate)
   ```

6. **Overall Verdict** (enter 1-3)
   
   After reviewing all dimensions, assess the overall alignment:
   ```
   1 = Well-Aligned       (all 4 dimensions strong, clearly justifies classification)
   2 = Partially Aligned  (broadly correct but has gaps)
   3 = Misaligned         (reasoning contradicts label or is inconsistent)
   ```

7. **Confidence** (enter 1-5)
   ```
   1 = Very Low     (guessing)
   2 = Low          (uncertain)
   3 = Medium       (reasonably sure)
   4 = High         (quite confident)
   5 = Very High    (very confident)
   ```

8. **Optional Notes**
   - Add any observations, flagged issues, or uncertainties

### Example Session

```bash
python annotate.py --reviewer "alice" --count 5
```

This runs alice through 5 records, then exits.

**Keyboard shortcuts:**
- `Ctrl+C` — Exit session at any time (progress is saved)
- `Enter` — Move to next question or next record
- `skip` — Use default value for rubric dimension

---

## Analyzing Results

### View Dashboard (All Statistics)

```bash
python export_results.py --action dashboard
```

Shows:
- Queue status (total, completed, pending)
- Agreement analysis (human vs AI verdicts)
- Reviewer statistics
- Rubric dimension breakdown

### Export Assessments to CSV

```bash
python export_results.py --action csv
```

Outputs: `assessments_export.csv` with all assessment data

**Columns include:**
- id, target, classification
- ai_verdict, human_verdict, verdict_match
- confidence, time_spent_seconds, reviewer
- classification_support, rubric_grounding, logical_consistency, evidence_use
- notes, completed_at

### Export Summary to JSON

```bash
python export_results.py --action json
```

Outputs: `annotation_summary.json` with high-level metrics

### Agreement Analysis

```bash
python export_results.py --action agreement
```

Shows:
- Total assessments and matching verdicts
- Disagreement breakdown
- Confidence patterns

### Disagreement Report

```bash
python export_results.py --action disagreements
```

Lists all cases where human verdict ≠ AI verdict

### Rubric Dimension Breakdown

```bash
python export_results.py --action dimensions
```

Shows distribution of weak/adequate/strong ratings by dimension

### Reviewer Statistics

```bash
python export_results.py --action reviewers
```

Shows per-reviewer metrics (count, avg time, confidence, agreement %)

---

## Multi-Reviewer Workflow

### Parallel Review Sessions

Multiple reviewers can work simultaneously:

```bash
# Terminal 1 - Alice reviews
python annotate.py --reviewer "alice"

# Terminal 2 - Bob reviews
python annotate.py --reviewer "bob"

# Terminal 3 - Carol reviews
python annotate.py --reviewer "carol"
```

The database queue automatically handles concurrent access. Each reviewer gets assigned the next pending record.

### Check Overall Progress

```bash
python annotation_queue.py --action stats
```

Displays progress across all reviewers in real-time.

---

## Data Flow

```
Input: sample_for_annotations.csv (default) or custom CSV
  ↓
Initialize: python annotation_queue.py --action init
  ↓ Creates: annotation_queue.db
  ↓
Review: python annotate.py --reviewer "alice"
  ↓ Displays: Full untruncated data + persistent context
  ↓ Updates: queue table, audit_log table
  ↓
Analyze: python export_results.py --action dashboard
  ↓ Generates: CSV, JSON, reports
```

---

## Database Schema

### queue table
- **id** — Record identifier (PRIMARY KEY)
- **target, classification** — Ground truth and prediction
- **thinking** — LLM reasoning tokens
- **ai_verdict, ai_reasoning** — AI judge verdict and explanation
- **status** — pending / completed / in_progress / skipped
- **reviewer** — Name of reviewer
- **human_verdict** — Reviewer's verdict
- **confidence** — 1-5 rating
- **classification_support, rubric_grounding, logical_consistency, evidence_use** — Dimension ratings
- **verdict_match** — Boolean (human_verdict == ai_verdict)
- **completed_at** — Timestamp
- **time_spent_seconds** — Time to review record

### audit_log table
- Tracks all actions (viewed, submitted, skipped)
- Timestamp for each action
- Reviewer attribution

---

## Troubleshooting

### Queue won't initialize
```bash
# Delete existing database and try again
rm annotation_queue.db
python annotation_queue.py --action init
```

### Session crashed mid-record
- Progress is saved only upon **submission**
- Interrupted records return to "pending" status
- Simply restart the session to continue

### Need to review specific records only
- Edit `annotation_queue.py` to add a `--filter` flag (currently not implemented)
- Alternative: Export CSV, filter manually, reload

### Want to change a verdict
- Currently no edit feature (would need UI enhancement)
- Workaround: Delete the record from database and re-review

---

## Performance Notes

- **Database:** SQLite can handle ~10,000 records per reviewer efficiently
- **Session length:** Reviewers typically assess 20-40 records/hour (depending on record complexity)
- **Concurrent reviewers:** SQLite supports up to ~5-10 concurrent writers; use PostgreSQL for larger teams

---

## Next Steps

1. **Initialize queue** from your Output_Analysis_Data.csv
2. **Start reviewing** with one or more reviewers
3. **Monitor progress** with `--action stats`
4. **Export results** when complete
5. **Analyze agreement** patterns to identify labeling difficulties

Happy annotating! 🎯
