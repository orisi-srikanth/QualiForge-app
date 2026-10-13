import urllib.request
import urllib.error
import json

base_url = "http://localhost:8000/api"

print("=== 1. Test Unauthenticated Access to Decision Gate ===")
req = urllib.request.Request(
    f"{base_url}/workflows/WF-C038A990/decision",
    data=json.dumps({
        "approved_by": "Operator",
        "decision": "ACCEPT_FINDINGS",
        "disposition": "QUARANTINE_BATCH",
        "engineering_comments": "Unauthenticated test"
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    urllib.request.urlopen(req)
    print("UNEXPECTED: Allowed unauthenticated decision!")
except urllib.error.HTTPError as e:
    print(f"PASS: HTTP {e.code} correctly rejected unauthenticated request ({e.reason})")

print("\n=== 2. Authenticate as Operator Persona ===")
login_req = urllib.request.Request(
    f"{base_url}/auth/login",
    data=json.dumps({"username": "operator@precisionaero.com", "password": "Password123!"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(login_req) as resp:
        op_token = json.loads(resp.read().decode())["access_token"]
        print("Operator login successful")
except Exception as e:
    print(f"Operator login failed: {e}")
    op_token = None

if op_token:
    print("\n=== 3. Test Operator RBAC on Decision Gate (Expect 403 Forbidden) ===")
    op_req = urllib.request.Request(
        f"{base_url}/workflows/WF-C038A990/decision",
        data=json.dumps({
            "approved_by": "Operator Dave",
            "decision": "ACCEPT_FINDINGS",
            "disposition": "QUARANTINE_BATCH",
            "engineering_comments": "Operator attempt"
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {op_token}"},
        method="POST"
    )
    try:
        urllib.request.urlopen(op_req)
        print("FAIL: Operator was allowed to authorize disposition!")
    except urllib.error.HTTPError as e:
        print(f"PASS: HTTP {e.code} correctly rejected Operator role ({e.read().decode()})")

print("\n=== 4. Authenticate as Quality Engineer Persona ===")
eng_req = urllib.request.Request(
    f"{base_url}/auth/login",
    data=json.dumps({"username": "engineer@precisionaero.com", "password": "Engineer123!"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(eng_req) as resp:
        eng_token = json.loads(resp.read().decode())["access_token"]
        print("Engineer login successful")
except Exception as e:
    print(f"Engineer login failed: {e}")
    eng_token = None

if eng_token:
    print("\n=== 5. Test Quality Engineer Authorization on Decision Gate ===")
    eng_decision_req = urllib.request.Request(
        f"{base_url}/workflows/WF-C038A990/decision",
        data=json.dumps({
            "approved_by": "Sarah Chen, Lead Quality Engineer",
            "decision": "ACCEPT_FINDINGS",
            "disposition": "QUARANTINE_BATCH",
            "engineering_comments": "Verified flank wear on CNC-04 carbide insert. 100% sorting required."
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {eng_token}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(eng_decision_req) as resp:
            data = json.loads(resp.read().decode())
            print(f"PASS: Quality Engineer successfully authorized disposition:")
            print(f"  Workflow Status: {data.get('status')}")
            print(f"  Decision: {data.get('human_approval', {}).get('decision')}")
            print(f"  Current Agent: {data.get('current_agent')}")
    except urllib.error.HTTPError as e:
        print(f"Decision failed: HTTP {e.code}: {e.read().decode()}")
