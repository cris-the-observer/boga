import json
import urllib.request

from classifier import classify_transcript
from severity_scorer import score_severity


# 1. Unload Qwen2.5 just to ensure memory constraints are met
def unload_model(model_name):
    print(f"Unloading {model_name} from memory...")
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req):
            pass
    except Exception:
        pass


unload_model("qwen2.5:3b-instruct-q4_K_M")

tests = {
    "Test A (heavy scam)": "I don't even know what Bitcoin is honestly. Okay, okay, I'm at the machine. It says enter amount. How much do I put? Five thousand? I don't have that much on me. Okay let me check. I have about thirty-two hundred in cash. The officer said I have to pay today or there's a warrant? Okay. Okay I'm putting in thirty-two hundred. It's asking for a wallet address now. Okay go ahead. 3... F... x... capital B...",
    "Test B (benign)": "Yeah I'm just buying some Bitcoin. I've done this before, putting in about two hundred bucks. My Coinbase wallet, I have the QR code right here. Cool, almost done.",
    "Test C (subtle)": "Okay I did the three hundred at the other place already. He said I need to do five hundred more here. No I don't really get how this works but he said just follow the steps. Don't worry about what it is just put the cash in.",
}

model = "qwen3:1.7b"
results = []

for name, transcript in tests.items():
    print(f"Running '{name}'...")
    llm_out = classify_transcript(model, transcript)
    score = score_severity(llm_out)
    score["test_name"] = name
    score["inference_time_seconds"] = llm_out["inference_time_seconds"]
    results.append(score)

print("\n" + "=" * 110)
print(f"{'Test Name':<20} | {'Class':<10} | {'Severity':<10} | {'Time(s)':<8} | Triggered Groups")
print("-" * 110)
for r in results:
    groups_str = ", ".join(r["triggered_groups"]) if r["triggered_groups"] else "None"
    print(
        f"{r['test_name'][:20]:<20} | {r['classification']:<10} | {r['severity']:<10} | {r['inference_time_seconds']:<8.2f} | {groups_str}"
    )
    print(f"  -> Observations: {r['observations']}")
print("=" * 110)
