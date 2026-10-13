"""
Code search utility for forbidden autonomous actions across QualityMind project.
Keywords: release, approve_batch, reject_batch, status = rejected, cnc, plc, machine_param,
stop, shutdown, setpoint, write_register, opcua, modbus, serial.
Classifies every hit into:
- READ_ONLY (data ingestion, reading logs, query parameters)
- DISPLAY_TEXT (UI labels, mock scenarios, documentation, string literals)
- REAL_WRITE (database persistence, API mutation, hardware communication)
"""
import os
import re
from pathlib import Path

KEYWORDS = [
    r"\brelease\b",
    r"\bapprove_batch\b",
    r"\breject_batch\b",
    r"status\s*=\s*['\"]?rejected['\"]?",
    r"\bcnc\b",
    r"\bplc\b",
    r"\bmachine_param\w*\b",
    r"\bstop\b",
    r"\bshutdown\b",
    r"\bsetpoint\b",
    r"\bwrite_register\b",
    r"\bopcua\b",
    r"\bmodbus\b",
    r"\bserial\b"
]

ROOT_DIRS = ["backend/app", "backend/app/agents", "backend/app/agents/prompts", "frontend/src"]

def classify_hit(file_path: str, line_num: int, line_content: str, keyword: str) -> str:
    line_lower = line_content.lower()
    
    # Check for hardware write attempts
    if any(k in line_lower for k in ["write_register", "opcua.write", "modbus.write", "serial.write"]):
        return "REAL_WRITE (HARDWARE) [CRITICAL]"
    
    # Check for safety guardrail assertions
    if "assert_no_" in line_lower or "guardrail" in line_lower:
        return "GUARDRAIL_INTERCEPT (Blocks real write)"
        
    # Check for tests or mocks
    if "test" in file_path.lower() or "mock" in line_lower:
        return "TEST_OR_MOCK"
        
    # Check for UI display text
    if file_path.endswith((".tsx", ".jsx", ".html", ".css")) or "label" in line_lower or "title" in line_lower or "badge" in line_lower or "placeholder" in line_lower or "text" in line_lower:
        return "DISPLAY_TEXT (UI)"
        
    # Check for markdown prompts or docs
    if file_path.endswith(".md"):
        return "DOCUMENTATION_OR_PROMPT"
        
    # Check for DB models / schemas / queries
    if any(k in line_lower for k in [".filter", "get(", "select", "read", "query"]):
        return "READ_ONLY (Query / Schema)"
        
    if any(k in line_lower for k in ["db.commit", "update", "set "]):
        return "REAL_WRITE (Database entity update)"
        
    return "READ_ONLY / CONFIG"

def run_search():
    results = []
    compiled_patterns = [(k, re.compile(k, re.IGNORECASE)) for k in KEYWORDS]
    
    for r_dir in ROOT_DIRS:
        base = Path(r_dir)
        if not base.exists():
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith((".py", ".ts", ".tsx", ".md", ".json")):
                    f_path = Path(root) / f
                    try:
                        with open(f_path, "r", encoding="utf-8", errors="ignore") as fp:
                            for idx, line in enumerate(fp, 1):
                                for kw_name, pattern in compiled_patterns:
                                    if pattern.search(line):
                                        classification = classify_hit(str(f_path), idx, line.strip(), kw_name)
                                        results.append({
                                            "file": str(f_path).replace("\\", "/"),
                                            "line": idx,
                                            "keyword": kw_name.replace(r"\b", ""),
                                            "snippet": line.strip()[:100],
                                            "classification": classification
                                        })
                    except Exception:
                        pass
    return results

if __name__ == "__main__":
    hits = run_search()
    print(f"Total keyword hits found: {len(hits)}")
    classes = {}
    for h in hits:
        classes[h["classification"]] = classes.get(h["classification"], 0) + 1
    for c, count in sorted(classes.items(), key=lambda x: x[1], reverse=True):
        print(f"  {c}: {count}")
