"""
Results Export and Analysis Tool

Exports annotations and generates agreement analysis, statistics, and reports.
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
import argparse
import os


class ResultsExporter:
    """Export and analyze annotation results"""
    
    def __init__(self, db_path='annotation_queue.db'):
        """
        Initialize exporter
        
        Args:
            db_path: Path to SQLite annotation database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
    
    def export_assessments_csv(self, output_path='assessments_export.csv'):
        """
        Export all completed assessments to CSV
        
        Args:
            output_path: Path for output CSV file
            
        Returns:
            DataFrame with exported data
        """
        query = '''
            SELECT 
                id, target, classification, ai_verdict, human_verdict,
                verdict_match, confidence, time_spent_seconds, reviewer,
                classification_support, rubric_grounding, logical_consistency, 
                evidence_use, notes, completed_at
            FROM queue 
            WHERE status = "completed"
            ORDER BY completed_at
        '''
        
        df = pd.read_sql_query(query, self.conn)
        df.to_csv(output_path, index=False)
        print(f"\n✓ Exported {len(df)} assessments to: {output_path}")
        return df
    
    def agreement_analysis(self):
        """
        Analyze agreement between human and AI verdicts
        
        Returns:
            Dictionary with agreement metrics
        """
        query = '''
            SELECT human_verdict, ai_verdict, verdict_match, confidence 
            FROM queue 
            WHERE status = "completed"
        '''
        
        df = pd.read_sql_query(query, self.conn)
        
        if len(df) == 0:
            print("\n⚠️  No completed assessments yet.")
            return {}
        
        total = len(df)
        matches = df['verdict_match'].sum()
        accuracy = (matches / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 70)
        print("AGREEMENT ANALYSIS: Human vs AI Verdicts")
        print("=" * 70)
        print(f"\nTotal Assessments:      {total}")
        print(f"Matching Verdicts:      {matches:>3} ({accuracy:.1f}%)")
        print(f"Disagreements:          {total - matches:>3} ({100 - accuracy:.1f}%)")
        
        # Breakdown by verdict type
        print("\n" + "-" * 70)
        print("DISAGREEMENT BREAKDOWN:")
        print("-" * 70)
        
        disagreements = df[df['verdict_match'] == False]
        if len(disagreements) > 0:
            for idx, row in disagreements.iterrows():
                print(f"  AI: {row['ai_verdict']:20s} → Human: {row['human_verdict']:20s}")
        else:
            print("  (All verdicts match!)")
        
        # Confidence analysis
        print("\n" + "-" * 70)
        print("AVERAGE CONFIDENCE BY VERDICT MATCH:")
        print("-" * 70)
        avg_conf_match = df[df['verdict_match'] == True]['confidence'].mean()
        avg_conf_mismatch = df[df['verdict_match'] == False]['confidence'].mean()
        print(f"  When verdicts match:       {avg_conf_match:.2f} / 5.0")
        print(f"  When verdicts disagree:    {avg_conf_mismatch:.2f} / 5.0")
        
        return {
            'total': total,
            'matches': matches,
            'accuracy_pct': accuracy,
            'disagreements': total - matches
        }
    
    def rubric_dimension_stats(self):
        """Analyze dimension-by-dimension assessment patterns"""
        query = '''
            SELECT 
                classification_support, rubric_grounding, 
                logical_consistency, evidence_use
            FROM queue 
            WHERE status = "completed"
        '''
        
        df = pd.read_sql_query(query, self.conn)
        
        if len(df) == 0:
            print("\n⚠️  No completed assessments yet.")
            return
        
        dimensions = {
            'Classification Support': df['classification_support'],
            'Rubric Grounding': df['rubric_grounding'],
            'Logical Consistency': df['logical_consistency'],
            'Evidence Use': df['evidence_use']
        }
        
        print("\n" + "=" * 70)
        print("RUBRIC DIMENSION ASSESSMENT BREAKDOWN")
        print("=" * 70)
        
        for dim_name, dim_data in dimensions.items():
            print(f"\n{dim_name.upper()}:")
            print("-" * 70)
            counts = dim_data.value_counts()
            total = len(dim_data)
            
            for value in ['weak', 'adequate', 'strong']:
                count = counts.get(value, 0)
                pct = (count / total * 100) if total > 0 else 0
                bar = "█" * int(pct / 5)
                print(f"  {value:10s}: {count:3d} ({pct:5.1f}%) {bar}")
    
    def reviewer_stats(self):
        """Generate statistics by reviewer"""
        query = '''
            SELECT 
                reviewer, 
                COUNT(*) as assessments,
                ROUND(AVG(time_spent_seconds), 1) as avg_time_sec,
                ROUND(AVG(confidence), 2) as avg_confidence,
                SUM(CASE WHEN verdict_match = 1 THEN 1 ELSE 0 END) as matches,
                ROUND(100.0 * SUM(CASE WHEN verdict_match = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as agreement_pct
            FROM queue 
            WHERE status = "completed"
            GROUP BY reviewer
            ORDER BY assessments DESC
        '''
        
        df = pd.read_sql_query(query, self.conn)
        
        if len(df) == 0:
            print("\n⚠️  No completed assessments yet.")
            return
        
        print("\n" + "=" * 90)
        print("REVIEWER STATISTICS")
        print("=" * 90)
        
        print(f"\n{'Reviewer':<20} {'Assessments':<12} {'Avg Time':<12} {'Avg Conf':<12} {'Agreement':<12}")
        print("-" * 90)
        
        for _, row in df.iterrows():
            reviewer = row['reviewer'][:20]
            assessments = int(row['assessments'])
            avg_time = f"{row['avg_time_sec']:.0f}s"
            avg_conf = f"{row['avg_confidence']:.2f}/5"
            agreement = f"{row['agreement_pct']:.1f}%"
            
            print(f"{reviewer:<20} {assessments:<12} {avg_time:<12} {avg_conf:<12} {agreement:<12}")
        
        print("-" * 90)
        total_assessments = df['assessments'].sum()
        print(f"{'TOTAL':<20} {int(total_assessments):<12}")
    
    def disagreement_summary(self):
        """Generate detailed disagreement summary"""
        query = '''
            SELECT 
                id, target, classification, ai_verdict, human_verdict,
                confidence, notes, reviewer, completed_at
            FROM queue 
            WHERE status = "completed" AND verdict_match = 0
            ORDER BY completed_at DESC
        '''
        
        df = pd.read_sql_query(query, self.conn)
        
        if len(df) == 0:
            print("\n✓ Perfect agreement! No disagreements to report.")
            return
        
        print("\n" + "=" * 90)
        print(f"DISAGREEMENT DETAILS ({len(df)} cases)")
        print("=" * 90)
        
        for idx, row in df.iterrows():
            print(f"\nRecord ID: {row['id']}")
            print(f"  Accuracy:       {row['target']} (target) vs {row['classification']} (pred)")
            print(f"  AI Verdict:     {row['ai_verdict']}")
            print(f"  Human Verdict:  {row['human_verdict']}")
            print(f"  Confidence:     {row['confidence']}/5")
            print(f"  Reviewer:       {row['reviewer']}")
            if row['notes']:
                print(f"  Notes:          {row['notes']}")
    
    def export_summary_json(self, output_path='annotation_summary.json'):
        """
        Export comprehensive summary to JSON
        
        Args:
            output_path: Path for output JSON file
        """
        query_stats = 'SELECT COUNT(*) as total FROM queue'
        query_completed = 'SELECT COUNT(*) as completed FROM queue WHERE status = "completed"'
        query_pending = 'SELECT COUNT(*) as pending FROM queue WHERE status = "pending"'
        
        total = pd.read_sql_query(query_stats, self.conn).iloc[0, 0]
        completed = pd.read_sql_query(query_completed, self.conn).iloc[0, 0]
        pending = pd.read_sql_query(query_pending, self.conn).iloc[0, 0]
        
        query_agreement = '''
            SELECT 
                SUM(CASE WHEN verdict_match = 1 THEN 1 ELSE 0 END) as matches,
                COUNT(*) as total
            FROM queue WHERE status = "completed"
        '''
        agreement_data = pd.read_sql_query(query_agreement, self.conn).iloc[0]
        
        if agreement_data['total'] > 0:
            agreement_pct = agreement_data['matches'] / agreement_data['total'] * 100
        else:
            agreement_pct = 0
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'database': self.db_path,
            'queue_status': {
                'total_records': int(total),
                'completed': int(completed),
                'pending': int(pending),
                'completion_pct': round(completed / max(total, 1) * 100, 1)
            },
            'agreement': {
                'matching_verdicts': int(agreement_data['matches']) if agreement_data['total'] > 0 else 0,
                'total_assessments': int(agreement_data['total']),
                'agreement_pct': round(agreement_pct, 1)
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✓ Summary exported to: {output_path}")
        return summary
    
    def display_dashboard(self):
        """Display comprehensive dashboard"""
        self.clear_screen()
        print("\n" + "=" * 90)
        print("ANNOTATION ASSESSMENT DASHBOARD")
        print("=" * 90)
        
        # Queue status
        query = '''
            SELECT 
                (SELECT COUNT(*) FROM queue) as total,
                (SELECT COUNT(*) FROM queue WHERE status = "completed") as completed,
                (SELECT COUNT(*) FROM queue WHERE status = "pending") as pending
        '''
        status = pd.read_sql_query(query, self.conn).iloc[0]
        total = int(status['total'])
        completed = int(status['completed'])
        pending = int(status['pending'])
        
        print(f"\nQUEUE STATUS:")
        print(f"  Total:      {total}")
        print(f"  Completed:  {completed:>3} ({completed/max(total, 1)*100:.1f}%)")
        print(f"  Pending:    {pending:>3}")
        
        # Agreement
        self.agreement_analysis()
        
        # Reviewer stats
        self.reviewer_stats()
        
        # Dimension stats
        self.rubric_dimension_stats()
        
        print("\n" + "=" * 90)
    
    @staticmethod
    def clear_screen():
        """Clear terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Export and analyze CoT verdict annotation results'
    )
    parser.add_argument(
        '--action',
        choices=['dashboard', 'csv', 'json', 'agreement', 'disagreements', 'dimensions', 'reviewers'],
        default='dashboard',
        help='Action to perform (default: dashboard)'
    )
    parser.add_argument(
        '--db',
        default='annotation_queue.db',
        help='Path to annotation database'
    )
    parser.add_argument(
        '--output',
        help='Output file path (for csv/json actions)'
    )
    
    args = parser.parse_args()
    
    exporter = ResultsExporter(db_path=args.db)
    
    try:
        if args.action == 'dashboard':
            exporter.display_dashboard()
        elif args.action == 'csv':
            output_path = args.output or 'assessments_export.csv'
            exporter.export_assessments_csv(output_path)
        elif args.action == 'json':
            output_path = args.output or 'annotation_summary.json'
            exporter.export_summary_json(output_path)
        elif args.action == 'agreement':
            exporter.agreement_analysis()
        elif args.action == 'disagreements':
            exporter.disagreement_summary()
        elif args.action == 'dimensions':
            exporter.rubric_dimension_stats()
        elif args.action == 'reviewers':
            exporter.reviewer_stats()
    
    finally:
        exporter.close()


if __name__ == '__main__':
    main()
