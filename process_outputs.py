"""
Process LLM judge outputs and generate binary classification confusion matrix.

This script transforms raw LLM output data into binary classification format:
- Target (ground truth): 0.0 → "Not Toxic", all others → "Toxic"
- Classification (prediction): "Not Toxic" stays, all others → "Toxic"

Outputs:
- Processed data CSV: Output_Analysis/Output_Analysis_Data.csv
- Confusion matrix visualization: Output_Analysis/confusion_matrix.png
- Classification metrics: Output_Analysis/confusion_matrix_metrics.txt
"""

import os
from pathlib import Path
from typing import Tuple

import pandas as pd
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt
import seaborn as sns


def load_output_data(csv_path: str) -> pd.DataFrame:
    """
    Load output CSV file.
    
    Args:
        csv_path: Path to the output.csv file
        
    Returns:
        DataFrame with columns: id, target, classification
        
    Raises:
        FileNotFoundError: If CSV file does not exist
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    return df[['id', 'target', 'classification']].copy()


def map_target_to_binary(target_value: float) -> str:
    """
    Map target (ground truth) value to binary classification.
    
    Args:
        target_value: Numeric toxicity score
        
    Returns:
        "Not Toxic" if value is 0.0, "Toxic" otherwise
    """
    if target_value == 0.0:
        return "Not Toxic"
    else:
        return "Toxic"


def map_classification_to_binary(classification_value: str) -> str:
    """
    Map classification (prediction) value to binary classification.
    
    Args:
        classification_value: Categorical classification value
        
    Returns:
        "Not Toxic" if value is "Not Toxic", "Toxic" otherwise
    """
    if classification_value == "Not Toxic":
        return "Not Toxic"
    else:
        return "Toxic"


def process_and_save_data(input_path: str, output_path: str) -> pd.DataFrame:
    """
    Load, process, and save binary classification data.
    
    Args:
        input_path: Path to input output.csv file
        output_path: Path to save processed data
        
    Returns:
        Processed DataFrame with binary mapped values
    """
    # Load data
    df = load_output_data(input_path)
    
    # Apply binary mapping
    df['target'] = df['target'].apply(map_target_to_binary)
    df['classification'] = df['classification'].apply(map_classification_to_binary)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save processed data
    df.to_csv(output_path, index=False)
    print(f"✓ Processed data saved to: {output_path}")
    
    return df


def generate_confusion_matrix(
    df: pd.DataFrame,
    output_dir: str
) -> Tuple[pd.DataFrame, dict]:
    """
    Generate confusion matrix and classification metrics.
    
    Args:
        df: DataFrame with 'target' (ground truth) and 'classification' (prediction) columns
        output_dir: Directory to save confusion matrix visualization and metrics
        
    Returns:
        Tuple of (confusion_matrix_df, metrics_dict)
    """
    # Extract ground truth and predictions
    y_true = df['target']
    y_pred = df['classification']
    
    # Generate confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=["Not Toxic", "Toxic"])
    
    # Calculate metrics
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, labels=["Not Toxic", "Toxic"], average='weighted'),
        'recall': recall_score(y_true, y_pred, labels=["Not Toxic", "Toxic"], average='weighted'),
        'f1': f1_score(y_true, y_pred, labels=["Not Toxic", "Toxic"], average='weighted'),
        'total_samples': len(df),
    }
    
    # Create confusion matrix DataFrame for readability
    cm_df = pd.DataFrame(
        cm,
        index=['Actual: Not Toxic', 'Actual: Toxic'],
        columns=['Predicted: Not Toxic', 'Predicted: Toxic']
    )
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save confusion matrix visualization
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=["Not Toxic", "Toxic"],
        yticklabels=["Not Toxic", "Toxic"],
        cbar_kws={'label': 'Count'}
    )
    plt.title('Confusion Matrix: LLM Judge Binary Classification')
    plt.ylabel('Ground Truth (Target)')
    plt.xlabel('Prediction (Classification)')
    plt.tight_layout()
    
    confusion_matrix_path = os.path.join(output_dir, 'confusion_matrix.png')
    plt.savefig(confusion_matrix_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Confusion matrix visualization saved to: {confusion_matrix_path}")
    
    # Save metrics to text file
    metrics_text_path = os.path.join(output_dir, 'confusion_matrix_metrics.txt')
    with open(metrics_text_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("BINARY CLASSIFICATION METRICS\n")
        f.write("=" * 60 + "\n\n")
        f.write("CONFUSION MATRIX:\n")
        f.write(cm_df.to_string())
        f.write("\n\n" + "-" * 60 + "\n\n")
        f.write("CLASSIFICATION METRICS:\n")
        f.write(f"Total Samples: {metrics['total_samples']}\n")
        f.write(f"Accuracy:      {metrics['accuracy']:.4f}\n")
        f.write(f"Precision:     {metrics['precision']:.4f}\n")
        f.write(f"Recall:        {metrics['recall']:.4f}\n")
        f.write(f"F1-Score:      {metrics['f1']:.4f}\n")
        f.write("\n" + "=" * 60 + "\n")
    
    print(f"✓ Metrics saved to: {metrics_text_path}")
    
    return cm_df, metrics


def main() -> None:
    """Main orchestration function."""
    # Define paths
    project_root = Path(__file__).parent
    input_path = project_root / "Outputs" / "output.csv"
    output_data_path = project_root / "Output_Analysis" / "Output_Analysis_Data.csv"
    output_analysis_dir = project_root / "Output_Analysis"
    
    print("Starting binary classification output mapping...\n")
    
    # Process and save data
    df = process_and_save_data(str(input_path), str(output_data_path))
    print(f"  - Total records processed: {len(df)}\n")
    
    # Generate confusion matrix
    cm_df, metrics = generate_confusion_matrix(df, str(output_analysis_dir))
    
    print("\nBinary Classification Metrics:")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1-Score:  {metrics['f1']:.4f}")
    print("\n✓ Process completed successfully!")


if __name__ == "__main__":
    main()
