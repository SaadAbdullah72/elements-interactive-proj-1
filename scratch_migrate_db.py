import os
import sys
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

def migrate_database(mongodb_url: str):
    print("Connecting to MongoDB...")
    client = MongoClient(mongodb_url)
    
    try:
        client.admin.command('ping')
        print("Successfully connected to MongoDB.")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        return

    source_db_name = "authentication"
    target_db_name = "dbfull"
    
    source_db = client[source_db_name]
    target_db = client[target_db_name]

    collections_to_migrate = ["doctors", "license_verifications", "users"]

    for coll_name in collections_to_migrate:
        print(f"\n--- Migrating collection: {coll_name} ---")
        source_collection = source_db[coll_name]
        target_collection = target_db[coll_name]

        documents = list(source_collection.find({}))
        if not documents:
            print(f"No documents found in {source_db_name}.{coll_name}. Skipping.")
            continue

        print(f"Found {len(documents)} documents in {source_db_name}.{coll_name}.")
        
        # We will insert documents one by one to handle duplicates gracefully
        inserted_count = 0
        skipped_count = 0
        
        for doc in documents:
            try:
                # Check if document already exists to avoid duplicates
                # Usually checking by email or _id is best
                query = {"_id": doc["_id"]}
                if target_collection.find_one(query):
                    skipped_count += 1
                else:
                    target_collection.insert_one(doc)
                    inserted_count += 1
            except Exception as e:
                print(f"Error inserting document {doc.get('_id')}: {e}")
                
        print(f"Migration for {coll_name} complete: {inserted_count} inserted, {skipped_count} skipped (already exist).")

    print("\n✅ Database migration completed successfully.")
    print("Data from 'authentication' has been copied to 'dbfull'.")

if __name__ == "__main__":
    url = os.getenv("MONGODB_URL")
    if not url:
        print("ERROR: MONGODB_URL environment variable is not set.")
        print("Please provide it as an argument: python migrate_db.py <YOUR_MONGODB_URL>")
        if len(sys.argv) > 1:
            url = sys.argv[1]
        else:
            sys.exit(1)
            
    migrate_database(url)
