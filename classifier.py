import json
import logging
import time
import urllib.request
from urllib.error import URLError

import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You analyze speech transcripts from a cryptocurrency ATM microphone.

CLEAN (most transactions are normal):
- Buying crypto for themselves
- Talking about prices, the market, investments
- Chatting with friends or family
- Small talk, casual conversation, brief phrases

SUSPICIOUS (classify ONLY if you see clear evidence of a scam):
- On the phone being told what to do at the machine by a caller
- Being directed to send crypto to someone else's address
- Mentioning police, IRS, warrants, arrest, or government demanding payment
- Expressing fear or panic about consequences
- Told to be quiet or keep the transaction secret
- Spelling out a wallet address as if dictated over the phone
- Confused about crypto while sending money
- Told they need to send more money after already sending some

IMPORTANT: Only list observations about suspicious things you actually found in the transcript. Do NOT list things that are absent. If nothing suspicious is found, return an empty observations list.
Respond ONLY in JSON."""


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
        "options": {"temperature": 0, "num_ctx": 2048},
        "think": False,
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
        raw_observations = llm_response.get("observations", [])

        # Filter out checklist-style observations where the LLM echoes prompt criteria with "None"
        observations = [obs for obs in raw_observations if not obs.rstrip().endswith(": None") and obs.strip() != "None"]
        if len(observations) < len(raw_observations):
            log.debug("Filtered %d checklist observations", len(raw_observations) - len(observations))

        log.info("Ollama classification: %s (%d observations)", classification, len(observations))
        return {
            "classification": classification,
            "observations": observations,
            "inference_time_seconds": inference_time,
        }
    except (URLError, OSError, ValueError) as e:
        log.error("Error calling Ollama: %s", e)
        return {"classification": "ERROR", "observations": [], "inference_time_seconds": time.time() - start_time}
