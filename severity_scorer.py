import logging

KEYWORD_GROUPS = {
    "AUTHORITY": [
        "warrant",
        "arrest",
        "police",
        "officer",
        "IRS",
        "FBI",
        "SSA",
        "immigration",
        "customs",
        "deport",
        "judge",
        "lawsuit",
        "sued",
        "government",
        "agency",
        "fraud department",
    ],
    "FEAR": [
        "scared",
        "afraid",
        "panic",
        "lose everything",
        "can't go to jail",
        "prison",
        "freeze",
        "frozen",
        "urgent",
        "hurry",
        "deadline",
        "consequences",
        "threatened",
    ],
    "PHONE_DIRECTION": [
        "phone",
        "dictated",
        "told to",
        "told me to",
        "asked what",
        "what to do next",
        "what do i do",
        "what do i",
        "supposed to",
        "send you",
        "don't want you to",
        "next step",
        "instructed",
        "walked through",
        "reading back",
        "spelling out",
    ],
    "WALLET_DICTATION": [
        "wallet",
        "address",
        "characters",
        "letters",
        "spelled",
        "dictating",
        "reading back",
        "QR",
        "starts with",
    ],
    "LARGE_AMOUNT": [
        "thousand",
        "$1000",
        "$2000",
        "$3000",
        "$4000",
        "$5000",
        "$6000",
        "$7000",
        "$8000",
        "$9000",
        "$10000",
        "large sum",
        "another machine",
        "come back",
        "more cash",
        "already sent",
        "already did",
    ],
    "SECRECY": [
        "don't tell",
        "not supposed to say",
        "can't tell",
        "keep quiet",
        "secret",
        "don't mention",
        "told not to",
    ],
    "CONFUSION": [
        "don't know what",
        "don't know how",
        "don't understand",
        "what is this",
        "what is happening",
        "how does this work",
        "never used",
        "first time",
        "confused",
        "what is crypto",
        "what is bitcoin",
        "voucher",
        "gift card",
        "wire transfer",
        "money order",
        "moneygram",
    ],
}


log = logging.getLogger(__name__)


def score_severity(llm_output, transcript=""):
    classification = llm_output.get("classification", "ERROR")
    observations = llm_output.get("observations", [])

    if classification == "ERROR":
        log.warning("Scoring skipped — classification is ERROR")
        return {
            "severity": "ERROR",
            "triggered_groups": [],
            "observation_count": 0,
            "classification": classification,
            "observations": observations,
        }

    # Score keywords against the transcript (ground truth), not LLM observations
    text_lower = transcript.lower()
    log.debug("Scoring transcript (%d chars) against %d keyword groups", len(transcript), len(KEYWORD_GROUPS))
    triggered_groups = set()
    for group_name, keywords in KEYWORD_GROUPS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                log.debug("  keyword '%s' matched in group %s", kw, group_name)
                triggered_groups.add(group_name)
                break

    triggered_list = sorted(triggered_groups)
    num_triggered = len(triggered_list)

    severity = "LOW"

    if classification == "CLEAN":
        # Safety net: keyword evidence from 2+ groups overrides a CLEAN classification
        if num_triggered >= 2:
            severity = "MEDIUM"
            log.info("CLEAN overridden to MEDIUM — %d keyword groups in transcript: %s", num_triggered, ", ".join(triggered_list))
        else:
            log.info("Classification is CLEAN, %d keyword groups — severity LOW", num_triggered)
    elif classification == "SUSPICIOUS":
        if num_triggered == 0:
            # LLM said suspicious but no keywords in transcript — don't trust it
            severity = "LOW"
            log.info("SUSPICIOUS downgraded to LOW — no keyword groups in transcript")
        # CRITICAL logic
        elif (
            "SECRECY" in triggered_groups
            or ("PHONE_DIRECTION" in triggered_groups and "FEAR" in triggered_groups)
            or num_triggered >= 4
        ):
            severity = "CRITICAL"
        # HIGH logic
        elif (
            num_triggered >= 3
            or ("PHONE_DIRECTION" in triggered_groups and "LARGE_AMOUNT" in triggered_groups)
            or "AUTHORITY" in triggered_groups
        ):
            severity = "HIGH"
        # MEDIUM logic
        elif num_triggered >= 1:
            severity = "MEDIUM"

    if num_triggered > 0:
        log.info("Severity scored: %s (triggered %d groups: %s)", severity, num_triggered, ", ".join(triggered_list))

    return {
        "severity": severity,
        "triggered_groups": triggered_list,
        "observation_count": len(observations),
        "classification": classification,
        "observations": observations,
    }
