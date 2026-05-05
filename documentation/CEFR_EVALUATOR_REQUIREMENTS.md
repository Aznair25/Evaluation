# CEFR Oral Expression Evaluator — Requirements Document

## 1. Project Overview

A standalone service that evaluates a student's **oral French proficiency** based on a recorded interview. The system accepts an audio recording of a student-interviewer conversation and produces a **CEFR level assessment (A1.1 – C2.2)** across six evaluation criteria, following the official **MÉTRO-LANG GRILLE D'ÉVALUATION** rubric.

### 1.1 Objective

Given an interview recording (audio file), the system must:

1. **Transcribe** the audio with speaker diarization (student vs. interviewer)
2. **Extract the student's audio** segments separately from the interviewer's
3. **Evaluate** the student's performance across **6 criteria** using a hybrid approach (LLM + audio analysis)
4. **Determine** the student's highest CEFR level and sub-level (e.g., B1.2) automatically by applying the official `.1/.2 decision rule` without requiring a pre-defined target level.
5. **Generate** a bilingual (French + English) PDF evaluation report.
6. **Secure** the platform with Google Authentication for user access.

### 1.2 Target Users

- Language schools and evaluation centres administering oral French assessments
- Teachers who record student interviews and need standardized CEFR scoring
- Institutional programs (e.g., immigrant integration, professional French certification)

---

## 2. Functional Requirements

### 2.1 Input

| Requirement | Description |
|-------------|-------------|
| **FR-INPUT-01** | System accepts audio file upload in common formats: **MP3, WAV, OGG, FLAC, M4A, WebM** |
| **FR-INPUT-02** | Audio must contain a **two-speaker conversation** (student + interviewer) |
| **FR-INPUT-03** | Minimum audio duration: **60 seconds** of student speech |
| **FR-INPUT-04** | Maximum audio duration: **30 minutes** |
| **FR-INPUT-05** | Target language: **French** (primary), English (secondary support) |
| **FR-INPUT-06** | User may optionally provide metadata: student name, date, evaluator name, institution, topic |

### 2.2 Processing Pipeline

```
Audio Upload
    │
    ▼
┌─────────────────────────────┐
│  Stage 1: Transcription     │
│  • Speech-to-text (ASR)     │
│  • Speaker diarization      │
│  • Word-level timestamps    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Stage 2: Audio Extraction  │
│  • Isolate student segments │
│  • Concatenate into single  │
│    student-only audio file  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Stage 3: Parallel Criterion Evaluation     │
│                                             │
│  ┌─── Transcript-based (LLM) ───┐          │
│  │ 1. Interaction                │          │
│  │ 2. Clarté du message          │          │
│  │ 3. Stratégies de communication│          │
│  │ 4. Vocabulaire et structures  │          │
│  └───────────────────────────────┘          │
│                                             │
│  ┌─── Audio-based (Azure Speech) ──┐       │
│  │ 5. Fluidité et aisance          │       │
│  │ 6. Prononciation                │       │
│  └─────────────────────────────────┘       │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Stage 4: Level Decision    │
│  • Apply .1/.2 rule         │
│  • Assign communicative     │
│    profile                  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Stage 5: Report Generation │
│  • Bilingual PDF (FR + EN)  │
│  • Upload to storage        │
└─────────────────────────────┘
```

#### FR-PROC-01: Transcription

- Use a high-accuracy ASR service (e.g., Deepgram, Azure Speech) for French speech recognition
- Produce **word-level timestamps** and **confidence scores** for each word
- Perform **speaker diarization** to distinguish student from interviewer
- Output a structured transcript with per-utterance speaker labels

#### FR-PROC-02: Student Audio Extraction

- Using diarized timestamps, extract **only the student's speaking segments** from the recording
- Concatenate student segments into a single clean audio file
- This student-only audio is the sole input to the Azure Speech pronunciation/fluency analysis
- The interviewer's voice must **never** be sent to the pronunciation API (it would corrupt scoring)

#### FR-PROC-03: Criterion Evaluation

Evaluate the student against **6 criteria** from the MÉTRO-LANG GRILLE D'ÉVALUATION:

