filepath_vercel = r"c:\Users\Hp\Desktop\new proje test\vercel.json"

vercel_config = """{
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "/$1"
    }
  ]
}
"""

with open(filepath_vercel, "w", encoding="utf-8") as f:
    f.write(vercel_config)

print("vercel.json updated successfully.")
