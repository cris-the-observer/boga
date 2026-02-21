import json
import time
import urllib.request

SYSTEM_PROMPT = """You analyze speech transcripts from a cryptocurrency ATM user. You only see the user's words. You cannot hear anyone on their phone.

Decide if the transcript is SUSPICIOUS or CLEAN. List every observation that supports your decision.

SUSPICIOUS signals:
- Spelling out a wallet address or reading back numbers/letters as if dictated
- Asking someone on the phone what button to press or what to do next
- Expressing confusion about crypto or the machine while still doing a large transaction
- Mentioning police, IRS, warrants, arrest, deportation, lawsuits, or any government agency demanding payment
- Expressing fear, panic, or urgency about consequences if they don't send money
- Mentioning a large dollar amount or saying they already sent money at another machine
- Saying they were told not to tell anyone why they're sending money
- Giving a reason for the transaction that contradicts other things they've said
- Confusing the crypto ATM with gift cards, wire transfers, or vouchers

Respond ONLY in JSON. No other text."""


def classify_transcript(model_name, transcript):
    payload = {
        "model": model_name,
        "prompt": transcript,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "classification": {"type": "string", "enum": ["SUSPICIOUS", "CLEAN"]},
                "observations": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["classification", "observations"],
        },
        "options": {"temperature": 0},
    }

    start_time = time.time()
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        inference_time = time.time() - start_time
        llm_response_text = result.get("response", "{}")

        # Parse the nested JSON response enforced by format
        try:
            llm_response = json.loads(llm_response_text)
        except json.JSONDecodeError:
            print("Failed to decode JSON from Ollama.")
            return {"classification": "ERROR", "observations": [], "inference_time_seconds": inference_time}

        return {
            "classification": llm_response.get("classification", "ERROR"),
            "observations": llm_response.get("observations", []),
            "inference_time_seconds": inference_time,
        }
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return {"classification": "ERROR", "observations": [], "inference_time_seconds": time.time() - start_time}
