"""
Filter a CSV by cot_verdict:
  - keep ALL rows where cot_verdict is "Partially" or "Misaligned"
  - keep the top 20 rows where cot_verdict is "Well-Aligned"
"""
 
import pandas as pd
 
INPUT_FILE = "Output_Analysis/Output_Analysis_Data.csv"
OUTPUT_FILE = "Output_Analysis/Output_Analysis_Data_filtered.csv"
 
df = pd.read_csv(INPUT_FILE)
 
# All Partially / Misaligned rows
keep_all = df[df["cot_verdict"].isin(["Partially Aligned", "Misaligned"])]
 
# Top 20 Well-Aligned rows (first 20 in file order).
# If "top" means sorted by some other column, use this form instead:
#   top_well_aligned = (
#       df[df["cot_verdict"] == "Well-Aligned"]
#       .sort_values("score", ascending=False)
#       .head(20)
#   )
top_well_aligned = df[df["cot_verdict"] == "Well-Aligned"].head(20)
 
# Combine and restore original row order
filtered = pd.concat([keep_all, top_well_aligned]).sort_index()
 
filtered.to_csv(OUTPUT_FILE, index=False)
 
print(f"Wrote {len(filtered)} of {len(df)} rows to {OUTPUT_FILE}")
print(f"  Partially / Misaligned: {len(keep_all)}")
print(f"  Well-Aligned (kept):    {len(top_well_aligned)}")