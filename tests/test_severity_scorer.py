from severity_scorer import score_severity


def test_critical_four_or_more_groups():
    result = score_severity(
        {"classification": "SUSPICIOUS", "observations": ["warrant", "panic", "what to do next", "starts with"]}
    )
    assert result["severity"] == "CRITICAL"
    assert len(result["triggered_groups"]) >= 4


def test_critical_secrecy_alone():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["told not to tell anyone"]})
    assert result["severity"] == "CRITICAL"
    assert "SECRECY" in result["triggered_groups"]


def test_critical_phone_direction_plus_fear():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["told to", "panic"]})
    assert result["severity"] == "CRITICAL"
    assert "PHONE_DIRECTION" in result["triggered_groups"]
    assert "FEAR" in result["triggered_groups"]


def test_high_three_groups():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["panic", "starts with", "police"]})
    assert result["severity"] == "HIGH"
    assert len(result["triggered_groups"]) == 3


def test_high_phone_direction_plus_large_amount():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["instructed", "large sum"]})
    assert result["severity"] == "HIGH"
    assert "PHONE_DIRECTION" in result["triggered_groups"]
    assert "LARGE_AMOUNT" in result["triggered_groups"]


def test_high_authority_alone():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["police"]})
    assert result["severity"] == "HIGH"
    assert "AUTHORITY" in result["triggered_groups"]


def test_medium_two_groups():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["panic", "starts with"]})
    assert result["severity"] == "MEDIUM"
    assert len(result["triggered_groups"]) == 2


def test_medium_suspicious_one_group():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["panic"]})
    assert result["severity"] == "MEDIUM"
    assert len(result["triggered_groups"]) == 1


def test_medium_suspicious_zero_groups():
    result = score_severity({"classification": "SUSPICIOUS", "observations": []})
    assert result["severity"] == "MEDIUM"
    assert len(result["triggered_groups"]) == 0


def test_low_clean_zero_groups():
    result = score_severity({"classification": "CLEAN", "observations": []})
    assert result["severity"] == "LOW"
    assert len(result["triggered_groups"]) == 0


def test_low_clean_one_group():
    result = score_severity({"classification": "CLEAN", "observations": ["panic"]})
    assert result["severity"] == "LOW"
    assert len(result["triggered_groups"]) == 1


def test_keyword_matching_is_case_insensitive():
    for word in ["WARRANT", "warrant", "Warrant"]:
        result = score_severity({"classification": "SUSPICIOUS", "observations": [word]})
        assert "AUTHORITY" in result["triggered_groups"]


def test_keyword_matching_is_substring():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["the officer told me"]})
    assert "AUTHORITY" in result["triggered_groups"]


def test_no_cross_contamination():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["I used my wallet app"]})
    assert "WALLET_DICTATION" in result["triggered_groups"]
    assert "SECRECY" not in result["triggered_groups"]
    assert "FEAR" not in result["triggered_groups"]


def test_empty_observations():
    result = score_severity({"classification": "CLEAN", "observations": []})
    assert result["severity"] == "LOW"
    assert len(result["triggered_groups"]) == 0


def test_output_structure():
    result = score_severity({"classification": "CLEAN", "observations": []})
    assert set(result.keys()) == {"severity", "triggered_groups", "observation_count", "classification", "observations"}


def test_triggered_groups_are_deduplicated():
    result = score_severity({"classification": "SUSPICIOUS", "observations": ["warrant", "police"]})
    assert result["triggered_groups"].count("AUTHORITY") == 1
