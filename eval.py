"""
FluxGuard RX - Evaluation & Regression Benchmark Suite
15 labeled clinical test cases to evaluate Contraindication, Dose, and Supervisor agents.
Prints accuracy, breakdown by category, and catches regressions.
"""

import sys
import time
from typing import List, Dict, Any
from agents import FluxGuardTriagePipeline

TEST_CASES = [
    # --- Category: Clean Orders (Expected: "Ready for human review") ---
    {
        "id": "TC-01",
        "description": "Standard initiation for treatment-naïve patient",
        "patient": {
            "name": "Sarah Miller", "age": 45, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "Metformin 500mg BID",
            "medical_history": "Type 2 Diabetes, BMI 32.1", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "Naïve to GLP-1 therapy. Starting dose."
        },
        "expected_status": "Ready for human review"
    },
    {
        "id": "TC-02",
        "description": "Appropriate dose titration to 0.5 mg after 4 weeks",
        "patient": {
            "name": "John Doe", "age": 52, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "Atorvastatin 20mg",
            "medical_history": "Obesity, BMI 34.0", "requested_drug": "Semaglutide",
            "dose": "0.5 mg weekly", "treatment_history": "Completed 4 weeks of 0.25mg with good tolerance."
        },
        "expected_status": "Ready for human review"
    },
    {
        "id": "TC-03",
        "description": "Appropriate titration to 1.0 mg maintenance",
        "patient": {
            "name": "Linda Vance", "age": 49, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "Lisinopril 10mg",
            "medical_history": "Hypertension, T2D, BMI 30.5", "requested_drug": "Semaglutide",
            "dose": "1.0 mg weekly", "treatment_history": "Completed 4 weeks of 0.5mg without adverse effects."
        },
        "expected_status": "Ready for human review"
    },
    {
        "id": "TC-04",
        "description": "Patient with benign non-MTC thyroid nodule initiating standard dose",
        "patient": {
            "name": "Maria Garcia", "age": 39, "is_pregnant": 0,
            "thyroid_cancer_history": "Benign colloid thyroid nodule (biopsy confirmed benign, non-MTC)",
            "current_meds": "Multivitamin",
            "medical_history": "Obesity, BMI 31.8", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "New initiation. Thyroid nodule benign."
        },
        "expected_status": "Ready for human review"
    },
    {
        "id": "TC-05",
        "description": "Maintenance dose 2.4 mg after full gradual escalation",
        "patient": {
            "name": "William Harris", "age": 58, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "None",
            "medical_history": "Severe obesity, BMI 38.2", "requested_drug": "Semaglutide",
            "dose": "2.4 mg weekly", "treatment_history": "Completed 16-week titration ladder (0.25, 0.5, 1.0, 1.7mg)."
        },
        "expected_status": "Ready for human review"
    },

    # --- Category: Absolute Contraindications (Expected: "Blocked") ---
    {
        "id": "TC-06",
        "description": "Active pregnancy (first trimester)",
        "patient": {
            "name": "Emma Watson", "age": 28, "is_pregnant": 1,
            "thyroid_cancer_history": "None", "current_meds": "Prenatal vitamins",
            "medical_history": "Gestational weight gain, 10 weeks pregnant", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "Requesting medication for weight."
        },
        "expected_status": "Blocked"
    },
    {
        "id": "TC-07",
        "description": "Personal history of Medullary Thyroid Carcinoma (MTC)",
        "patient": {
            "name": "Gregory House", "age": 60, "is_pregnant": 0,
            "thyroid_cancer_history": "Personal history of Medullary Thyroid Carcinoma (treated 2017)",
            "current_meds": "Levothyroxine 125mcg",
            "medical_history": "Post-thyroidectomy for MTC, BMI 33.0", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "Requesting initiation for weight loss."
        },
        "expected_status": "Blocked"
    },
    {
        "id": "TC-08",
        "description": "Family history of Multiple Endocrine Neoplasia syndrome type 2 (MEN 2)",
        "patient": {
            "name": "Bruce Banner", "age": 42, "is_pregnant": 0,
            "thyroid_cancer_history": "First-degree relative (sister) with MEN 2A syndrome",
            "current_meds": "None",
            "medical_history": "T2D, BMI 35.0", "requested_drug": "Semaglutide",
            "dose": "0.5 mg weekly", "treatment_history": "Initiation request."
        },
        "expected_status": "Blocked"
    },
    {
        "id": "TC-09",
        "description": "Dangerous supra-therapeutic overdose (10.0 mg weekly)",
        "patient": {
            "name": "Tony Stark", "age": 49, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "None",
            "medical_history": "BMI 29.0", "requested_drug": "Semaglutide",
            "dose": "10.0 mg weekly", "treatment_history": "Prescription entered with severe overdose."
        },
        "expected_status": "Blocked"
    },
    {
        "id": "TC-10",
        "description": "Dose exceeds FDA maximum (5.0 mg weekly)",
        "patient": {
            "name": "Natasha Romanoff", "age": 36, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "None",
            "medical_history": "Obesity, BMI 32.5", "requested_drug": "Semaglutide",
            "dose": "5.0 mg weekly", "treatment_history": "Requesting double max approved dose."
        },
        "expected_status": "Blocked"
    },

    # --- Category: Clinical Risks & Precautions (Expected: "Flagged") ---
    {
        "id": "TC-11",
        "description": "Concomitant Sulfonylurea (Glimepiride) -> Severe hypoglycemia risk",
        "patient": {
            "name": "Arthur Dent", "age": 64, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "Glimepiride 4mg daily, Metformin 1000mg",
            "medical_history": "Uncontrolled T2D, HbA1c 8.8%", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "Adding GLP-1 to oral regimen."
        },
        "expected_status": "Flagged"
    },
    {
        "id": "TC-12",
        "description": "Concomitant Basal Insulin -> Severe hypoglycemia risk",
        "patient": {
            "name": "Donna Noble", "age": 55, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "Insulin Glargine 40 units daily",
            "medical_history": "T2D, BMI 34.5", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "Adding GLP-1; insulin dose reduction required."
        },
        "expected_status": "Flagged"
    },
    {
        "id": "TC-13",
        "description": "Documented prior history of acute pancreatitis",
        "patient": {
            "name": "Walter White", "age": 53, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "None",
            "medical_history": "Acute alcohol-induced pancreatitis in 2021 (resolved), BMI 31.0", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "New start. Pancreatitis precaution."
        },
        "expected_status": "Flagged"
    },
    {
        "id": "TC-14",
        "description": "Skipping titration: Naïve patient starting directly at 2.4 mg",
        "patient": {
            "name": "Jesse Pinkman", "age": 30, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "None",
            "medical_history": "Obesity, BMI 35.8", "requested_drug": "Semaglutide",
            "dose": "2.4 mg weekly", "treatment_history": "Patient never took GLP-1 before. Requested max dose."
        },
        "expected_status": "Flagged"
    },
    {
        "id": "TC-15",
        "description": "Moderate chronic kidney disease requiring volume and renal monitoring",
        "patient": {
            "name": "Saul Goodman", "age": 62, "is_pregnant": 0,
            "thyroid_cancer_history": "None", "current_meds": "Hydrochlorothiazide 25mg",
            "medical_history": "CKD Stage 3b (eGFR 36 mL/min), T2D, dehydration risk", "requested_drug": "Semaglutide",
            "dose": "0.25 mg weekly", "treatment_history": "Initiation with renal monitoring needed."
        },
        "expected_status": "Flagged"
    }
]

