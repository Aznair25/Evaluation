from dataclasses import dataclass

BAND_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

COMMUNICATIVE_PROFILES = {
    "A1": ("Communicateur en développement", "Developing Communicator"),
    "A2": ("Communicateur fonctionnel", "Functional Communicator"),
    "B1": ("Communicateur autonome", "Autonomous Communicator"),
    "B2": ("Communicateur avancé", "Advanced Communicator"),
    "C1": ("Communicateur expert", "Expert Communicator"),
    "C2": ("Communicateur expert", "Expert Communicator"),
}


@dataclass
class LevelDecision:
    cefr_band: str          # e.g. "B1"
    sub_level: str          # ".1" or ".2"
    cefr_level: str         # e.g. "B1.2"
    communicative_profile_fr: str
    communicative_profile_en: str
    criteria_yes_count: int
    interaction_achieved: bool


def decide_level(cefr_band: str, criteria_results: dict) -> LevelDecision:
    """
    Apply the .1/.2 rule:
    - .2 if 5 or more criteria are achieved INCLUDING interaction
    - .1 otherwise
    """
    achieved_count = sum(
        1 for v in criteria_results.values()
        if isinstance(v, dict) and v.get("achieved") is True
    )
    interaction_achieved = bool(
        criteria_results.get("interaction", {}).get("achieved", False)
    )

    if achieved_count >= 5 and interaction_achieved:
        sub_level = ".2"
    else:
        sub_level = ".1"

    cefr_level = f"{cefr_band}{sub_level}"
    profile_fr, profile_en = COMMUNICATIVE_PROFILES.get(cefr_band, ("", ""))

    return LevelDecision(
        cefr_band=cefr_band,
        sub_level=sub_level,
        cefr_level=cefr_level,
        communicative_profile_fr=profile_fr,
        communicative_profile_en=profile_en,
        criteria_yes_count=achieved_count,
        interaction_achieved=interaction_achieved,
    )


def sub_level_explanation_fr(decision: LevelDecision) -> str:
    if decision.sub_level == ".2":
        return (
            f"Le sous-niveau .2 a été attribué car l'apprenant remplit {decision.criteria_yes_count} "
            f"critères sur 6, incluant le critère Interaction."
        )
    return (
        f"Le sous-niveau .1 a été attribué car l'apprenant remplit seulement {decision.criteria_yes_count} "
        f"critères sur 6 (minimum de 5 dont Interaction requis pour le niveau .2)."
    )


def sub_level_explanation_en(decision: LevelDecision) -> str:
    if decision.sub_level == ".2":
        return (
            f"Sub-level .2 was assigned because the student meets {decision.criteria_yes_count} "
            f"out of 6 criteria, including the Interaction criterion."
        )
    return (
        f"Sub-level .1 was assigned because the student meets only {decision.criteria_yes_count} "
        f"out of 6 criteria (minimum of 5 including Interaction required for level .2)."
    )
