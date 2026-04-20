import pandas as pd
import numpy as np

# Load the dataset
csv_path = '/Users/yliu/Downloads/jigsaw-unintended-bias-in-toxicity-classification/train.csv'
df = pd.read_csv(csv_path)

print(f"Dataset shape: {df.shape}")
print(f"\nTarget column statistics:")
print(df['target'].describe())
print()

# Filter 1: 50 entries with lowest target value
lowest_50 = df.nsmallest(50, 'target')

# Filter 2: 50 entries with highest target value
highest_50 = df.nlargest(50, 'target')

# Filter 3: 50 entries around target value = 0.25
target_0_25 = df.iloc[(df['target'] - 0.25).abs().argsort()[:50]]

# Filter 4: 50 entries around target value = 0.75
target_0_75 = df.iloc[(df['target'] - 0.75).abs().argsort()[:50]]

print(f"Lowest 50 entries - Target range: {lowest_50['target'].min():.4f} to {lowest_50['target'].max():.4f}")
print(f"Highest 50 entries - Target range: {highest_50['target'].min():.4f} to {highest_50['target'].max():.4f}")
print(f"Around 0.25 entries - Target range: {target_0_25['target'].min():.4f} to {target_0_25['target'].max():.4f}")
print(f"Around 0.75 entries - Target range: {target_0_75['target'].min():.4f} to {target_0_75['target'].max():.4f}")
print()

# Create combined filtered data
combined_filtered = pd.concat([
    lowest_50.assign(source='lowest_50'),
    highest_50.assign(source='highest_50'),
    target_0_25.assign(source='around_0_25'),
    target_0_75.assign(source='around_0_75')
], ignore_index=True)

# Add new classification columns to all filtered datasets
def add_classification_columns(df):
    # multiclass_target column
    conditions = [
        (df['target'] > 0) & (df['severe_toxicity'] == 0),
        (df['target'] > 0) & (df['severe_toxicity'] > 0),
        df['target'] <= 0
    ]
    choices = ['toxic', 'severe_toxic', 'non_toxic']
    df['multiclass_target'] = np.select(conditions, choices, default='non_toxic')
    
    # binary_target column
    df['binary_target'] = np.where(df['target'] > 0, 'toxic', 'non_toxic')
    
    return df

# Apply classification to all filtered datasets
lowest_50 = add_classification_columns(lowest_50)
highest_50 = add_classification_columns(highest_50)
target_0_25 = add_classification_columns(target_0_25)
target_0_75 = add_classification_columns(target_0_75)
combined_filtered = add_classification_columns(combined_filtered)

print(f"Combined filtered dataset shape: {combined_filtered.shape}")
print(f"Total entries: {len(combined_filtered)}")
print(f"All columns preserved: {len(lowest_50.columns)} columns")
print()

# Display sample of new columns
print("Sample of new classification columns:")
print(combined_filtered[['target', 'severe_toxicity', 'multiclass_target', 'binary_target']].head(10))
print()

# Save files
output_dir = '/Users/yliu/Desktop/Daisy/Vector Multimodal Bootcamp/LLM Interpretability/Develop'
combined_filtered.to_csv(f'{output_dir}/all_filtered_combined.csv', index=False)

print(f"✓ Files saved successfully to: {output_dir}")
print()
print("Generated files:")
print("  - all_filtered_combined.csv (200 entries with multiclass_target and binary_target columns)")
