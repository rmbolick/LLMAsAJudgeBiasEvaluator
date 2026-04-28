import pandas as pd

# Read the source CSV
df = pd.read_csv('/home/coder/LLMAsAJudgeBiasEvaluator/Inputs/all_filtered_combined.csv')

# Select the two columns you want
new_df = df[['id', 'target', 'comment_text']].rename(
    columns={'id': 'id', 'target': 'target','comment_text': 'text_to_evaluate'})

# Write to a new CSV
new_df.to_csv('/home/coder/LLMAsAJudgeBiasEvaluator/Inputs/input_full.csv', index=False)