from pymongo import MongoClient
import pandas as pd
import csv
import json
import os
from dotenv import load_dotenv

load_dotenv()

print("Connecting to MongoDB...")

# NOTE: This script is intended as a one-time dataset loader for local
# environments. It reads CSV/JSON files and bulk-inserts into MongoDB.
# Running this in a production environment may overwrite collections
# and is NOT idempotent unless you add safeguards. Use with caution.
#
# The MongoDB connection string is read from environment variables;
# avoid printing or committing the full URL to logs or source control.
mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
db_name = os.getenv('MONGODB_LOCAL_DB', 'local_data')
client = MongoClient(mongodburl)

# use database "local"
db = client[db_name]

# ---------------------------
# Load datasets
# ---------------------------

print("Loading CSV files...")

faers_df = pd.read_csv("faers_clean_dataset.csv")
drug_disease_df = pd.read_csv("drug_disease_map.csv")
drug_reaction_df = pd.read_csv("drug_reaction_map.csv")

# Load new datasets
print("Loading drug interactions...")
with open('drug_interactions.csv', 'r') as f:
    drug_interactions = list(csv.DictReader(f))

print("Loading symptom-disease map...")
with open('symptom_disease_map.csv', 'r') as f:
    symptom_disease = list(csv.DictReader(f))

print("Loading medical knowledge graph...")
with open('medical_knowledge_graph.json', 'r') as f:
    knowledge_graph = json.load(f)

# ---------------------------
# Convert to dictionary
# ---------------------------

faers_records = faers_df.to_dict("records")
drug_disease_records = drug_disease_df.to_dict("records")
drug_reaction_records = drug_reaction_df.to_dict("records")

# ---------------------------
# Create collections
# ---------------------------

faers_collection = db["faers_clean_reports"]
drug_disease_collection = db["drug_disease_map"]
drug_reaction_collection = db["drug_reaction_map"]
drug_interactions_collection = db["drug_interactions"]
symptom_disease_collection = db["symptom_disease_map"]
knowledge_graph_collection = db["medical_knowledge_graph"]

# Clear old data (optional)
faers_collection.delete_many({})
drug_disease_collection.delete_many({})
drug_reaction_collection.delete_many({})
drug_interactions_collection.delete_many({})
symptom_disease_collection.delete_many({})

# ---------------------------
# Insert data
# ---------------------------

print("Inserting FAERS reports...")
faers_collection.insert_many(faers_records)

print("Inserting drug-disease mapping...")
drug_disease_collection.insert_many(drug_disease_records)

print("Inserting drug-reaction mapping...")
drug_reaction_collection.insert_many(drug_reaction_records)

print("Inserting drug interactions...")
drug_interactions_collection.insert_many(drug_interactions)

print("Inserting symptom-disease map...")
symptom_disease_collection.insert_many(symptom_disease)

print("Inserting medical knowledge graph...")
knowledge_graph_collection.insert_one(knowledge_graph)

# ---------------------------
# Create indexes for fast queries
# ---------------------------

faers_collection.create_index("drug_name")
faers_collection.create_index("disease")

drug_disease_collection.create_index("disease")
drug_disease_collection.create_index("drug_name")

drug_reaction_collection.create_index("drug_name")

drug_interactions_collection.create_index("drug1")
drug_interactions_collection.create_index("drug2")

symptom_disease_collection.create_index("symptoms")
symptom_disease_collection.create_index("diseases")

knowledge_graph_collection.create_index("diseases")
knowledge_graph_collection.create_index("medications")

# Create index for patient timeline
db.patient_reports.create_index("user_email")
db.patient_reports.create_index("date")

print("Indexes created")

print("\nAll datasets inserted successfully into MongoDB")