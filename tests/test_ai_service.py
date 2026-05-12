from app.modules.articles.ai_service import (
    _clamp_score,
    _normalize_analysis_item,
    _parse_json_array,
)


def test_clamp_score_bounds_and_invalid_values():
    assert _clamp_score(0.8) == 0.8
    assert _clamp_score(2) == 1.0
    assert _clamp_score(-5) == 0.0
    assert _clamp_score("invalid") == 0.0


def test_parse_json_array_supports_code_fences():
    payload = """```json
[
  {
    "relevance_score": 0.9,
    "backend_depth_score": 0.7,
    "novelty_score": 0.6,
    "actionability_score": 0.8,
    "linkedin_potential_score": 0.5,
    "final_score": 0.75,
    "decision": "keep",
    "reasoning_summary": "Solid backend architecture breakdown."
  }
]
```"""
    parsed = _parse_json_array(payload)
    assert len(parsed) == 1
    assert parsed[0]["decision"] == "keep"
    assert parsed[0]["final_score"] == 0.75


def test_normalize_analysis_item_derives_decision_when_missing():
    item = {
        "relevance_score": 0.85,
        "backend_depth_score": 0.9,
        "novelty_score": 0.7,
        "actionability_score": 0.8,
        "linkedin_potential_score": 0.6,
        "final_score": 0.9,
        "reasoning_summary": "Excellent technical depth.",
    }
    normalized = _normalize_analysis_item(item)
    assert normalized["decision"] == "keep"
    assert normalized["model_name"]
