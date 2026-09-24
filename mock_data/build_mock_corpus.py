"""Deterministic mock-corpus builder. Derives html+md+pdf from existing json.
Synthetic IDs only. No network. Overwrites generated files each run."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def _load(name: str):
    with open(ROOT / name) as f:
        return json.load(f)

def _pdf_minimal(title: str, lines: list[str]) -> bytes:
    text = f"{title}\n" + "\n".join(lines)
    # Minimal valid PDF with one page, Helvetica, raw text ops.
    esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    y = 750
    ops = []
    for ln in esc.split("\n")[:40]:
        ops.append(f"BT /F1 10 Tf 50 {y} Td ({ln[:90]}) Tj ET")
        y -= 14
    content = "\n".join(ops).encode("latin-1", "replace")
    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    objs.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = [b"%PDF-1.4"]
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(sum(len(x) + 1 for x in out))
        out.append(f"{i} 0 obj".encode() + b"\n" + body + b"\nendobj")
    xref = sum(len(x) + 1 for x in out)
    out.append(f"xref\n0 {len(objs)+1}\n0000000000 65535 f ".encode())
    for o in offsets:
        out.append(f"{o:010d} 00000 n ".encode())
    out.append(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return b"\n".join(out)

def main() -> None:
    employees = _load("employees.json")
    pto = _load("pto_balances.json")
    benefits = _load("benefits.json")
    # HTML: table views (parseable heterogeneous format #1)
    rows = "".join(f"<tr><td>{e['id']}</td><td>{e['role']}</td><td>{e['location']}</td></tr>" for e in employees)
    (ROOT / "employees.html").write_text(f"<!doctype html><html><body><h1>Employees</h1><h2>Roster</h2><table>{rows}</table></body></html>")
    brows = "".join(f"<tr><td>{b['employee_id']}</td><td>{b['plan']}</td><td>{b['status']}</td></tr>" for b in benefits)
    (ROOT / "benefits.html").write_text(f"<!doctype html><html><body><h1>Benefits</h1><h2>Elections</h2><table>{brows}</table></body></html>")
    # MD: human-readable summaries (format #2, distinct from policy_docs corpus)
    md = ["# Mock PTO Balances", ""]
    for p in pto:
        md.append(f"## {p['employee_id']}")
        md.append(f"Remaining {p['remaining']} of {p['total']} (used {p['used']}).")
    (ROOT / "pto_balances.md").write_text("\n".join(md) + "\n")
    (ROOT / "corpus_readme.md").write_text("# Mock corpus\n\nSources: employees.json, pto_balances.json, benefits.json.\nDerived: employees.html, benefits.html, pto_balances.md, employees.pdf, policies_summary.pdf.\nAll synthetic.\n")
    # PDF: minimal valid PDFs (format #3)
    (ROOT / "employees.pdf").write_bytes(_pdf_minimal("Employees", [f"{e['id']} {e['role']} {e['location']}" for e in employees]))
    (ROOT / "policies_summary.pdf").write_bytes(_pdf_minimal("Policies summary", [f"{b['employee_id']} {b['plan']} {b['status']}" for b in benefits]))
    print("built: html=2 md=2 pdf=2 json=3 (pre-existing)")

if __name__ == "__main__":
    main()
