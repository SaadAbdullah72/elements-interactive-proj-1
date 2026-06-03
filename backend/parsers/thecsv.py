import pandas as pd

print("Loading parsed dataset...")

# Load parsed dataset
df = pd.read_csv("faers_parsed_dataset.csv")

print("Original records:", len(df))

# -------------------------
# 1. Clean main dataset
# -------------------------

df_clean = df.copy()

df_clean["drug_name"] = df_clean["drug_name"].astype(str).str.lower().str.strip()
df_clean["disease"] = df_clean["disease"].astype(str).str.lower().str.strip()
df_clean["reaction"] = df_clean["reaction"].astype(str).str.lower().str.strip()

# Remove duplicates
df_clean = df_clean.drop_duplicates()

# Save cleaned dataset
df_clean.to_csv("faers_clean_dataset.csv", index=False)

print("Clean dataset created")

# -------------------------
# 2. Drug–Disease Mapping
# -------------------------

drug_disease = df_clean[["disease", "drug_name"]]

drug_disease = drug_disease.dropna()

drug_disease = drug_disease.drop_duplicates()

drug_disease.to_csv("drug_disease_map.csv", index=False)

print("Drug–Disease mapping created")

# -------------------------
# 3. Drug–Reaction Mapping
# -------------------------

drug_reaction = df_clean[["drug_name", "reaction"]]

drug_reaction = drug_reaction.dropna()

drug_reaction = drug_reaction.drop_duplicates()

drug_reaction.to_csv("drug_reaction_map.csv", index=False)

print("Drug–Reaction mapping created")

# -------------------------
# Summary
# -------------------------

print("\nDATASET SUMMARY")
print("Full cleaned dataset:", len(df_clean))
print("Disease-Drug mappings:", len(drug_disease))
print("Drug-Reaction mappings:", len(drug_reaction))

print("\nAll datasets generated successfully.")