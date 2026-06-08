import os
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, os.getcwd())
import auth
import doctor_auth
from auth import UserLogin

accounts = [
    {
        'email': 'hima21517@gmail.com',
        'name': 'Dr. Hina Ahmed',
        'password': 'Doctor@123',
        'age': 40,
        'date_of_birth': '1984-09-20',
        'gender': 'Female',
        'province': 'Punjab',
        'specialization': 'General Physician',
        'medical_council_registration': 'PMC-123457',
        'medical_council_country': 'Pakistan',
        'cnic': '35202-1234567-1',
        'phone': '0301-1111111',
        'address': '123 Health Avenue',
        'city': 'Lahore',
        'hospital_affiliation': 'Apex Medical Center',
        'hospital_address': '1 Medical Plaza, Lahore',
        'years_of_experience': 12,
        'additional_qualifications': 'MBBS, FCPS',
    },
    {
        'email': 'hejaz6784@gmail.com',
        'name': 'Dr. Hamza Ejaz',
        'password': 'Doctor@123',
        'age': 42,
        'date_of_birth': '1982-07-14',
        'gender': 'Male',
        'province': 'Sindh',
        'specialization': 'Cardiologist',
        'medical_council_registration': 'PMC-234567',
        'medical_council_country': 'Pakistan',
        'cnic': '35202-2345678-2',
        'phone': '0302-2222222',
        'address': '456 Cardio Road',
        'city': 'Karachi',
        'hospital_affiliation': 'Evercare Hospital',
        'hospital_address': '2 Heart Street, Karachi',
        'years_of_experience': 14,
        'additional_qualifications': 'MBBS, FCPS, MRCP',
    },
    {
        'email': 'k6076606@gmail.com',
        'name': 'Dr. Khadija Noor',
        'password': 'Doctor@123',
        'age': 38,
        'date_of_birth': '1986-05-30',
        'gender': 'Female',
        'province': 'Punjab',
        'specialization': 'Dermatologist',
        'medical_council_registration': 'PMC-345678',
        'medical_council_country': 'Pakistan',
        'cnic': '35202-3456789-3',
        'phone': '0303-3333333',
        'address': '789 Skin Care Blvd',
        'city': 'Rawalpindi',
        'hospital_affiliation': 'Dermacare Clinic',
        'hospital_address': '3 Skin Avenue, Rawalpindi',
        'years_of_experience': 10,
        'additional_qualifications': 'MBBS, DPD',
    },
]


def insert_doctor_record(doc):
    existing = doctor_auth.doctors_collection.find_one({'email': doc['email']})
    if existing:
        return existing.get('doctor_id'), False
    doctor_id = doctor_auth.generate_doctor_id(doc['gender'], doc['phone'], doc['cnic'])
    cnic_v = doctor_auth.verify_cnic(doc['cnic'])
    license_v = doctor_auth.verify_pmc_license(doc['medical_council_registration'], doc['name'])
    record = {
        'email': doc['email'],
        'name': doc['name'],
        'password_hash': doctor_auth.hash_password(doc['password']),
        'age': doc['age'],
        'date_of_birth': doc['date_of_birth'],
        'gender': doc['gender'],
        'province': doc['province'],
        'specialization': doc['specialization'],
        'medical_council_registration': doc['medical_council_registration'],
        'medical_council_country': doc['medical_council_country'],
        'cnic': doc['cnic'],
        'phone': doc['phone'],
        'address': doc['address'],
        'city': doc['city'],
        'hospital_affiliation': doc['hospital_affiliation'],
        'hospital_address': doc['hospital_address'],
        'years_of_experience': doc['years_of_experience'],
        'additional_qualifications': doc['additional_qualifications'],
        'license_image': None,
        'doctor_id': doctor_id,
        'license_verification': license_v,
        'cnic_verification': cnic_v,
        'account_status': 'active' if license_v['verified'] else 'pending_verification',
        'created_at': datetime.utcnow().isoformat(),
        'last_login': None,
        'total_consultations': 0,
    }
    doctor_auth.doctors_collection.insert_one(record)
    return doctor_id, True


def insert_auth_user(doc):
    existing = auth.users_collection.find_one({'email': doc['email'].lower()})
    if existing:
        return str(existing['_id']), False
    user_record = {
        'name': doc['name'],
        'email': doc['email'].lower(),
        'password_hash': auth.hash_password(doc['password']),
        'age': doc['age'],
        'gender': doc['gender'],
        'medical_history': '',
        'email_verified': True,
        'verification_token': '',
        'role': 'doctor',
        'created_at': datetime.utcnow().isoformat(),
        'analyses': [],
    }
    result = auth.users_collection.insert_one(user_record)
    return str(result.inserted_id), True


async def verify_logins():
    for doc in accounts:
        login_data = UserLogin(email=doc['email'], password=doc['password'])
        try:
            result = await auth.login(login_data)
            print('LOGIN SUCCESS', doc['email'], 'id=', result.user.id)
        except Exception as e:
            print('LOGIN FAIL', doc['email'], str(e))


if __name__ == '__main__':
    print('Using doctor_auth:', doctor_auth.__file__)
    print('doctor_auth mongo:', doctor_auth.mongodburl)
    print('Using auth:', auth.__file__)
    print('auth mongo:', auth.mongodburl)
    for doc in accounts:
        doctor_id, created = insert_doctor_record(doc)
        print('Doctor', doc['email'], 'doctor_id=', doctor_id, 'created=' + str(created))
    for doc in accounts:
        user_id, created = insert_auth_user(doc)
        print('Auth user', doc['email'], 'user_id=', user_id, 'created=' + str(created))
    asyncio.run(verify_logins())
