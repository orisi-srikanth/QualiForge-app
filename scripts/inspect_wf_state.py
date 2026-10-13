import sqlite3
import json

conn = sqlite3.connect('backend/data/quality_system.db')
c = conn.cursor()
c.execute("SELECT state_json FROM workflow_state WHERE workflow_id='WF-A7C30CC5'")
row = c.fetchone()
if not row:
    print("Workflow not found")
    exit(1)

state = json.loads(row[0])
print("=== Workflow State Keys ===")
print(list(state.keys()))

print("\n=== Current Agent ===")
print(state.get("current_agent"))

print("\n=== Batch ID ===")
print(state.get("batch_id"))

print("\n=== Execution Trace Steps ===")
for i, step in enumerate(state.get("execution_trace", [])):
    print(f"Step {i+1}: {step.get('agent_name')} | Status: {step.get('status')}")
    print(f"   Input summary: {step.get('input_summary')}")
    print(f"   Tools called: {step.get('tools_called')}")
    print(f"   Model used: {step.get('model_used')}")
    print(f"   Output summary: {step.get('output_summary')}")


print("\n=== Visual Prediction (Model Results) ===")
print(state.get("visual_prediction"))

print("\n=== RCA Report (Evidence & Hypotheses) ===")
rca = state.get("rca_report") or {}
print(f"Historical matches (retrieved evidence): {len(rca.get('historical_matches', []))}")
for match in rca.get('historical_matches', [])[:2]:
    print("  Evidence:", match)

print(f"Ranked hypotheses: {len(rca.get('ranked_hypotheses', []))}")
for hyp in rca.get('ranked_hypotheses', [])[:3]:
    print("  Hypothesis:", hyp)

print("\n=== Critic Review (Reviewer Comments) ===")
critic = state.get("critic_review") or {}
print(critic)

print("\n=== Human Approval (Human Decision) ===")
print(state.get("human_approval"))

print("\n=== agent_runs columns ===")
c.execute("PRAGMA table_info(agent_runs)")
print([r[1] for r in c.fetchall()])
c.execute("SELECT * FROM agent_runs WHERE workflow_id='WF-A7C30CC5' LIMIT 2")
print("Sample agent_runs rows:", c.fetchall())

print("\n=== human_decisions columns ===")
c.execute("PRAGMA table_info(human_decisions)")
print([r[1] for r in c.fetchall()])
c.execute("SELECT * FROM human_decisions WHERE batch_id='BATCH-0245'")
print("Sample human_decisions rows:", c.fetchall())

print("\n=== reviewer_comments columns ===")
c.execute("PRAGMA table_info(reviewer_comments)")
print([r[1] for r in c.fetchall()])
c.execute("SELECT * FROM reviewer_comments WHERE workflow_id='WF-A7C30CC5'")
print("Sample reviewer_comments rows:", c.fetchall())


