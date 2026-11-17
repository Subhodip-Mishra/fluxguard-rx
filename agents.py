"""
FluxGuard RX - Clinical Triage Multi-Agent System
Three agents:
1. ContraindicationAgent (Real LLM call 1)
2. DoseAgent (Real LLM call 2)
3. SupervisorAgent (Real LLM call 3) - NEVER APPROVE
"""

from typing import Dict, Any
from llm_client import LLMClient

class ContraindicationAgent:
    """Evaluates pregnancy, personal/family history of MTC/MEN2, pancreatitis, and drug interactions using real LLM calls."""
    def __init__(self, client: LLMClient):
        self.client = client
        self.system_prompt = """You are an automated clinical order safety check module in healthcare IT triage software.
Analyze the provided synthetic patient clinical order for contraindications and drug interactions regarding Semaglutide (GLP-1 receptor agonist).
Focus strictly on contraindications and drug-drug interactions. Dose magnitude is evaluated separately by the DoseAgent.

Rules:
1. BLOCK:
   - Pregnancy or currently pregnant: Semaglutide is strictly contraindicated (risk of embryofetal toxicity).
   - Medullary Thyroid Carcinoma (MTC): Personal OR family history is a BLACK BOX contraindication.
   - Multiple Endocrine Neoplasia syndrome type 2 (MEN 2): Personal OR family history is a BLACK BOX contraindication.
2. FLAG:
   - Concomitant use with Insulin or Sulfonylureas (glimepiride, glipizide, glyburide): High risk of severe hypoglycemia; requires clinician review and dose reduction of the secretagogue.
   - Prior history of pancreatitis: Major warning/precaution for GLP-1 agonists.
   - Significant renal impairment: Needs clinician monitoring for dehydration and renal function.
   - Benign thyroid conditions (e.g. benign nodules, hypothyroidism): Safe, but flag if documentation needs clinician verification.
3. PASS:
   - No absolute contraindications or high-risk interactions identified.

Output strictly valid JSON with this schema:
{
  "status": "PASS" | "FLAG" | "BLOCK",
  "reason": "1-2 sentence clinical explanation of findings"
}"""

    def evaluate(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = f"""Evaluate this patient order:
- Patient Name: {patient.get('name')}
- Age: {patient.get('age')}
- Pregnant: {'Yes (Confirmed pregnant)' if patient.get('is_pregnant') else 'No'}
- Thyroid Cancer History: {patient.get('thyroid_cancer_history')}
- Current Medications: {patient.get('current_meds')}
- Medical History: {patient.get('medical_history')}
- Requested Drug: {patient.get('requested_drug')}
- Dose: {patient.get('dose')}

Return JSON with status and reason."""
        result = self.client.chat_json(self.system_prompt, user_prompt, agent_name="ContraindicationAgent")
        status = result.get("status", "").upper()
        if status not in ["PASS", "FLAG", "BLOCK"]:
            status = "FLAG"
        return {"status": status, "reason": result.get("reason", "")}


class DoseAgent:
    """Evaluates the requested dose against clinical guidelines and titration schedule using real LLM calls."""
    def __init__(self, client: LLMClient):
        self.client = client
        self.system_prompt = """You are an automated pharmacy order safety check module in healthcare IT triage software.
Analyze the requested Semaglutide dose and patient treatment history against standard dosing guidelines.
Focus strictly on dose magnitude and titration schedule. Contraindications (such as pregnancy or thyroid disease) are evaluated separately by the ContraindicationAgent; do not evaluate contraindications here.

Standard Semaglutide (Subcutaneous weekly) Guidelines:
1. Initiation Dose: 0.25 mg weekly for 4 weeks -> PASS.
2. Maintenance Titration: 0.5 mg, 1.0 mg, 1.7 mg, up to maximum 2.4 mg weekly -> PASS.
3. Maximum Dose Limit: Overdoses exceeding 2.4 mg weekly (e.g., 5.0 mg, 10.0 mg weekly) -> BLOCK.
4. Titration Protocol: Treatment-naïve patient starting directly on high maintenance dose (>0.5 mg, e.g. 1.7 mg, 2.4 mg) -> FLAG.

Output strictly valid JSON with this schema:
{
  "status": "PASS" | "FLAG" | "BLOCK",
  "reason": "1-2 sentence dosing assessment"
}"""

    def evaluate(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = f"""Evaluate this medication order dose:
- Requested Drug: {patient.get('requested_drug')}
- Requested Dose: {patient.get('dose')}
- Treatment History: {patient.get('treatment_history')}

Return JSON with status and reason."""
        result = self.client.chat_json(self.system_prompt, user_prompt, agent_name="DoseAgent")
        status = result.get("status", "").upper()
        if status not in ["PASS", "FLAG", "BLOCK"]:
            status = "FLAG"
        return {"status": status, "reason": result.get("reason", "")}


class SupervisorAgent:
    """
    Synthesizes findings from ContraindicationAgent and DoseAgent via real LLM call.
    CRITICAL INVARIANT: This agent must NEVER approve an order.
    Allowed output statuses: "Ready for human review", "Flagged", or "Blocked".
    """
    ALLOWED_STATUSES = ["Ready for human review", "Flagged", "Blocked"]

    def __init__(self, client: LLMClient):
        self.client = client
        self.system_prompt = """You are the SupervisorAgent in FluxGuard RX, a clinical Human-In-The-Loop (HITL) triage system.
Your job is to synthesize findings from the ContraindicationAgent and the DoseAgent to produce a final triage classification for the clinician queue.

CRITICAL SAFETY INVARIANT:
- You must NEVER approve an order. Automated systems are never licensed to approve medications.
- The ONLY valid output statuses are:
  1. "Blocked" - If there is an absolute contraindication (e.g. pregnancy, MTC/MEN2 history) OR dangerous overdose (>2.4mg).
  2. "Flagged" - If there are clinical risks, drug interactions (e.g. sulfonylureas/hypoglycemia), prior pancreatitis, or improper titration.
  3. "Ready for human review" - If both checks passed clean and the order is ready for physician evaluation and sign-off.

Decision Hierarchy:
- If ContraindicationAgent is BLOCK or DoseAgent is BLOCK -> status MUST be "Blocked".
- Else if ContraindicationAgent is FLAG or DoseAgent is FLAG -> status MUST be "Flagged".
- Else if both are PASS -> status MUST be "Ready for human review".

Output strictly valid JSON with this schema:
{
  "status": "Ready for human review" | "Flagged" | "Blocked",
  "reason": "1-2 sentence clinical summary explaining the triage status to the reviewing physician"
}"""

    def evaluate(self, patient: Dict[str, Any], contra_result: Dict[str, Any], dose_result: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = f"""Synthesize clinical triage for patient:
- Patient: {patient.get('name')}, Age: {patient.get('age')}, Pregnant: {bool(patient.get('is_pregnant'))}
- Requested: {patient.get('requested_drug')} {patient.get('dose')}
- ContraindicationAgent result: status={contra_result.get('status')}, reason={contra_result.get('reason')}
- DoseAgent result: status={dose_result.get('status')}, reason={dose_result.get('reason')}

Remember: You MUST NEVER APPROVE. Output status must be exactly 'Ready for human review', 'Flagged', or 'Blocked'."""
        
        raw_result = self.client.chat_json(self.system_prompt, user_prompt, agent_name="SupervisorAgent")
        status = raw_result.get("status", "").strip()
        reason = raw_result.get("reason", "").strip()

        # Deterministic Guardrail against hallucinated approval
        c_status = contra_result.get("status", "").upper()
        d_status = dose_result.get("status", "").upper()

        if c_status == "BLOCK" or d_status == "BLOCK":
            expected_level = "Blocked"
        elif c_status == "FLAG" or d_status == "FLAG":
            expected_level = "Flagged"
        else:
            expected_level = "Ready for human review"

        if status not in self.ALLOWED_STATUSES:
            status = expected_level
        elif expected_level == "Blocked" and status != "Blocked":
            status = "Blocked"
        elif expected_level == "Flagged" and status == "Ready for human review":
            status = "Flagged"

        return {
            "status": status,
            "reason": reason if reason else f"Triaged as {status} based on clinical contraindication and dosing checks."
        }


class FluxGuardTriagePipeline:
    """Coordinates the 3-agent triage pipeline."""
    def __init__(self, client: LLMClient = None):
        self.client = client or LLMClient()
        self.contra_agent = ContraindicationAgent(self.client)
        self.dose_agent = DoseAgent(self.client)
        self.supervisor_agent = SupervisorAgent(self.client)

    def process_order(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        # Real LLM Call 1: Contraindications
        contra_result = self.contra_agent.evaluate(patient)
        
        # Real LLM Call 2: Dose check
        dose_result = self.dose_agent.evaluate(patient)
        
        # Real LLM Call 3: Supervisor HITL decision
        supervisor_result = self.supervisor_agent.evaluate(patient, contra_result, dose_result)
        
        return {
            "patient_id": patient.get("id"),
            "patient_name": patient.get("name"),
            "age": patient.get("age"),
            "requested_drug": patient.get("requested_drug"),
            "dose": patient.get("dose"),
            "contraindication_check": contra_result,
            "dose_check": dose_result,
            "supervisor_decision": supervisor_result
        }
