import os

files = ['backend/main.py', 'backend/doctor_auth.py', 'backend/auth.py', 'backend/profile.py']
for f in files:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Remove the blocking ping
        content = content.replace("client.admin.command('ping')", "# client.admin.command('ping') # removed to prevent Vercel cold start timeouts")
        content = content.replace('client.admin.command("ping")', "# client.admin.command('ping') # removed to prevent Vercel cold start timeouts")
        
        # Reduce timeout from 5000 to 1500
        content = content.replace("serverSelectionTimeoutMS=5000", "serverSelectionTimeoutMS=1500")
        
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f'Patched {f}')
