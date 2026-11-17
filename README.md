# FluxGuard-Rx

A human-in-the-loop clinical order triage prototype using multiple LLM agents. Built with standard Python—no complex frameworks or heavy libraries.

---

## ⚠️ Disclaimer

- **Prototype & Synthetic Data Only**: For research/testing purposes; not medical advice.
- **Never Auto-Approves**: FluxGuard-Rx strictly triages orders for human clinician review. A licensed clinician must always make the final prescribing decision.

---

## How It Works

Three specialized agents evaluate each medication order (Semaglutide):

1. **`ContraindicationAgent`**: Checks for pregnancy, thyroid cancer history (personal/family MTC or MEN 2), pancreatitis history, and drug interactions (sulfonylureas, insulin).
2. **`DoseAgent`**: Checks starting dose (0.25 mg weekly), titration schedule, and flags titration skips or blocks overdoses (> 2.4 mg weekly).
3. **`SupervisorAgent`**: Combines both assessments. **Never approves**. Outputs only:
   - `Ready for human review` — Both checks clean; ready for physician review.
   - `Flagged` — Clinical precaution or drug interaction needing review.
   - `Blocked` — Absolute contraindication or unsafe dose.

---

## Architecture Flow

```text
SQLite (25 Patients)
       │
       ├──► ContraindicationAgent ──┐
       │                            ▼
       └──► DoseAgent ────────────► SupervisorAgent ──► report.html
                                    (Never Approves)
```

---

## Tech Stack

- **Python**: Standard library (`sqlite3`, `json`, `re`, `time`, `requests`, `dotenv`).
- **Database**: SQLite (`fluxguard_rx.db`).
- **LLM API**: Groq Cloud API.
  - Models used: `openai/gpt-oss-20b` (default in code), `qwen/qwen3.8-27b`.

---

## Setup

No complex setup or `pip install` required.

1. Ensure Python 3.10+ is installed.
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Add your Groq API key in `.env`:
   ```env
   GROQ_API_KEY="your_groq_api_key_here"
   GROQ_MODEL="openai/gpt-oss-20b"
   ```

---

## How to Run

```bash
# 1. Initialize SQLite DB with 25 synthetic patients
python3 db.py

# 2. Test live agent connectivity (makes 1 real call per agent, prints raw responses)
python3 check_live.py

# 3. Run evaluation suite (15 labeled test cases with accuracy scoring)
python3 eval.py

# 4. Run triage pipeline on all 25 patients and generate report.html
python3 main.py
```

Open `report.html` in any browser to view the interactive triage table with filter tabs.

---

## Evaluation (`eval.py`)

- Contains **15 ground-truth clinical test cases** (5 Clean, 5 Contraindicated, 5 Clinical Precaution).
- The pipeline processes each test case live with the LLM and reports accuracy, category breakdown, and any prompt regression mismatches.

---

## Guardrails & Limitations

- **No Mocks**: Every agent makes a real LLM API call over HTTP. If a call fails, it stops and surfaces the actual error.
- **Audit Logging**: Every prompt, raw response, model, and latency is appended to `calls.log`.
- **Rate Limits**: Subject to provider token/request limits (handled with backoff retries).
- **Human In The Loop**: LLM outputs can hallucinate; human review is mandatory.

---

## What I Would Do Next

1. **FHIR Standard**: Ingest real EHR HL7/FHIR medication orders.
2. **Async Agent Calls**: Run Contraindication and Dose agents in parallel to cut latency in half.
3. **Structured Outputs**: Use strict JSON schema validation (Pydantic / native tool calling).
