# FluxGuard-Rx

> A human-in-the-loop clinical order triage prototype using multiple LLM agents.

---

## Disclaimer

> [!WARNING]
> **Research and Prototyping Use Only**
> This project uses purely **synthetic patient data** and is designed strictly as an engineering prototype. It does **not** provide medical advice, diagnosis, or clinical recommendations.
> 
> **Core Safety Invariant**: FluxGuard-Rx **never auto-approves** prescriptions. Every medication order must be evaluated and signed off by a licensed human healthcare provider.

---

## How It Works

FluxGuard-Rx evaluates medication requests (focusing on Semaglutide GLP-1 receptor agonist orders) using three specialized LLM agents:

1. **`ContraindicationAgent`**
   - Evaluates patient demographics, pregnancy status, thyroid history, and concurrent medications.
   - **Blocks** on absolute contraindications: active pregnancy/breastfeeding, personal or family history of Medullary Thyroid Carcinoma (MTC), or Multiple Endocrine Neoplasia syndrome type 2 (MEN 2).
   - **Flags** on major precautions: concurrent use with sulfonylureas or insulin (severe hypoglycemia risk), prior history of pancreatitis, or significant renal impairment.
   - **Passes** if no clinical contraindications or high-risk interactions are identified.

2. **`DoseAgent`**
   - Evaluates requested dose magnitude and titration schedule against clinical dosing guidelines.
   - **Blocks** dangerous supra-therapeutic overdoses exceeding maximum clinical limits (> 2.4 mg weekly).
   - **Flags** protocol deviations, such as treatment-naïve patients initiating directly on high maintenance doses (> 0.5 mg weekly) bypassing initiation.
   - **Passes** standard initiation (0.25 mg weekly) and gradual titration steps (0.5 mg, 1.0 mg, 1.7 mg, 2.4 mg weekly).

3. **`SupervisorAgent`**
   - Combines the independent outputs from `ContraindicationAgent` and `DoseAgent`.
   - Strictly enforces the Human-In-The-Loop (HITL) protocol: **never approves orders**.
   - Outputs strictly one of three triage routing statuses with a concise clinical rationale:
     - `Ready for human review` — Both checks passed clean; prepared for physician evaluation and sign-off.
     - `Flagged` — Clinical risks, drug-drug interactions, or titration adjustments requiring clinician review.
     - `Blocked` — Absolute contraindications or unsafe overdoses requiring clinical intervention or cancellation.

---

## Architecture

```text
[ SQLite Database: fluxguard_rx.db ]
   (25 Synthetic Patient Orders)
                 |
                 v
   +---------------------------+
   |   Pipeline Orchestrator   |
   +---------------------------+
         |               |
         v               v
+------------------+   +------------------+
| Contraindication |   |    DoseAgent     |
|      Agent       |   |  (LLM Call 2)    |
|   (LLM Call 1)   |   +------------------+
+------------------+             |
         \                      /
          \                    /
           v                  v
       +--------------------------+
       |     SupervisorAgent      |
       |       (LLM Call 3)       |
       |  [Strict: Never Approve] |
       +--------------------------+
                     |
                     v  (Status + Reason)
        [ Interactive report.html ]
   (All / Ready for Review / Flagged / Blocked)
```

---

## Tech Stack

- **Python**: Standard library components (`sqlite3`, `json`, `re`, `time`, `datetime`, `os`).
- **Database**: SQLite (`fluxguard_rx.db`).
- **LLM API**: Groq Cloud API (OpenAI-compatible chat completions interface).
- **Models Used in Code**:
  - `openai/gpt-oss-20b` (Default configured in `llm_client.py`)
  - `qwen/qwen3.8-27b` (Supported via `GROQ_MODEL` environment variable)
  - `gpt-4o-mini` (Fallback when `OPENAI_API_KEY` is provided)

---

## Setup

### Prerequisites
- Python 3.10+
- A Groq API key

### Configuration
1. Clone or navigate to the repository directory:
   ```bash
   cd fluxguard-rx
   ```
2. Copy the example environment file and configure your API key:
   ```bash
   cp .env.example .env
   ```
3. Set your Groq API key in `.env`:
   ```bash
   GROQ_API_KEY="your_groq_api_key_here"
   GROQ_MODEL="openai/gpt-oss-20b"
   ```
   *(No extra `pip install` required if running in standard Python environments with `requests` and `python-dotenv`).*

---

## Running the Project

### 1. Initialize SQLite Database
Creates `fluxguard_rx.db` and populates 25 synthetic patient records across diverse clinical profiles:
```bash
python3 db.py
```

### 2. Verify Live Agent Connectivity (`check_live.py`)
Executes 1 live call per agent, verifies JSON parsing and the "NEVER APPROVE" guardrail, prints raw LLM responses to the console, and logs latency:
```bash
python3 check_live.py
```

### 3. Run Benchmark Suite (`eval.py`)
Runs 15 labeled benchmark test cases against the pipeline and computes classification accuracy:
```bash
python3 eval.py
```

### 4. Run Full Batch Triage & Generate Report (`main.py`)
Runs all 25 SQLite patient orders through the 3-agent pipeline and generates `report.html`:
```bash
python3 main.py
```
Open `report.html` in your browser to inspect the interactive triage dashboard, filterable by tabs (`All Orders`, `Ready for Review`, `Flagged`, `Blocked`).

---

## Evaluation Suite

`eval.py` provides regression testing across **15 labeled ground-truth clinical test cases**:
- **5 Clean Cases** (Standard 0.25 mg initiation, appropriate titration, benign thyroid nodule) $\rightarrow$ Expected: `Ready for human review`
- **5 Contraindicated Cases** (Active pregnancy, personal MTC history, family MEN 2 history, 5 mg and 10 mg weekly overdoses) $\rightarrow$ Expected: `Blocked`
- **5 Clinical Risk Cases** (Sulfonylurea interactions, basal insulin risk, history of pancreatitis, skipping titration to 2.4 mg, stage 3 CKD) $\rightarrow$ Expected: `Flagged`

The suite runs each case through the live 3-agent pipeline, compares predicted vs. expected triage status, prints per-case latency, category-level breakdowns, and highlights any mismatch regressions.

---

## Guardrails and Limitations

- **No Mocks or Simulated Outputs**: Every agent makes a real LLM API call over the network. If an API call fails or quota is exhausted, the pipeline reports the real error rather than falling back to synthetic responses.
- **Audit Logging**: Every API transaction is logged to `calls.log` with timestamp, agent name, model, system prompt, user prompt, raw response, and latency.
- **Rate Limits**: Free-tier API keys operate under strict token and request limits (e.g., TPM/RPM quotas). `llm_client.py` includes exponential backoff and rate-limit retry handling.
- **Probabilistic Output**: LLM outputs can hallucinate or misinterpret clinical nuances.
- **Mandatory HITL Review**: Automated classification is an assistive sorting mechanism only. A licensed clinician must always inspect the patient chart and make the final prescribing decision.

---

## What I Would Do Next

1. **FHIR / EHR Integration**: Replace the SQLite schema with HL7 FHIR `Patient`, `MedicationRequest`, and `Condition` resource parsers for real-world electronic health record interoperability.
2. **Parallel Agent Execution**: Run `ContraindicationAgent` and `DoseAgent` concurrently via `asyncio` or worker pools to halve end-to-end triage latency before reaching `SupervisorAgent`.
3. **Structured Outputs & Schema Validation**: Utilize provider-native structured JSON schemas (`response_format` with JSON Schema / Pydantic models) to eliminate regex fallbacks and guarantee schema adherence.
