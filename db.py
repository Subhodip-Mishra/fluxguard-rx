"""
FluxGuard RX - Database Initializer
Creates SQLite database and seeds 25 synthetic clinical patient records.
"""

import sqlite3
import os

DB_PATH = "fluxguard_rx.db"

PATIENTS = [
    # --- Clean Cases (Expected: Ready for human review) ---
    (1, "Alice Morgan", 42, 0, "None", "Metformin 500mg BID", "T2D, BMI 31.5. No organ damage.", "Semaglutide", "0.25 mg weekly", "Treatment naïve. Starting initiation dose."),
    (2, "Robert Davis", 55, 0, "None", "Atorvastatin 20mg", "Obesity, BMI 33.2, hyperlipidemia.", "Semaglutide", "0.25 mg weekly", "Initiating weight management."),
    (3, "Clara Chen", 38, 0, "None", "None", "Obesity, BMI 32.0, non-diabetic.", "Semaglutide", "0.25 mg weekly", "Initial prescription for lifestyle adjunctive."),
    (4, "David Wilson", 61, 0, "None", "Amlodipine 5mg", "Essential hypertension, BMI 30.8.", "Semaglutide", "0.5 mg weekly", "Completed 4 weeks of 0.25mg tolerating well."),
    (5, "Elena Rostova", 49, 0, "None", "Metformin 1000mg BID", "T2D, HbA1c 7.6%, BMI 29.5.", "Semaglutide", "1.0 mg weekly", "On 0.5mg for 6 weeks, gradual titration."),
    (6, "James Miller", 52, 0, "None", "Lisinopril 10mg, Metformin 500mg", "T2D, mild HTN, BMI 34.1.", "Semaglutide", "0.25 mg weekly", "Initiation dose."),
    (7, "Sarah Jenkins", 44, 0, "None", "Levothyroxine 50mcg (hypothyroidism)", "Primary hypothyroidism, stable TSH. BMI 31.0.", "Semaglutide", "0.25 mg weekly", "Initial dose. Regular thyroid monitoring."),
    (8, "Carlos Santana", 58, 0, "None", "Losartan 50mg", "BMI 32.5, metabolic syndrome.", "Semaglutide", "0.5 mg weekly", "Completed 4 weeks at 0.25mg with no GI side effects."),

    # --- Blocked Cases: Absolute Contraindications (Pregnancy / Thyroid MTC / MEN2 / Fatal Dose) ---
    (9, "Emily Blunt", 29, 1, "None", "Prenatal multivitamins", "G1P0, 14 weeks pregnant, gestational glucose intolerance.", "Semaglutide", "0.25 mg weekly", "Patient requested GLP-1 for weight control."),
    (10, "Jessica Taylor", 33, 1, "None", "Folic acid 800mcg", "Confirmed intrauterine pregnancy (first trimester).", "Semaglutide", "0.5 mg weekly", "Previous user asking to continue prescription."),
    (11, "Arthur Pendelton", 48, 0, "Personal history of Medullary Thyroid Carcinoma (MTC) in 2018", "None", "Status post total thyroidectomy for MTC.", "Semaglutide", "0.25 mg weekly", "Seeking weight loss treatment."),
    (12, "Brenda Vance", 36, 0, "Family history of Multiple Endocrine Neoplasia type 2 (MEN 2)", "None", "Mother and brother diagnosed with MEN 2A syndrome.", "Semaglutide", "0.5 mg weekly", "Requested semaglutide for metabolic health."),
    (13, "Gary Oldman", 63, 0, "Personal history of Medullary Thyroid Carcinoma", "Atorvastatin 40mg", "Treated MTC 5 years ago, in remission.", "Semaglutide", "1.0 mg weekly", "Referred for glycemic control."),
    (14, "Samuel Jackson", 45, 0, "Family history of MTC (Father)", "Metformin 850mg", "Father died from medullary thyroid carcinoma.", "Semaglutide", "0.25 mg weekly", "Initial request."),
    (15, "Chloe Bennet", 27, 0, "None", "None", "Severe obesity, BMI 41.", "Semaglutide", "10.0 mg weekly", "Order entered with dangerous supra-therapeutic dose."),
    (16, "Mark Wahlberg", 40, 0, "None", "Multivitamin", "Bodybuilder aiming for extreme cut.", "Semaglutide", "5.0 mg weekly", "Massive overdose request exceeding max guidelines."),

    # --- Flagged Cases: Drug Interactions & High Hypoglycemia Risk ---
    (17, "George Martin", 67, 0, "None", "Glimepiride 4mg daily, Metformin 1000mg", "T2D for 12 years, HbA1c 8.4%.", "Semaglutide", "0.25 mg weekly", "Adding GLP-1. Concomitant sulfonylurea requires dose adjustment."),
    (18, "Fiona Apple", 59, 0, "None", "Insulin Glargine 35 units nightly, Glipizide 10mg", "Long-standing T2D, high risk of hypoglycemia.", "Semaglutide", "0.25 mg weekly", "Initiating dual incretin therapy."),
    (19, "Harold Finch", 71, 0, "None", "Glyburide 5mg daily", "Mild cognitive decline, T2D, lives alone.", "Semaglutide", "0.5 mg weekly", "Hypoglycemia risk with sulfonylurea."),

    # --- Flagged Cases: Clinical Precautions (Pancreatitis / Renal / High Initial Titration) ---
    (20, "Lucas Graham", 46, 0, "None", "Omeprazole 20mg", "Documented acute necrotizing pancreatitis 3 years ago.", "Semaglutide", "0.25 mg weekly", "Requesting semaglutide. History of pancreatitis."),
    (21, "Rachel Green", 39, 0, "None", "None", "BMI 35, history of gallstone pancreatitis in 2022.", "Semaglutide", "0.5 mg weekly", "Prior pancreatitis precaution."),
    (22, "Peter Parker", 31, 0, "None", "None", "Obesity, BMI 36.5. Naïve to GLP-1s.", "Semaglutide", "2.4 mg weekly", "Ordering maximum maintenance dose without prior titration!"),
    (23, "Diana Prince", 47, 0, "None", "Lisinopril 20mg", "T2D, BMI 33. Naïve to GLP-1 agonists.", "Semaglutide", "1.7 mg weekly", "Requesting high starting dose bypassing 0.25mg and 0.5mg."),
    (24, "Victor Stone", 65, 0, "None", "Furosemide 40mg, Metformin 500mg", "Moderate renal impairment (eGFR 38 mL/min).", "Semaglutide", "0.25 mg weekly", "Requires renal function and volume monitoring."),

    # --- Borderline / Complex Case ---
    (25, "Hannah Abbott", 34, 0, "History of benign thyroid nodules (Biopsy negative for MTC)", "Synthroid 75mcg", "Benign follicular nodule on ultrasound 2023.", "Semaglutide", "0.25 mg weekly", "Benign thyroid nodules - not MTC/MEN2, safe to initiate with review.")
]

def init_db(db_path: str = DB_PATH):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE patients (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        is_pregnant INTEGER NOT NULL,
        thyroid_cancer_history TEXT NOT NULL,
        current_meds TEXT NOT NULL,
        medical_history TEXT NOT NULL,
        requested_drug TEXT NOT NULL,
        dose TEXT NOT NULL,
        treatment_history TEXT NOT NULL
    )
    """)

    cursor.executemany("""
    INSERT INTO patients (id, name, age, is_pregnant, thyroid_cancer_history, current_meds, medical_history, requested_drug, dose, treatment_history)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, PATIENTS)

    conn.commit()
    conn.close()
    print(f"Database initialized at '{db_path}' with {len(PATIENTS)} patient records.")

if __name__ == "__main__":
    init_db()
