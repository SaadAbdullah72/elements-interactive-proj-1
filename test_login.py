import urllib.request, json, urllib.error
req = urllib.request.Request(
    'https://elements-interactive-proj-1.vercel.app/api/doctor/login',
    data=json.dumps({'name':'DrAdmin','password':'Doctor@1122'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    print(urllib.request.urlopen(req).read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print("BODY:", e.read().decode('utf-8'))
