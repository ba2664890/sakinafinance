import os, requests
key = "AIzaSyDwHLFhMQb5mOZTB7k_P4FHYhpZso8vsEQ"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
r = requests.get(url)
if r.status_code == 200:
    for m in r.json().get("models", []):
        print(f"{m['name']} - supportedGenerationMethods: {m.get('supportedGenerationMethods', [])}")
else:
    print(r.status_code, r.text)
