"""
Reset email tracking for all patients.
Use this to reset the counter when testing.
"""
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
db_name = os.getenv('MONGODB_DBFULL_DB', 'dbfull')
client = MongoClient(mongodburl)
db = client[db_name]
email_notifications_collection = db["email_notifications"]

# Delete all tracking documents
result = email_notifications_collection.delete_many({})

print(f"✅ Email tracking reset!")
print(f"   - Deleted {result.deleted_count} tracking records")
print(f"   - All patients can now receive emails again (3 per 5 queries)")
