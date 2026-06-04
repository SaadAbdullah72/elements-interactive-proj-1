"""
Backfill script to populate `doctor_id` for existing doctor records.

Creates IDs using the same pattern used in `doctor_auth.generate_doctor_id`:
  DR<genderDigit>-<provinceCode><random2Digits>-<last3LicenseDigits>

Usage:
  python backend/scripts/backfill_doctor_ids.py

It reads MongoDB connection details from environment:
  - MONGODB_URL
  - MONGODB_DBFULL_DB (default: dbfull)

The script will:
 - find doctors without `doctor_id` or with an old 24-char ObjectId string
 - compute a new formatted `doctor_id`
 - update the doctor document
 - update related `license_verifications` entries to set `doctor_id`

Run locally and inspect output before pushing to production.
"""

import os
import re
import random
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# Province map (same as backend)
PROVINCE_CODE_MAP = {
    "punjab": "3",
    "sindh": "4",
    "khyber pakhtunkhwa": "5",
    "kpk": "5",
    "balochistan": "6",
    "islamabad": "7",
    "islamabad capital territory": "7",
    "gilgit-baltistan": "8",
    "gilgit baltistan": "8",
    "gilgit": "8",
    "azad jammu & kashmir": "9",
    "ajk": "9"
}

# Small city -> province hint map for common cities
CITY_TO_PROVINCE = {
    "karachi": "Sindh",
    "lahore": "Punjab",
    "islamabad": "Islamabad",
    "rawalpindi": "Punjab",
    "peshawar": "Khyber Pakhtunkhwa",
    "quetta": "Balochistan",
    "gilgit": "Gilgit-Baltistan",
    "muzaffarabad": "Azad Jammu & Kashmir",
}


def get_province_code(province: str) -> str:
    if not province:
        return "0"
    normalized = province.strip().lower()
    return PROVINCE_CODE_MAP.get(normalized, "0")


def infer_province_from_city(city: str) -> str:
    if not city:
        return ""
    key = city.strip().lower()
    return CITY_TO_PROVINCE.get(key, "")


def generate_doctor_id(gender: str, province: str, license_number: str) -> str:
    gender_digit = "1" if (gender or "").strip().lower() == "male" else "0"
    province_digit = get_province_code(province)
    license_digits = re.sub(r"\D", "", license_number or "")
    license_suffix = license_digits[-3:].zfill(3) if license_digits else "000"
    random_segment = str(random.randint(0, 99)).zfill(2)
    return f"DR{gender_digit}-{province_digit}{random_segment}-{license_suffix}"


def main():
    MONGODB_URL = os.getenv("MONGODB_URL", os.getenv("LOCAL_MONGODB_URL", "mongodb://localhost:27017/"))
    DB_NAME = os.getenv("MONGODB_DBFULL_DB", "dbfull")

    print(f"Connecting to MongoDB: {MONGODB_URL} DB: {DB_NAME}")
    client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    doctors = db["doctors"]
    license_verifications = db["license_verifications"]

    query = {
        "$or": [
            {"doctor_id": {"$exists": False}},
            {"doctor_id": {"$regex": "^[a-fA-F0-9]{24}$"}}
        ]
    }

    candidates = list(doctors.find(query))
    print(f"Found {len(candidates)} doctor(s) to update")

    updated = 0
    skipped = 0
    for doc in candidates:
        db_id = str(doc.get("_id"))
        gender = doc.get("gender", "Male")
        province = doc.get("province") or infer_province_from_city(doc.get("city", "")) or ""
        license_no = doc.get("medical_council_registration", "")

        if not license_no:
            print(f"Skipping {db_id} - no license number")
            skipped += 1
            continue

        new_doctor_id = generate_doctor_id(gender, province, license_no)

        # Update doctor record
        res = doctors.update_one({"_id": doc["_id"]}, {"$set": {"doctor_id": new_doctor_id}})
        if res.modified_count:
            # Update license_verifications entries that reference the old id or doctor_db_id
            license_verifications.update_many(
                {"$or": [{"doctor_db_id": db_id}, {"doctor_id": db_id}, {"email": doc.get("email")} ]},
                {"$set": {"doctor_id": new_doctor_id, "doctor_db_id": db_id}}
            )
            print(f"Updated {db_id} -> {new_doctor_id}")
            updated += 1
        else:
            print(f"No change for {db_id} (maybe already updated)")

    print("\nSummary:")
    print(f"  Processed: {len(candidates)}")
    print(f"  Updated:   {updated}")
    print(f"  Skipped:   {skipped}")


if __name__ == "__main__":
    main()
