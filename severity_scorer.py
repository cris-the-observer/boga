def score_severity(llm_output):
    classification = llm_output.get("classification", "ERROR")
    observations = llm_output.get("observations", [])

    if classification == "ERROR":
        return {
            "severity": "ERROR",
            "triggered_groups": [],
            "observation_count": 0,
            "classification": classification,
            "observations": observations,
        }

    keyword_groups = {
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
            "asked what",
            "what to do next",
            "now what",
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
            "don't know what bitcoin",
            "never used",
            "don't understand",
            "what is crypto",
            "how does this work",
            "first time",
            "confused",
            "what is this machine",
            "voucher",
            "gift card",
            "wire transfer",
            "money order",
            "moneygram",
        ],
    }

    triggered_groups = set()
    for obs in observations:
        obs_lower = obs.lower()
        for group_name, keywords in keyword_groups.items():
            for kw in keywords:
                if kw.lower() in obs_lower:
                    triggered_groups.add(group_name)
                    break

    triggered_list = list(triggered_groups)
    num_triggered = len(triggered_list)

    severity = "LOW"

    # CRITICAL logic
    if (
        "SECRECY" in triggered_groups
        or ("PHONE_DIRECTION" in triggered_groups and "FEAR" in triggered_groups)
        or num_triggered >= 4
    ):
        severity = "CRITICAL"
    # HIGH logic
    elif (
        num_triggered == 3
        or ("PHONE_DIRECTION" in triggered_groups and "LARGE_AMOUNT" in triggered_groups)
        or "AUTHORITY" in triggered_groups
    ):
        severity = "HIGH"
    # MEDIUM logic
    elif num_triggered == 2 or (classification == "SUSPICIOUS" and num_triggered <= 1):
        severity = "MEDIUM"
    # LOW logic
    else:
        severity = "LOW"

    return {
        "severity": severity,
        "triggered_groups": triggered_list,
        "observation_count": len(observations),
        "classification": classification,
        "observations": observations,
    }