| # | Criterion (FR) | Criterion (EN) | Evaluation Method |
|---|---------------|-----------------|-------------------|
| 1 | **Interaction** | Interaction | Transcript → LLM |
| 2 | **Clarté du message** | Message Clarity | Transcript → LLM |
| 3 | **Stratégies de communication** | Communication Strategies | Transcript → LLM |
| 4 | **Vocabulaire et structures** | Vocabulary & Structures | Transcript → LLM |
| 5 | **Fluidité et aisance** | Fluency & Ease | Student audio → Azure Speech |
| 6 | **Prononciation** | Pronunciation | Student audio → Azure Speech |

Each criterion must produce:
- **Achieved**: Yes / No (for the determined target level)
- **Evidence**: Specific examples from transcript or audio metrics
- **Comment**: 1–3 sentence justification in both French and English

#### FR-PROC-04: Level Determination

The system must independently determine the student's highest level of proficiency using the following logic:

1. **Iterative Assessment**: The LLM evaluates the transcript against descriptors for all bands (A1 to C2) to identify the **highest CEFR band** where the student consistently demonstrates competence.
2. **Apply the .1/.2 sub-level rule**:
   - The system checks if the student meets the "solid mastery" requirements for the identified band.
   - **Level .2** (e.g., B1.2) is assigned if 5 or more criteria are "Yes" **including Interaction**.
   - Otherwise, the student is assigned **Level .1** (e.g., B1.1).
3. **No Target Input**: The system does NOT require a target level to be provided; the assessment is holistic and starts from the evidence found in the audio.
4. **Assign communicative profile** based on level band:

| Level Range | Profile (FR) | Profile (EN) |
|-------------|-------------|--------------|
| A1 – A2 | Communicateur en développement | Developing Communicator |
| A2 – B1 | Communicateur fonctionnel | Functional Communicator |
| B1 – B2 | Communicateur autonome | Autonomous Communicator |
| B2 – C1 | Communicateur avancé | Advanced Communicator |
| C1 – C2 | Communicateur expert | Expert Communicator |

### 2.4 Authentication & User Management

| Requirement | Description |
|-------------|-------------|
| **FR-AUTH-01** | **Google OAuth 2.0 Integration**: Users must log in/sign up using their Google accounts. |
| **FR-AUTH-02** | **Session Management**: Secure JWT-based or session-based authentication for all API requests. |
| **FR-AUTH-03** | **User Profile**: Store basic user info (name, email, profile picture) retrieved from Google. |
| **FR-AUTH-04** | **History Tracking**: Users can view and download their previous evaluation reports. |

### 2.3 Output

#### FR-OUT-01: Bilingual PDF Report

A single PDF document with two sections:

