import requests

key = "AIzaSyDwHLFhMQb5mOZTB7k_P4FHYhpZso8vsEQ"
url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
r_list = requests.get(url_list)
if r_list.status_code != 200:
    print(f"Failed to list models: {r_list.text}")
    exit(1)

models = r_list.json().get("models", [])
available_models = [m['name'] for m in models if 'generateContent' in m.get('supportedGenerationMethods', [])]

print(f"Found {len(available_models)} models supporting generateContent.")

working_model = None
for model_name in available_models:
    model_id = model_name.split('/')[-1]
    print(f"Testing {model_id}...")
    
    url_gen = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Dis juste 'OK'."}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 5}
    }
    
    r_gen = requests.post(url_gen, json=payload)
    if r_gen.status_code == 200:
        print(f"SUCCESS with {model_id}!")
        working_model = model_id
        break
    else:
        print(f"FAILED {model_id}: HTTP {r_gen.status_code} - {r_gen.text[:100]}")

if working_model:
    # Update .env
    env_path = "/home/cardan/Documents/sakinafinance/.env"
    with open(env_path, "w") as f:
        f.write(f"GEMINI_MODEL={working_model}\n")
        f.write(f"GEMINI_FALLBACK_MODELS={working_model}\n")
        f.write(f"GEMINI_API_KEY={key}\n")
    print(f"Updated .env with {working_model}")
else:
    print("No working model found.")
