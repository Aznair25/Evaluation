import json
import logging
from dataclasses import dataclass

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

CEFR_LEVEL_DESCRIPTORS = {
    "A1": "Can respond to very simple questions with one-word answers or rehearsed phrases. Conveys very basic personal information. Relies on repetition. Isolated words, minimal phrases, very basic structures.",
    "A2": "Can handle short social exchanges, answer and ask simple questions on familiar topics. Describes daily routines, preferences, simple experiences. Can use simple circumlocution. Simple sentences, present tense, basic connectors.",
    "B1": "Can maintain a conversation on familiar topics, express opinions, explain reasons. Can explain opinions, narrate experiences. Can paraphrase, use synonyms. Broader vocabulary, passé composé/imparfait.",
    "B2": "Can interact spontaneously, respond to unexpected questions, manage turn-taking. Can present clear, detailed descriptions on complex subjects. Can reformulate flexibly. Abstract vocabulary, subordinate clauses, conditional, subjunctive attempts.",
    "C1": "Can participate fully in extended discourse, adjust register, manage complex exchanges. Can present nuanced ideas with precision. Can restructure arguments in real-time. Precise specialized vocabulary, complex syntax, register awareness.",
    "C2": "Complete mastery. Very advanced mastery, nuanced, flexible, adapted to any context. Rich, precise, adapted to any situation including specialized.",
}

CRITERIA_PROMPTS = {
    "interaction": {
        "name_fr": "Interaction",
        "name_en": "Interaction",
        "description": "L'apprenant répond aux questions, les relance, maintient l'échange. The learner responds, asks questions, and maintains the conversation.",
        "focus": "Assess turn-taking patterns, question-answer dynamics, initiative in conversation, ability to maintain flow.",
    },
    "clarity": {
        "name_fr": "Clarté du message",
        "name_en": "Message Clarity",
        "description": "Les idées sont compréhensibles. Ideas are comprehensible and clearly communicated.",
        "focus": "Assess idea development, coherence, logical flow, topic coverage.",
    },
    "strategies": {
        "name_fr": "Stratégies de communication",
        "name_en": "Communication Strategies",
        "description": "Reformule, cherche des alternatives, contourne les difficultés. Rephrases, finds alternatives, works around difficulties.",
        "focus": "Look for evidence of rephrasing, self-correction, circumlocution, clarification requests.",
    },
    "vocabulary": {
        "name_fr": "Vocabulaire et structures",
        "name_en": "Vocabulary & Structures",
        "description": "Variété, justesse, adéquation au niveau. Variety, accuracy, appropriateness to level.",
        "focus": "Assess tense usage, sentence complexity, vocabulary range and appropriateness. Check for passé composé, imparfait, subordinate clauses, conditional.",
    },
}


def _build_prompt(criterion_key: str, student_transcript: str, target_level: str) -> str:
    criterion = CRITERIA_PROMPTS[criterion_key]
    descriptors_text = "\n".join(
        f"- {level}: {desc}" for level, desc in CEFR_LEVEL_DESCRIPTORS.items()
    )

    return f"""You are an expert CEFR French language evaluator following the MÉTRO-LANG GRILLE D'ÉVALUATION rubric.

CRITERION: {criterion['name_en']} / {criterion['name_fr']}
DESCRIPTION: {criterion['description']}
EVALUATION FOCUS: {criterion['focus']}

CEFR LEVEL DESCRIPTORS:
{descriptors_text}

TARGET CEFR LEVEL FOR THIS EVALUATION: {target_level}

STUDENT TRANSCRIPT (student turns only):
\"\"\"
{student_transcript}
\"\"\"

Task: Evaluate whether the student achieves the criterion at the TARGET LEVEL ({target_level}).

Respond ONLY with valid JSON in this exact format:
{{
  "achieved": true or false,
  "evidence": ["specific example from transcript 1", "specific example 2"],
  "comment_fr": "1-3 sentence justification in French",
  "comment_en": "1-3 sentence justification in English",
  "highest_level_demonstrated": "A1|A2|B1|B2|C1|C2"
}}"""


def _build_level_detection_prompt(student_transcript: str) -> str:
    descriptors_text = "\n".join(
        f"- {level}: {desc}" for level, desc in CEFR_LEVEL_DESCRIPTORS.items()
    )
    return f"""You are an expert CEFR French language evaluator.

CEFR LEVEL DESCRIPTORS:
{descriptors_text}

STUDENT TRANSCRIPT (student turns only):
\"\"\"
{student_transcript}
\"\"\"

Task: Determine the highest CEFR band (A1, A2, B1, B2, C1, or C2) where the student CONSISTENTLY demonstrates competence across all aspects of oral expression (interaction, clarity, communication strategies, vocabulary & structures).

Respond ONLY with valid JSON:
{{
  "cefr_band": "B1",
  "reasoning": "Brief explanation of why this is the highest consistent band"
}}"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def evaluate_criterion(
    criterion_key: str,
    student_transcript: str,
    target_level: str,
) -> dict:
    logger.info(f"evaluate_criterion: key={criterion_key} | target_level={target_level} | transcript_chars={len(student_transcript)}")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = _build_prompt(criterion_key, student_transcript, target_level)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    result = json.loads(content)
    logger.info(f"evaluate_criterion '{criterion_key}': achieved={result.get('achieved')} | highest_level={result.get('highest_level_demonstrated', 'N/A')}")
    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def detect_cefr_band(student_transcript: str) -> str:
    """Detect the highest CEFR band from transcript using GPT-4o."""
    logger.info(f"detect_cefr_band: transcript_chars={len(student_transcript)}")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = _build_level_detection_prompt(student_transcript)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    content = response.choices[0].message.content
    result = json.loads(content)
    band = result.get("cefr_band", "B1")
    logger.info(f"detect_cefr_band result: band={band} | reasoning={result.get('reasoning', '')[:120]!r}")
    return band
