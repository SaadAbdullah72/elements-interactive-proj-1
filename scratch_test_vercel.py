import requests

health_url = "https://health-zeta-three.vercel.app/api/health"
login_url = "https://health-zeta-three.vercel.app/api/doctor/login"

print("--- Testing Vercel Health Check ---")
try:
    res = requests.get(health_url, timeout=10)
    print(f"Health Status: {res.status_code}")
    print(f"Health Response: {res.text}")
except Exception as e:
    print(f"Health Check connection failed: {e}")

print("\n--- Testing Vercel Doctor Login ---")
payload = {
    "name": "DrAdmin",
    "password": "Doctor@1122"
}
try:
    res = requests.post(login_url, json=payload, timeout=10)
    print(f"Login Status: {res.status_code}")
    print(f"Login Response: {res.text}")
except Exception as e:
    print(f"Login connection failed: {e}")
