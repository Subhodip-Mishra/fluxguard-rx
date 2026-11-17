"""
FluxGuard RX - Live Diagnostic Check (check_live.py)
Makes one real LLM call per agent:
1. ContraindicationAgent
2. DoseAgent
3. SupervisorAgent
Logs every call to calls.log and prints the raw responses.
If any call fails, it stops and displays the exact API error.
"""

import sys
import json
from llm_client import LLMClient
from agents import ContraindicationAgent, DoseAgent, SupervisorAgent

def main():
    print("=" * 80)
    print("FLUXGUARD RX - LIVE AGENT DIAGNOSTIC CHECK")
    print("=" * 80)
    
    try:
        client = LLMClient()
        print(f"Provider: {client.provider}")
        print(f"Model:    {client.model}")
        print(f"API Key:  {client.api_key[:6]}...{client.api_key[-4:] if client.api_key else 'NONE'}")
        print("-" * 80)
    except Exception as e:
        print(f"\n[FATAL ERROR] Initialization Failed: {e}")
        sys.exit(1)

    # Sample patient for diagnostic test
    sample_patient = {
        "id": 999,
        "name": "Live Test Patient",
        "age": 45,
        "is_pregnant": 0,
        "thyroid_cancer_history": "None",
        "current_meds": "Metformin 500mg BID",
        "medical_history": "Type 2 Diabetes, BMI 31.0",
        "requested_drug": "Semaglutide",
        "dose": "0.25 mg weekly",
        "treatment_history": "Treatment naïve. Starting initiation dose."
    }

    # 1. Test ContraindicationAgent
    print("\n[1/3] Testing ContraindicationAgent with real LLM API call...")
    contra_agent = ContraindicationAgent(client)
    try:
        user_prompt_1 = f"""Evaluate this patient order:
- Patient Name: {sample_patient['name']}
- Age: {sample_patient['age']}
- Pregnant: No
- Thyroid Cancer History: {sample_patient['thyroid_cancer_history']}
- Current Medications: {sample_patient['current_meds']}
- Medical History: {sample_patient['medical_history']}
- Requested Drug: {sample_patient['requested_drug']}
- Dose: {sample_patient['dose']}

Return JSON with status and reason."""
        raw_1 = client.chat(contra_agent.system_prompt, user_prompt_1, agent_name="ContraindicationAgent")
        print("\n--- RAW RESPONSE FROM ContraindicationAgent ---")
        print(raw_1)
        parsed_1 = contra_agent.evaluate(sample_patient)
        print("\nParsed Result:", parsed_1)
    except Exception as e:
        print(f"\n[ERROR] ContraindicationAgent failed real call: {e}")
        sys.exit(1)

    # 2. Test DoseAgent
    print("\n" + "-" * 80)
    print("[2/3] Testing DoseAgent with real LLM API call...")
    dose_agent = DoseAgent(client)
    try:
        user_prompt_2 = f"""Evaluate this medication order dose:
- Requested Drug: {sample_patient['requested_drug']}
- Requested Dose: {sample_patient['dose']}
- Treatment History: {sample_patient['treatment_history']}
- Medical History: {sample_patient['medical_history']}

Return JSON with status and reason."""
        raw_2 = client.chat(dose_agent.system_prompt, user_prompt_2, agent_name="DoseAgent")
        print("\n--- RAW RESPONSE FROM DoseAgent ---")
        print(raw_2)
        parsed_2 = dose_agent.evaluate(sample_patient)
        print("\nParsed Result:", parsed_2)
    except Exception as e:
        print(f"\n[ERROR] DoseAgent failed real call: {e}")
        sys.exit(1)

    # 3. Test SupervisorAgent
    print("\n" + "-" * 80)
    print("[3/3] Testing SupervisorAgent with real LLM API call (NEVER APPROVE)...")
    supervisor_agent = SupervisorAgent(client)
    try:
        user_prompt_3 = f"""Synthesize clinical triage for patient:
- Patient: {sample_patient['name']}, Age: {sample_patient['age']}, Pregnant: False
- Requested: {sample_patient['requested_drug']} {sample_patient['dose']}
- ContraindicationAgent result: status={parsed_1.get('status')}, reason={parsed_1.get('reason')}
- DoseAgent result: status={parsed_2.get('status')}, reason={parsed_2.get('reason')}

Remember: You MUST NEVER APPROVE. Output status must be exactly 'Ready for human review', 'Flagged', or 'Blocked'."""
        raw_3 = client.chat(supervisor_agent.system_prompt, user_prompt_3, agent_name="SupervisorAgent")
        print("\n--- RAW RESPONSE FROM SupervisorAgent ---")
        print(raw_3)
        parsed_3 = supervisor_agent.evaluate(sample_patient, parsed_1, parsed_2)
        print("\nParsed Result:", parsed_3)
    except Exception as e:
        print(f"\n[ERROR] SupervisorAgent failed real call: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("ALL 3 AGENTS SUCCESSFULLY COMPLETED REAL LLM CALLS!")
    print("Logged all calls to calls.log.")
    print("=" * 80)

if __name__ == "__main__":
    main()
