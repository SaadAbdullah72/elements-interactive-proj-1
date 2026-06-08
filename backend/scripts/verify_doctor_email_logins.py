import os
import sys
from datetime import datetime
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import auth
from auth import UserLogin

users = [
    {'email': 'hima21517@gmail.com', 'password': 'Doctor@123'},
    {'email': 'hejaz6784@gmail.com', 'password': 'Doctor@123'},
    {'email': 'k6076606@gmail.com', 'password': 'Doctor@123'},
]

async def check_logins():
    for u in users:
        try:
            login_data = UserLogin(email=u['email'], password=u['password'])
            result = await auth.login(login_data)
            print('LOGIN SUCCESS', u['email'], 'user id=', result.user.id)
        except Exception as e:
            print('LOGIN FAIL', u['email'], str(e))

if __name__ == '__main__':
    asyncio.run(check_logins())
