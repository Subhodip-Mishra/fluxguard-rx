"""
FluxGuard RX - Main Runner & HTML Report Generator
Iterates through all 25 synthetic patients in SQLite database,
executes the 3-agent clinical triage pipeline,
and generates an interactive, tabbed report.html.
"""

import sqlite3
import os
import json
import time
from typing import List, Dict, Any
from agents import FluxGuardTriagePipeline
from db import DB_PATH, init_db

def load_patients(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Initializing now...")
        init_db(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients ORDER BY id ASC")
    rows = cursor.fetchall()
    patients = [dict(r) for r in rows]
    conn.close()
    return patients

def generate_html_report(results: List[Dict[str, Any]], output_path: str = "report.html"):
    total = len(results)
    ready_count = sum(1 for r in results if r["supervisor_decision"]["status"] == "Ready for human review")
    flagged_count = sum(1 for r in results if r["supervisor_decision"]["status"] == "Flagged")
    blocked_count = sum(1 for r in results if r["supervisor_decision"]["status"] == "Blocked")

    rows_html = []
    for r in results:
        status = r["supervisor_decision"]["status"]
        status_slug = status.lower().replace(" ", "-")
        reason = r["supervisor_decision"]["reason"]
        c_status = r["contraindication_check"]["status"]
        c_reason = r["contraindication_check"]["reason"]
        d_status = r["dose_check"]["status"]
        d_reason = r["dose_check"]["reason"]

        if status == "Ready for human review":
            badge_class = "badge-ready"
            status_icon = "🟢"
        elif status == "Flagged":
            badge_class = "badge-flagged"
            status_icon = "🟡"
        else:
            badge_class = "badge-blocked"
            status_icon = "🔴"

        c_badge = "pill-pass" if c_status == "PASS" else ("pill-flag" if c_status == "FLAG" else "pill-block")
        d_badge = "pill-pass" if d_status == "PASS" else ("pill-flag" if d_status == "FLAG" else "pill-block")

        preg_info = '<span class="text-danger font-weight-bold">Pregnant (Yes)</span>' if r.get('is_pregnant') else 'No'
        thyroid_info = r.get('thyroid_cancer_history', 'None')
        if "MTC" in thyroid_info or "MEN" in thyroid_info:
            thyroid_display = f'<span class="text-danger">{thyroid_info}</span>'
        else:
            thyroid_display = thyroid_info

        row = f"""
        <tr class="order-row filter-{status_slug}" data-status="{status_slug}">
            <td class="cell-id">#{r['patient_id']}</td>
            <td>
                <strong>{r['patient_name']}</strong><br>
                <small class="text-muted">Age: {r['age']} | Pregnant: {preg_info}</small>
            </td>
            <td>
                <span class="med-tag">{r['requested_drug']}</span><br>
                <strong>{r['dose']}</strong>
            </td>
            <td>
                <small><strong>Thyroid:</strong> {thyroid_display}</small><br>
                <small><strong>Meds:</strong> {r.get('current_meds')}</small><br>
                <small class="text-muted"><strong>History:</strong> {r.get('medical_history')}</small>
            </td>
            <td>
                <span class="pill {c_badge}">Contra: {c_status}</span><br>
                <small class="text-muted" title="{c_reason}">{c_reason[:75]}...</small>
            </td>
            <td>
                <span class="pill {d_badge}">Dose: {d_status}</span><br>
                <small class="text-muted" title="{d_reason}">{d_reason[:75]}...</small>
            </td>
            <td>
                <span class="badge {badge_class}">{status_icon} {status}</span>
            </td>
            <td class="cell-reason">
                {reason}
            </td>
        </tr>
        """
        rows_html.append(row)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FluxGuard RX - Clinical Order Triage Report</title>
    <style>
        :root {{
            --bg-main: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --color-ready: #10b981;
            --color-flagged: #f59e0b;
            --color-blocked: #ef4444;
            --color-primary: #3b82f6;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            padding: 2rem;
            line-height: 1.5;
        }}
        .header {{
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
        }}
        .header-title h1 {{
            font-size: 1.85rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .header-subtitle {{
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }}
        .badge-hitl {{
            background: #2563eb22;
            color: #60a5fa;
            border: 1px solid #3b82f644;
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
        }}
        .stat-card.ready {{ border-left: 4px solid var(--color-ready); }}
        .stat-card.flagged {{ border-left: 4px solid var(--color-flagged); }}
        .stat-card.blocked {{ border-left: 4px solid var(--color-blocked); }}
        .stat-card.total {{ border-left: 4px solid var(--color-primary); }}
        .stat-value {{ font-size: 2rem; font-weight: 700; }}
        .stat-label {{ color: var(--text-muted); font-size: 0.85rem; text-transform: uppercase; font-weight: 600; }}
        
        .tabs {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.25rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.5rem;
        }}
        .tab-btn {{
            background: transparent;
            color: var(--text-muted);
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 0.5rem;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease-in-out;
        }}
        .tab-btn:hover {{
            background: #33415555;
            color: #fff;
        }}
        .tab-btn.active {{
            background: #3b82f6;
            color: #ffffff;
        }}

        .table-container {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            text-align: left;
        }}
        th {{
            background-color: #1e293b;
            color: var(--text-muted);
            padding: 0.85rem 1rem;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--border-color);
        }}
        td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}
        tr:hover td {{
            background-color: #27354a;
        }}
        .cell-id {{ font-weight: bold; color: var(--text-muted); width: 45px; }}
        .cell-reason {{ max-width: 380px; font-size: 0.85rem; line-height: 1.4; }}
        
        .badge {{
            display: inline-block;
            padding: 0.35rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 600;
            white-space: nowrap;
        }}
        .badge-ready {{ background: #065f46; color: #6ee7b7; border: 1px solid #10b98144; }}
        .badge-flagged {{ background: #78350f; color: #fde68a; border: 1px solid #f59e0b44; }}
        .badge-blocked {{ background: #7f1d1d; color: #fca5a5; border: 1px solid #ef444444; }}

        .pill {{
            display: inline-block;
            padding: 0.2rem 0.45rem;
            border-radius: 0.25rem;
            font-size: 0.72rem;
            font-weight: 600;
            margin-bottom: 0.2rem;
        }}
        .pill-pass {{ background: #064e3b; color: #a7f3d0; }}
        .pill-flag {{ background: #713f12; color: #fde047; }}
        .pill-block {{ background: #7f1d1d; color: #fecaca; }}

        .med-tag {{
            background: #1e3a8a;
            color: #bfdbfe;
            padding: 0.15rem 0.4rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .text-danger {{ color: #f87171 !important; }}
        .text-muted {{ color: var(--text-muted); }}
        .font-weight-bold {{ font-weight: bold; }}

        .footer {{
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.8rem;
            display: flex;
            justify-content: space-between;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-title">
            <h1>🛡️ FluxGuard RX &bull; Clinical Order Triage</h1>
            <div class="header-subtitle">Multi-Agent Human-in-the-Loop Safeguard Pipeline &bull; Semaglutide Prescribing Orders</div>
        </div>
        <div>
            <span class="badge-hitl">HITL Invariant: Never Auto-Approve</span>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card total">
            <span class="stat-label">Total Orders</span>
            <span class="stat-value">{total}</span>
        </div>
        <div class="stat-card ready">
            <span class="stat-label">Ready for Review</span>
            <span class="stat-value">{ready_count}</span>
        </div>
        <div class="stat-card flagged">
            <span class="stat-label">Flagged (Risk/Titration)</span>
            <span class="stat-value">{flagged_count}</span>
        </div>
        <div class="stat-card blocked">
            <span class="stat-label">Blocked (Contraindicated)</span>
            <span class="stat-value">{blocked_count}</span>
        </div>
    </div>

    <div class="tabs">
        <button class="tab-btn active" onclick="filterTable('all', this)">All Orders ({total})</button>
        <button class="tab-btn" onclick="filterTable('ready-for-human-review', this)">🟢 Ready for Review ({ready_count})</button>
        <button class="tab-btn" onclick="filterTable('flagged', this)">🟡 Flagged ({flagged_count})</button>
        <button class="tab-btn" onclick="filterTable('blocked', this)">🔴 Blocked ({blocked_count})</button>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Patient Demographics</th>
                    <th>Medication Order</th>
                    <th>Clinical History & Meds</th>
                    <th>Contraindication Agent</th>
                    <th>Dose Agent</th>
                    <th>Supervisor Triage</th>
                    <th>Clinical Rationale (HITL Queue)</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>

    <div class="footer">
        <div>Generated by FluxGuard RX Autonomous Clinical Decision Support Agent</div>
        <div>Timestamp: {time.strftime("%Y-%m-%d %H:%M:%S")} UTC</div>
    </div>

    <script>
        function filterTable(status, btn) {{
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const rows = document.querySelectorAll('.order-row');
            rows.forEach(row => {{
                if (status === 'all' || row.dataset.status === status) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Report successfully generated at: {output_path}")

def main():
    print("=" * 70)
    print("FLUXGUARD RX - PROCESSING CLINICAL ORDERS (25 PATIENTS)")
    print("=" * 70)
    
    patients = load_patients()
    pipeline = FluxGuardTriagePipeline()

    results = []
    start_time = time.time()

    for idx, p in enumerate(patients, start=1):
        t0 = time.time()
        print(f"[{idx:02d}/25] Processing {p['name']} ({p['requested_drug']} {p['dose']})...", end="", flush=True)
        res = pipeline.process_order(p)
        # Store original patient data in result for report formatting
        res.update(p)
        results.append(res)
        elapsed = time.time() - t0
        status = res["supervisor_decision"]["status"]
        print(f" -> {status} ({elapsed:.1f}s)")
        time.sleep(0.5)

    total_time = time.time() - start_time
    print("=" * 70)
    print(f"Completed triage for all 25 patients in {total_time:.2f} seconds.")
    print("Generating HTML report...")
    generate_html_report(results, "report.html")
    print("=" * 70)

if __name__ == "__main__":
    main()
