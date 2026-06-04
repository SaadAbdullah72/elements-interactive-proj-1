from pymongo import MongoClient

# Local database connection
client = MongoClient("mongodb://localhost:27017/")
db = client["local_data"]
patients_col = db["patients"]

print("Latest 5 patients:")
for p in patients_col.find().sort([("_id", -1)]).limit(5):
    print(f"Name: {p.get('pname')}, CaseID: {p.get('caseid')}, Phone: {p.get('phone_number')}")
