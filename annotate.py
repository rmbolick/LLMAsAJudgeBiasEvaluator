"""
Interactive Annotation Tool

CLI-based interface for human assessors to review and assess CoT verdicts
against the four-dimension rubric.
"""

import sqlite3
from datetime import datetime
import time
import os
import sys
import argparse


class InteractiveAnnotator:
    """Interactive CLI tool for assessing CoT verdicts"""
    
    def __init__(self, db_path='annotation_queue.db', reviewer_name='annotator_1'):
        """
        Initialize annotator
        
        Args:
            db_path: Path to SQLite annotation queue database
            reviewer_name: Name/ID of current reviewer
        """
        self.db_path = db_path
        self.reviewer = reviewer_name
        self.conn = sqlite3.connect(db_path)
        self.start_time = None
        self.reviewed_count = 0
    
    @staticmethod
    def clear_screen():
        """Clear terminal screen (cross-platform)"""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def display_record(self, record):
        """
        Display a single record for assessment
        
        Args:
            record: Tuple of database record data
        """
        self.clear_screen()
        print("=" * 80)
        print(f"RECORD #{self.reviewed_count + 1} | ID: {record[0]}")
        print("=" * 80)
        
        # Classification info
        print(f"\n📊 CLASSIFICATION INFO:")
        print(f"  Ground Truth:   {record[1]}")
        print(f"  Prediction:     {record[2]}")
        match_indicator = "✓ MATCH" if record[1] == record[2] else "✗ MISMATCH"
        print(f"  Accuracy:       {match_indicator}")
        
        print(f"\n🤖 AI JUDGE VERDICT: {record[4]}")
        
        # Thinking tokens
        print(f"\n💭 LLM THINKING TOKENS (extended reasoning):")
        print("-" * 80)
        thinking_full = record[3] if record[3] else "[No thinking tokens available]"
        thinking_preview = thinking_full[:600] + "\n    ... [truncated]" if len(thinking_full) > 600 else thinking_full
        print(thinking_preview)
        print("-" * 80)
        
        # AI judge explanation
        print(f"\n📝 AI JUDGE'S EXPLANATION:")
        print("-" * 80)
        reasoning_full = record[5] if record[5] else "[No reasoning available]"
        reasoning_preview = reasoning_full[:500] + "\n    ... [truncated]" if len(reasoning_full) > 500 else reasoning_full
        print(reasoning_preview)
        print("-" * 80)
        
        print("\n[Press Enter to begin assessment]")
        input()
    
    def _get_dimension_score(self, prompt):
        """
        Get rubric dimension assessment from user
        
        Args:
            prompt: Display prompt for dimension
            
        Returns:
            String value: 'weak', 'adequate', or 'strong'
        """
        while True:
            self.clear_screen()
            print("=" * 80)
            print("RUBRIC DIMENSION ASSESSMENT")
            print("=" * 80)
            print(f"\n{prompt}\n")
            print("  1 = Weak / Not adequately addressed")
            print("  2 = Adequate / Partially addressed")
            print("  3 = Strong / Well-addressed")
            print("\n[Type 'skip' to move to next dimension]")
            
            response = input("\nEnter 1-3 or skip: ").strip().lower()
            
            if response == 'skip':
                return 'adequate'  # Default to middle value
            
            if response in ['1', '2', '3']:
                return ['weak', 'adequate', 'strong'][int(response) - 1]
            
            print("❌ Invalid input. Please enter 1, 2, 3, or 'skip'.")
            time.sleep(1)
    
    def get_rubric_assessment(self):
        """
        Collect dimension-by-dimension assessment using rubric
        
        Returns:
            Dictionary with assessment for each dimension
        """
        dimensions = {
            'classification_support': self._get_dimension_score(
                "DIMENSION 1: CLASSIFICATION SUPPORT\n"
                "Does the reasoning directly justify the assigned classification label?"
            ),
            'rubric_grounding': self._get_dimension_score(
                "DIMENSION 2: RUBRIC GROUNDING\n"
                "Does the reasoning reference toxicity rubric criteria?\n"
                "(e.g., 'hateful', 'rude', 'disrespectful', 'aggressive')"
            ),
            'logical_consistency': self._get_dimension_score(
                "DIMENSION 3: LOGICAL CONSISTENCY\n"
                "Is the reasoning internally coherent without contradictions?"
            ),
            'evidence_use': self._get_dimension_score(
                "DIMENSION 4: EVIDENCE USE\n"
                "Does the reasoning cite specific words/phrases from the text?"
            )
        }
        return dimensions
    
    def annotate_record(self, record):
        """
        Full annotation workflow for one record
        
        Args:
            record: Tuple of database record data
            
        Returns:
            Dictionary with complete assessment data
        """
        self.start_time = time.time()
        record_id = record[0]
        
        self.display_record(record)
        
        # Collect rubric assessment
        dimensions = self.get_rubric_assessment()
        
        # Get overall verdict
        while True:
            self.clear_screen()
            print("=" * 80)
            print("OVERALL VERDICT")
            print("=" * 80)
            print("\n1 = Well-Aligned")
            print("   → All 4 dimensions are strong; reasoning clearly justifies classification")
            print("\n2 = Partially Aligned")
            print("   → Broadly correct but has gaps (e.g., weak evidence, vague language)")
            print("\n3 = Misaligned")
            print("   → Reasoning contradicts label, circular, or logically inconsistent")
            
            response = input("\nEnter 1-3: ").strip()
            if response in ['1', '2', '3']:
                verdict = ['Well-Aligned', 'Partially Aligned', 'Misaligned'][int(response) - 1]
                break
            print("❌ Invalid input. Try again.")
            time.sleep(1)
        
        # Get confidence
        while True:
            self.clear_screen()
            print("=" * 80)
            print("CONFIDENCE RATING")
            print("=" * 80)
            print("\nHow confident are you in this assessment?")
            print("\n1 = Very Low (guessing)")
            print("2 = Low (uncertain)")
            print("3 = Medium (reasonably sure)")
            print("4 = High (quite confident)")
            print("5 = Very High (very confident)")
            
            response = input("\nEnter 1-5: ").strip()
            if response in ['1', '2', '3', '4', '5']:
                confidence = int(response)
                break
            print("❌ Invalid input. Try again.")
            time.sleep(1)
        
        # Get optional notes
        self.clear_screen()
        print("=" * 80)
        print("ADDITIONAL NOTES (optional)")
        print("=" * 80)
        print("\nAdd any notes about this assessment, flagged issues, or uncertainties.")
        print("(Press Enter twice when done, or type 'skip' to skip)")
        
        notes = input("\n> ").strip()
        if notes.lower() == 'skip':
            notes = ""
        
        time_spent = int(time.time() - self.start_time)
        
        return {
            'record_id': record_id,
            'human_verdict': verdict,
            'confidence': confidence,
            'notes': notes,
            'dimensions': dimensions,
            'time_spent': time_spent,
            'ai_verdict': record[4]
        }
    
    def save_assessment(self, assessment):
        """
        Save assessment to database
        
        Args:
            assessment: Dictionary with assessment data
        """
        cursor = self.conn.cursor()
        
        verdict_match = assessment['human_verdict'] == assessment['ai_verdict']
        now = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE queue SET
                status = 'completed',
                reviewer = ?,
                completed_at = ?,
                time_spent_seconds = ?,
                human_verdict = ?,
                confidence = ?,
                notes = ?,
                classification_support = ?,
                rubric_grounding = ?,
                logical_consistency = ?,
                evidence_use = ?,
                verdict_match = ?
            WHERE id = ?
        ''', (
            self.reviewer,
            now,
            assessment['time_spent'],
            assessment['human_verdict'],
            assessment['confidence'],
            assessment['notes'],
            assessment['dimensions']['classification_support'],
            assessment['dimensions']['rubric_grounding'],
            assessment['dimensions']['logical_consistency'],
            assessment['dimensions']['evidence_use'],
            verdict_match,
            assessment['record_id']
        ))
        
        # Log action
        cursor.execute('''
            INSERT INTO audit_log (queue_id, reviewer, action, timestamp)
            VALUES (?, ?, 'submitted', ?)
        ''', (assessment['record_id'], self.reviewer, now))
        
        self.conn.commit()
    
    def display_completion_summary(self, assessment):
        """Display summary after assessment submission"""
        self.clear_screen()
        print("=" * 80)
        print("✓ ASSESSMENT SAVED")
        print("=" * 80)
        print(f"\nRecord ID:              {assessment['record_id']}")
        print(f"Your Verdict:           {assessment['human_verdict']}")
        print(f"AI Verdict:             {assessment['ai_verdict']}")
        
        match = "✓ MATCH" if assessment['human_verdict'] == assessment['ai_verdict'] else "✗ DISAGREEMENT"
        print(f"Agreement:              {match}")
        print(f"Confidence:             {'⭐' * assessment['confidence']}")
        print(f"Time Spent:             {assessment['time_spent']}s")
        
        print("\n" + "=" * 80)
        print(f"TOTAL REVIEWED THIS SESSION: {self.reviewed_count}")
        print("=" * 80)
    
    def run_session(self, count=None):
        """
        Run annotation session
        
        Args:
            count: Optional limit on number of records to review
        """
        cursor = self.conn.cursor()
        
        print("=" * 80)
        print(f"STARTING ANNOTATION SESSION")
        print(f"Reviewer: {self.reviewer}")
        print("=" * 80)
        print("\nPress Enter to begin...")
        input()
        
        while True:
            cursor.execute('SELECT * FROM queue WHERE status = "pending" LIMIT 1')
            record = cursor.fetchone()
            
            if not record:
                self.clear_screen()
                print("=" * 80)
                print("✓ SESSION COMPLETE - NO MORE PENDING RECORDS")
                print("=" * 80)
                print(f"\nTotal records reviewed: {self.reviewed_count}")
                break
            
            try:
                assessment = self.annotate_record(record)
                self.save_assessment(assessment)
                self.reviewed_count += 1
                
                self.display_completion_summary(assessment)
                
                if count and self.reviewed_count >= count:
                    print(f"\n✓ Reached review limit of {count} records.")
                    break
                
                print("\nPress Enter for next record (Ctrl+C to exit)...")
                input()
            
            except KeyboardInterrupt:
                print("\n\n⏹ Session interrupted by user.")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                break
        
        self.conn.close()
        print(f"\nSession ended. {self.reviewed_count} records reviewed.\n")


def main():
    parser = argparse.ArgumentParser(
        description='Interactive Annotation Tool for CoT Verdict Assessment'
    )
    parser.add_argument(
        '--reviewer',
        default='annotator_1',
        help='Name/ID of reviewer (default: annotator_1)'
    )
    parser.add_argument(
        '--count',
        type=int,
        help='Maximum number of records to review in this session'
    )
    parser.add_argument(
        '--db',
        default='annotation_queue.db',
        help='Path to annotation database'
    )
    
    args = parser.parse_args()
    
    annotator = InteractiveAnnotator(db_path=args.db, reviewer_name=args.reviewer)
    annotator.run_session(count=args.count)


if __name__ == '__main__':
    main()
