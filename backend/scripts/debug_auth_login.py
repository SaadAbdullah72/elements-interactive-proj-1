import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import auth
from auth import UserLogin

print('auth module file:', auth.__file__)
print('auth db name:', auth.auth_db_name)
print('mongo url:', auth.mongodburl)

async def run_one(email, password):
    login_data = UserLogin(email=email, password=password)
    user = auth.users_collection.find_one({'email': login_data.email.lower()})
    print('user found:', user is not None)
    if user:
        print('stored hash:', user['password_hash'])
        print('verify check:', auth.verify_password(login_data.password, user['password_hash']))
    try:
        result = await auth.login(login_data)
        print('login result type:', type(result))
        print('login result:', result)
    except Exception as e:
        print('login exception:', type(e).__name__, e)

if __name__ == '__main__':
    asyncio.run(run_one('hima21517@gmail.com', 'Doctor@123'))
