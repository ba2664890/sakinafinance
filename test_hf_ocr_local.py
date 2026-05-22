"""
Test HuggingFace Inference API — Modèles OCR/Vision
Exécutez ce script dans votre terminal :
  HF_API_KEY=your_key python3 test_hf_ocr_local.py
"""
import base64
import os
import requests

HF_TOKEN = os.environ.get("HF_API_KEY", "")
IMAGE_PATH = os.environ.get(
    "OCR_TEST_IMAGE",
    "/home/cardan/Documents/sakinafinance/reports/téléchargement.jpeg"
)

if not HF_TOKEN:
    print("❌ HF_API_KEY non défini. Lancez : HF_API_KEY=hf_xxx python3 test_hf_ocr_local.py")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json",
}

with open(IMAGE_PATH, "rb") as f:
    image_bytes = f.read()
image_b64 = base64.b64encode(image_bytes).decode("ascii")
image_data_url = f"data:image/jpeg;base64,{image_b64}"

MODELS = [
    ("microsoft/trocr-large-printed", "image-to-text"),
    ("meta-llama/Llama-3.2-11B-Vision-Instruct", "chat-vision"),
    ("mistralai/Pixtral-12B-2409", "chat-vision"),
    ("Qwen/Qwen2-VL-7B-Instruct", "chat-vision"),
]

PROMPT = (
    "Tu es un moteur OCR. Extrais tout le texte visible de ce document financier. "
    "Retourne uniquement le texte brut avec les montants, dates, noms et numéros."
)


def test_image_to_text(model_id):
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    r = requests.post(url, headers={"Authorization": f"Bearer {HF_TOKEN}"}, data=image_bytes, timeout=30)
    if r.status_code == 200:
        data = r.json()
        return "✅ OK", (data[0].get("generated_text") if isinstance(data, list) else str(data))[:500]
    return f"❌ {r.status_code}", r.text[:200]


def test_chat_vision(model_id):
    url = f"https://api-inference.huggingface.co/models/{model_id}/v1/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_data_url}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        "max_tokens": 1024,
    }
    r = requests.post(url, headers=HEADERS, json=payload, timeout=60)
    if r.status_code == 200:
        text = r.json()["choices"][0]["message"]["content"]
        return "✅ OK", text[:600]
    return f"❌ {r.status_code}", r.text[:200]


print("=" * 60)
print("TEST HuggingFace OCR — Vision Models")
print("=" * 60)

for model_id, model_type in MODELS:
    print(f"\n🔍 {model_id} ({model_type})")
    try:
        fn = test_image_to_text if model_type == "image-to-text" else test_chat_vision
        status, result = fn(model_id)
        print(f"   {status}")
        print(f"   {result}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n" + "=" * 60)
