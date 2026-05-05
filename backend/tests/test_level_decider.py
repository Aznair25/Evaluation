import pytest
from app.services.level_decider import decide_level, sub_level_explanation_fr, sub_level_explanation_en


def make_criteria(achieved_keys: list[str], all_keys=None) -> dict:
    if all_keys is None:
        all_keys = ["interaction", "clarity", "strategies", "vocabulary", "fluency", "pronunciation"]
    return {k: {"achieved": k in achieved_keys} for k in all_keys}


def test_level_2_when_5_criteria_including_interaction():
    criteria = make_criteria(["interaction", "clarity", "strategies", "vocabulary", "fluency"])
    decision = decide_level("B1", criteria)
    assert decision.sub_level == ".2"
    assert decision.cefr_level == "B1.2"


def test_level_2_when_all_6_criteria():
    criteria = make_criteria(["interaction", "clarity", "strategies", "vocabulary", "fluency", "pronunciation"])
    decision = decide_level("B2", criteria)
    assert decision.sub_level == ".2"
    assert decision.cefr_level == "B2.2"


def test_level_1_when_5_criteria_without_interaction():
    criteria = make_criteria(["clarity", "strategies", "vocabulary", "fluency", "pronunciation"])
    decision = decide_level("B1", criteria)
    assert decision.sub_level == ".1"
    assert decision.cefr_level == "B1.1"


def test_level_1_when_only_4_criteria():
    criteria = make_criteria(["interaction", "clarity", "strategies", "vocabulary"])
    decision = decide_level("A2", criteria)
    assert decision.sub_level == ".1"
    assert decision.cefr_level == "A2.1"


def test_level_1_when_no_criteria():
    criteria = make_criteria([])
    decision = decide_level("A1", criteria)
    assert decision.sub_level == ".1"
    assert decision.cefr_level == "A1.1"


def test_communicative_profile_b1():
    criteria = make_criteria(["interaction", "clarity", "strategies", "vocabulary", "fluency"])
    decision = decide_level("B1", criteria)
    assert "autonome" in decision.communicative_profile_fr.lower()
    assert "Autonomous" in decision.communicative_profile_en


def test_communicative_profile_c2():
    criteria = make_criteria(["interaction", "clarity", "strategies", "vocabulary", "fluency"])
    decision = decide_level("C2", criteria)
    assert "expert" in decision.communicative_profile_fr.lower()


def test_explanation_fr_level_2():
    criteria = make_criteria(["interaction", "clarity", "strategies", "vocabulary", "fluency"])
    decision = decide_level("B1", criteria)
    explanation = sub_level_explanation_fr(decision)
    assert ".2" in explanation
    assert "5" in explanation


def test_explanation_fr_level_1():
    criteria = make_criteria(["clarity", "strategies", "vocabulary", "fluency", "pronunciation"])
    decision = decide_level("B1", criteria)
    explanation = sub_level_explanation_fr(decision)
    assert ".1" in explanation


def test_explanation_en_level_2():
    criteria = make_criteria(["interaction", "clarity", "strategies", "vocabulary", "fluency"])
    decision = decide_level("B1", criteria)
    explanation = sub_level_explanation_en(decision)
    assert ".2" in explanation


def test_criteria_count():
    criteria = make_criteria(["interaction", "clarity"])
    decision = decide_level("A2", criteria)
    assert decision.criteria_yes_count == 2


def test_interaction_achieved_flag():
    criteria_with = make_criteria(["interaction", "clarity"])
    decision_with = decide_level("A2", criteria_with)
    assert decision_with.interaction_achieved is True

    criteria_without = make_criteria(["clarity", "vocabulary"])
    decision_without = decide_level("A2", criteria_without)
    assert decision_without.interaction_achieved is False
