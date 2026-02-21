import json
import logging
import time
import urllib.request
from urllib.error import URLError

import config

log = logging.getLogger(__name__)

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

    log.info("Sending transcript to Ollama (%s) — %d chars", model_name, len(transcript))
    log.debug("Prompt preview: %.200s%s", transcript, "..." if len(transcript) > 200 else "")

    start_time = time.time()
    try:
        req = urllib.request.Request(
            config.OLLAMA_GENERATE_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))

        inference_time = time.time() - start_time
        llm_response_text = result.get("response", "{}")
        log.debug("Raw Ollama response: %s", llm_response_text)
        log.info("Ollama responded in %.2fs", inference_time)

        # Parse the nested JSON response enforced by format
        try:
            llm_response = json.loads(llm_response_text)
        except json.JSONDecodeError:
            log.error("Failed to decode JSON from Ollama response: %s", llm_response_text)
            return {"classification": "ERROR", "observations": [], "inference_time_seconds": inference_time}

        classification = llm_response.get("classification", "ERROR")
        observations = llm_response.get("observations", [])
        log.info("Ollama classification: %s (%d observations)", classification, len(observations))
        return {
            "classification": classification,
            "observations": observations,
            "inference_time_seconds": inference_time,
        }
    except (URLError, OSError, ValueError) as e:
        log.error("Error calling Ollama: %s", e)
        return {"classification": "ERROR", "observations": [], "inference_time_seconds": time.time() - start_time}
