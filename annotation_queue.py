"""
Annotation Queue Manager

Initializes SQLite queue from Output_Analysis_Data.csv for human assessment of CoT verdicts.
Provides queue statistics and management.
"""

import sqlite3
import pandas as pd
from datetime import datetime
import argparse


class AnnotationQueue:
    """Manages SQLite-based annotation queue for CoT verdict assessment"""
    
    def __init__(self, db_path='annotation_queue.db', csv_path='Output_Analysis_Data.csv'):
        """
        Initialize queue manager
        
        Args:
            db_path: Path to SQLite database file
            csv_path: Path to source CSV data
        """
        self.db_path = db_path
        self.csv_path = csv_path
        self.conn = sqlite3.connect(db_path)
    
    def initialize_queue(self):
        """Load CSV data into SQLite queue and create schema"""
        df = pd.read_csv(self.csv_path)
        
        cursor = self.conn.cursor()
        
        # Create queue table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queue (
                id TEXT PRIMARY KEY,
                target TEXT,
                classification TEXT,
                thinking TEXT,
                ai_verdict TEXT,
                ai_reasoning TEXT,
                
                status TEXT DEFAULT 'pending',
                reviewer TEXT,
                assigned_at TEXT,
                completed_at TEXT,
                time_spent_seconds INTEGER,
                
                human_verdict TEXT,
                confidence INTEGER,
                notes TEXT,
                
                classification_support TEXT,
                rubric_grounding TEXT,
                logical_consistency TEXT,
                evidence_use TEXT,
                
                verdict_match BOOLEAN
            )
        ''')
        
        # Create audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue_id TEXT,
                reviewer TEXT,
                action TEXT,
                timestamp TEXT,
                FOREIGN KEY (queue_id) REFERENCES queue(id)
            )
        ''')
        
        # Insert records from CSV
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR IGNORE INTO queue 
                (id, target, classification, thinking, ai_verdict, ai_reasoning)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(row['id']),
                row['target'],
                row['classification'],
                row['thinking'],
                row['cot_verdict'],
                row['cot_judge_reasoning']
            ))
        
        self.conn.commit()
        print(f"✓ Queue initialized with {len(df)} records")
        print(f"  Database: {self.db_path}")
    
    def get_next_record(self, status='pending'):
        """
        Get next unreviewed record
        
        Args:
            status: Filter by queue status
            
        Returns:
            Tuple of record data or None if no records available
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM queue WHERE status = ? LIMIT 1
        ''', (status,))
        return cursor.fetchone()
    
    def get_stats(self):
        """
        Get queue statistics
        
        Returns:
            Dictionary with total, completed, pending, and reviewer counts
        """
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM queue')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM queue WHERE status = "completed"')
        completed = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM queue WHERE status = "pending"')
        pending = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM queue WHERE status = "in_progress"')
        in_progress = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT reviewer) FROM queue WHERE status = "completed"')
        reviewers = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM queue 
            WHERE status = "completed" AND verdict_match = 1
        ''')
        matching = cursor.fetchone()[0]
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'in_progress': in_progress,
            'reviewers': reviewers,
            'matching_verdicts': matching
        }
    
    def display_stats(self):
        """Display formatted queue statistics"""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("ANNOTATION QUEUE STATISTICS")
        print("=" * 60)
        print(f"Total Records:      {stats['total']}")
        print(f"Completed:          {stats['completed']:>3} ({stats['completed']/max(stats['total'], 1)*100:.1f}%)")
        print(f"Pending:            {stats['pending']:>3}")
        print(f"In Progress:        {stats['in_progress']:>3}")
        print(f"Active Reviewers:   {stats['reviewers']}")
        
        if stats['completed'] > 0:
            match_pct = stats['matching_verdicts'] / stats['completed'] * 100
            print(f"Agreement Rate:     {match_pct:.1f}% ({stats['matching_verdicts']}/{stats['completed']})")
        
        print("=" * 60 + "\n")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Annotation Queue Manager for CoT Verdict Assessment'
    )
    parser.add_argument(
        '--action',
        choices=['init', 'stats', 'reset'],
        default='stats',
        help='Action to perform'
    )
    parser.add_argument(
        '--db',
        default='annotation_queue.db',
        help='Path to annotation database'
    )
    parser.add_argument(
        '--csv',
        default='Output_Analysis/Output_Analysis_Data.csv',
        help='Path to input CSV file'
    )
    
    args = parser.parse_args()
    
    queue = AnnotationQueue(db_path=args.db, csv_path=args.csv)
    
    if args.action == 'init':
        queue.initialize_queue()
        queue.display_stats()
    elif args.action == 'stats':
        queue.display_stats()
    elif args.action == 'reset':
        print("⚠️  Reset not yet implemented. Use '--action init' to reinitialize.")
    
    queue.close()


if __name__ == '__main__':
    main()