def run_evaluation():
    print("=" * 80)
    print(" FLUXGUARD RX - CLINICAL ORDER TRIAGE EVALUATION SUITE")
    print(f" Running {len(TEST_CASES)} labeled benchmark test cases...")
    print("=" * 80)

    pipeline = FluxGuardTriagePipeline()
    passed = 0
    failed = 0
    start_time = time.time()

    print(f"{'ID':<7} | {'Expected':<22} | {'Predicted':<22} | {'Status':<6} | {'Test Description'}")
    print("-" * 80)

    results_breakdown = {
        "Ready for human review": {"total": 0, "correct": 0},
        "Flagged": {"total": 0, "correct": 0},
        "Blocked": {"total": 0, "correct": 0}
    }

    regressions = []

    for tc in TEST_CASES:
        t0 = time.time()
        output = pipeline.process_order(tc["patient"])
        elapsed = time.time() - t0
        time.sleep(0.5)

        predicted = output["supervisor_decision"]["status"]
        expected = tc["expected_status"]
        reason = output["supervisor_decision"]["reason"]

        results_breakdown[expected]["total"] += 1

        is_match = (predicted == expected)
        if is_match:
            passed += 1
            results_breakdown[expected]["correct"] += 1
            mark = "PASS [OK]"
        else:
            failed += 1
            mark = "FAIL [X]"
            regressions.append({
                "id": tc["id"],
                "desc": tc["description"],
                "expected": expected,
                "predicted": predicted,
                "reason": reason
            })

        print(f"{tc['id']:<7} | {expected:<22} | {predicted:<22} | {mark:<9} | {tc['description'][:30]}")

    total_time = time.time() - start_time
    accuracy = (passed / len(TEST_CASES)) * 100.0

    print("=" * 80)
    print(" EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total Cases:     {len(TEST_CASES)}")
    print(f"Correct:         {passed}")
    print(f"Failed:          {failed}")
    print(f"Accuracy:        {accuracy:.1f}%")
    print(f"Total Duration:  {total_time:.2f}s (avg {total_time/len(TEST_CASES):.2f}s/case)")
    print("-" * 80)
    print("Breakdown by Category:")
    for cat, stats in results_breakdown.items():
        cat_acc = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  • {cat:<24}: {stats['correct']}/{stats['total']} ({cat_acc:.1f}%)")
    print("=" * 80)

    if regressions:
        print("\nREGRESSION / MISMATCH DETAILS:")
        for r in regressions:
            print(f"  [{r['id']}] {r['desc']}")
            print(f"    - Expected:  {r['expected']}")
            print(f"    - Predicted: {r['predicted']}")
            print(f"    - Reason:    {r['reason']}\n")
        return False
    else:
        print("\nAll 15 labeled test cases PASSED. Zero regressions detected.")
        return True

if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)