**Section 1 — French (GRILLE D'ÉVALUATION MÉTRO-LANG):**
- Informations générales (nom, date, évaluateur, institution)
- Niveau global + sous-niveau (e.g., B1.2)
- Profil communicatif
- Tableau des 6 critères: Oui/Non + commentaires justificatifs
- Attribution du sous-niveau (explication de la règle .1/.2)
- Commentaire global (forces, pistes d'amélioration, prochaines étapes)

**Section 2 — English (MÉTRO-LANG EVALUATION GRID):**
- General information (name, date, evaluator, institution)
- Overall level + sub-level
- Communicative profile
- 6-criteria table: Yes/No + justification comments
- Sub-level attribution (explanation of .1/.2 rule)
- Global comment (strengths, areas for improvement, next steps)

#### FR-OUT-02: Structured JSON Response

In addition to the PDF, the API must return structured JSON containing:

```json
{
  "evaluation_id": "uuid",
  "cefr_level": "B1.2",
  "sub_level_rule": ".2",
  "communicative_profile": "Communicateur autonome",
  "criteria": {
    "interaction": {
      "achieved": true,
      "evidence": ["Maintains exchange", "Asks follow-up questions"],
      "comment_fr": "...",
      "comment_en": "..."
    },
    "clarity": { "achieved": true, "..." : "..." },
    "strategies": { "achieved": false, "..." : "..." },
    "vocabulary": { "achieved": true, "..." : "..." },
    "fluency": {
      "achieved": true,
      "azure_scores": {
        "fluency_score": 72.5,
        "prosody_score": 68.0
      },
      "comment_fr": "...",
      "comment_en": "..."
    },
    "pronunciation": {
      "achieved": true,
      "azure_scores": {
        "pronunciation_score": 78.3,
        "accuracy_score": 80.1,
        "completeness_score": 85.0
      },
      "comment_fr": "...",
      "comment_en": "..."
    }
  },
  "global_comment_fr": "...",
  "global_comment_en": "...",
  "report_url": "https://s3.../evaluation_report.pdf",
  "transcript": "...",
  "audio_duration_seconds": 342.5,
  "student_speaking_duration_seconds": 185.2
}
```

#### FR-OUT-03: Report Security

- PDF format is intentionally chosen to prevent student modification of evaluation results
- Reports must be stored securely (S3 with controlled access)

---

## 3. Evaluation Criteria Detail

### 3.1 Criterion 1 — Interaction

> **FR**: L'apprenant répond aux questions, les relance, maintient l'échange
> **EN**: The learner responds, asks questions, and maintains the conversation

| Level | Descriptor |
|-------|-----------|
| A1 | Can respond to very simple questions with one-word answers or rehearsed phrases |
| A2 | Can handle short social exchanges, answer and ask simple questions on familiar topics |
| B1 | Can maintain a conversation on familiar topics, express opinions, explain reasons |
| B2 | Can interact spontaneously, respond to unexpected questions, manage turn-taking |
| C1 | Can participate fully in extended discourse, adjust register, manage complex exchanges |

**Evaluation method**: LLM analysis of full dialogue transcript. Assess turn-taking patterns, question-answer dynamics, initiative in conversation, ability to maintain flow.

### 3.2 Criterion 2 — Clarté du message (Message Clarity)

> **FR**: Les idées sont compréhensibles
> **EN**: Ideas are comprehensible and clearly communicated

| Level | Descriptor |
|-------|-----------|
| A1 | Can convey very basic personal information (name, age, nationality) |
| A2 | Can describe daily routines, preferences, simple experiences |
| B1 | Can explain opinions, narrate experiences, describe plans with coherent structure |
| B2 | Can present clear, detailed descriptions on complex subjects, develop arguments |
| C1 | Can present nuanced ideas with precision, structure complex arguments logically |

**Evaluation method**: LLM analysis of student utterances. Assess idea development, coherence, logical flow, topic coverage.

### 3.3 Criterion 3 — Stratégies de communication (Communication Strategies)

> **FR**: Reformule, cherche des alternatives, contourne les difficultés
> **EN**: Rephrases, finds alternatives, works around difficulties

| Level | Descriptor |
|-------|-----------|
| A1 | Relies on repetition and gestures; cannot reformulate |
| A2 | Can use simple circumlocution for unknown words |
| B1 | Can paraphrase, use synonyms, ask for help when needed |
| B2 | Can reformulate flexibly, use a range of strategies to repair communication |
| C1 | Can restructure arguments in real-time, adapt communication approach fluidly |

**Evaluation method**: LLM analysis of transcript for evidence of rephrasing, self-correction, circumlocution, clarification requests.

### 3.4 Criterion 4 — Vocabulaire et structures (Vocabulary & Structures)

> **FR**: Variété, justesse, adéquation au niveau
> **EN**: Variety, accuracy, appropriateness to level

| Level | Descriptor |
|-------|-----------|
| A1 | Isolated words, minimal phrases, very basic structures (être, avoir) |
| A2 | Simple sentences (S+V+O), present tense, basic connectors (et, mais) |
| B1 | Broader vocabulary, passé composé/imparfait, more connectors (parce que, donc) |
| B2 | Abstract vocabulary, subordinate clauses, conditional, subjunctive attempts |
| C1 | Precise specialized vocabulary, complex syntax, register awareness |

**Evaluation method**: LLM analysis of student utterances against level-specific grammar objectives checklist. Assess tense usage, sentence complexity, vocabulary range and appropriateness.

### 3.5 Criterion 5 — Fluidité et aisance (Fluency & Ease)

> **FR**: Débit continu, pauses appropriées, enchaînement des idées
> **EN**: Continuous speech, appropriate pauses, idea linking

| Azure Speech Metric | What it measures | CEFR Relevance |
|---------------------|-----------------|----------------|
| **Fluency Score** (0–100) | Speech rate, pauses, hesitations | Direct fluency indicator |
| **Prosody Score** (0–100) | Rhythm, intonation, stress patterns | Natural flow of speech |

**Evaluation method**: Azure Speech Pronunciation Assessment API on student-only audio. Map scores to CEFR level using calibrated thresholds.

### 3.6 Criterion 6 — Prononciation (Pronunciation)

> **FR**: Intelligibilité, rythme, accent
> **EN**: Intelligibility, rhythm, accent

| Azure Speech Metric | What it measures | CEFR Relevance |
|---------------------|-----------------|----------------|
| **Pronunciation Score** (0–100) | Overall pronunciation quality | Primary indicator |
| **Accuracy Score** (0–100) | Phonetic correctness per word | Precision of sounds |
| **Completeness Score** (0–100) | Whether all words were fully pronounced | Articulation completeness |

**Evaluation method**: Azure Speech Pronunciation Assessment API on student-only audio. Map scores to CEFR level using calibrated thresholds.

---

## 4. CEFR Level Framework

The system must evaluate across 12 sub-levels. The full descriptor for each level is defined in the MÉTRO-LANG synthesis table:

| Level | Description |
|-------|-----------|
| **A1.1** | Isolated words, very simple formulaic responses, guided answers |
| **A1.2** | Short phrases about daily life, simple interactions |
| **A2.1** | Describes activities, needs, preferences with simple phrases |
| **A2.2** | Simple opinions, short narratives, predictable exchanges |
| **B1.1** | Explains reasons, discusses projects, sustains simple conversation |
| **B1.2** | Simple arguments, more detailed discourse, increasing ease |
| **B2.1** | Argues clearly, nuances ideas, interacts spontaneously |
| **B2.2** | Expresses with ease on varied topics, defends viewpoints, adapts discourse |
| **C1.1** | Fluid, detailed, precise expression on varied topics |
| **C1.2** | Finely adapts discourse to context with high precision |
| **C2.1** | Very advanced mastery, nuanced, flexible, adapted to any context |
| **C2.2** | Complete mastery, rich, precise, adapted to any situation including specialized |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Requirement | Target |
|-------------|--------|
| **NFR-PERF-01** | End-to-end processing time: **< 3 minutes** for a 15-minute recording |
| **NFR-PERF-02** | Parallel criterion evaluation (all 6 criteria evaluated concurrently) |
| **NFR-PERF-03** | PDF generation: **< 5 seconds** |

### 5.2 Accuracy

| Requirement | Target |
|-------------|--------|
| **NFR-ACC-01** | CEFR level determination within **±1 sub-level** of expert human assessment |
| **NFR-ACC-02** | Speaker diarization accuracy: **> 90%** correct speaker attribution |
| **NFR-ACC-03** | Transcription word error rate (WER): **< 15%** for French speech |

### 5.3 Security

| Requirement | Description |
|-------------|-------------|
| **NFR-SEC-01** | Audio files encrypted at rest and in transit |
| **NFR-SEC-02** | PDF reports are non-editable by students |
| **NFR-SEC-03** | Audio files deleted after processing (configurable retention) |
| **NFR-SEC-04** | API endpoints require authentication |

### 5.4 Reliability

| Requirement | Description |
|-------------|-------------|
| **NFR-REL-01** | Graceful failure handling — partial results returned if one criterion fails |
| **NFR-REL-02** | Retry logic for external API calls (Azure, OpenAI, ASR) |
| **NFR-REL-03** | Evaluation status tracking with SSE progress updates |

### 5.5 Scalability

| Requirement | Description |
|-------------|-------------|
| **NFR-SCALE-01** | Support concurrent evaluations (queue-based processing) |
| **NFR-SCALE-02** | Stateless processing — no in-memory state between requests |

---

## 6. API Specification

### 6.1 Upload & Evaluate

```
POST /api/cefr-evaluator/evaluate
Content-Type: multipart/form-data

Fields:
  audio_file:       binary (required) — MP3/WAV/OGG/FLAC/M4A/WebM
  language:         string (default: "fr") — target language
  student_name:     string (optional) — for the report
  evaluator_name:   string (optional) — for the report
  institution:      string (optional) — for the report
  date:             string (optional) — evaluation date

Response: 202 Accepted
{
  "evaluation_id": "uuid",
  "status": "processing",
  "message": "Evaluation started. Use evaluation_id to track progress."
}
```

### 6.2 Check Status

```
GET /api/cefr-evaluator/evaluations/{evaluation_id}/status

Response: 200 OK
{
  "evaluation_id": "uuid",
  "status": "analyzing",          // pending | transcribing | analyzing | completed | failed
  "progress_percentage": 65,
  "current_step": "Evaluating pronunciation..."
}
```

### 6.3 Get Results

```
GET /api/cefr-evaluator/evaluations/{evaluation_id}

Response: 200 OK
{
  "evaluation_id": "uuid",
  "cefr_level": "B1.2",
  "criteria": { ... },            // Full 6-criteria results
  "report_url": "https://...",    // Bilingual PDF download URL
  "transcript": "...",
  "status": "completed"
}
```

### 6.4 Progress Stream (SSE)

```
GET /api/cefr-evaluator/evaluations/{evaluation_id}/events

Response: text/event-stream
data: {"status": "transcribing", "progress_percentage": 15, "current_step": "Transcribing audio..."}
data: {"status": "analyzing", "progress_percentage": 45, "current_step": "Evaluating interaction..."}
data: {"status": "completed", "progress_percentage": 100, "cefr_level": "B1.2"}
```

---

## 7. Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **ASR / Transcription** | Deepgram Nova-3 or Azure Speech | Speech-to-text with diarization |
| **Speaker Diarization** | Deepgram diarization or pyannote | Separate student from interviewer |
| **Audio Processing** | FFmpeg | Extract student audio segments |
| **Pronunciation / Fluency** | Azure Speech Pronunciation Assessment API | Criteria 5 & 6 scoring |
| **Transcript Criteria** | OpenAI GPT-4o (JSON mode) | Criteria 1–4 scoring |
| **PDF Generation** | python-docx + LibreOffice or ReportLab | Bilingual report from template |
| **Storage** | AWS S3 | Audio files, transcripts, PDF reports |
| **Frontend / Client** | React (with Vite or Next.js) | Modern, responsive dashboard for file uploads and report viewing |
| **Styling** | Vanilla CSS or Tailwind CSS | Premium, professional UI design |
| **Authentication** | Google OAuth 2.0 | Secure social login/signup |
| **Backend** | Python / FastAPI | API server |
| **Database** | PostgreSQL | Evaluation records, results |
| **Task Queue** | asyncio / Celery (for scale) | Background processing |

---

## 8. Dependencies on External Services

| Service | Usage | Required Credentials |
|---------|-------|---------------------|
| **Azure Speech** | Pronunciation Assessment API for criteria 5 & 6 | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` |
| **OpenAI** | GPT-4o for transcript-based criteria 1–4 evaluation | `OPENAI_API_KEY` |
| **ASR Provider** | Transcription with word-level timestamps and diarization | `DEEPGRAM_API_KEY` or Azure Speech key |
| **AWS S3** | File storage (audio, transcripts, PDF reports) | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |

---

## 9. Glossary

| Term | Definition |
|------|-----------|
| **CEFR** | Common European Framework of Reference for Languages |
| **MÉTRO-LANG** | The client's language assessment framework and rubric system |
| **GRILLE D'ÉVALUATION** | The official evaluation grid (6 criteria) used for assessment |
| **Sub-level** | The .1 or .2 designation within a CEFR band (e.g., B1.1 vs B1.2) |
| **Diarization** | The process of identifying who spoke when in a multi-speaker recording |
| **ASR** | Automatic Speech Recognition — converting audio to text |
| **Communicative Profile** | A qualitative label assigned based on the CEFR band (e.g., "Communicateur autonome") |
| **Azure Speech Pronunciation Assessment** | Microsoft's API for evaluating pronunciation, fluency, and prosody |
