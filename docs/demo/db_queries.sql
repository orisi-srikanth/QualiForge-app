-- =============================================================================
-- QualityMind Technical Discussion & Demonstration SQL Queries
-- Verified for both PostgreSQL (Render production) and SQLite (local dev)
-- =============================================================================

-- Query 1: All tables and total row counts across the manufacturing database.
SELECT 'users' AS table_name, COUNT(*) AS total_rows FROM users
UNION ALL SELECT 'machines', COUNT(*) FROM machines
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'inspection_characteristics', COUNT(*) FROM inspection_characteristics
UNION ALL SELECT 'process_baselines', COUNT(*) FROM process_baselines
UNION ALL SELECT 'batches', COUNT(*) FROM batches
UNION ALL SELECT 'measurements', COUNT(*) FROM measurements
UNION ALL SELECT 'inspection_images', COUNT(*) FROM inspection_images
UNION ALL SELECT 'visual_findings', COUNT(*) FROM visual_findings
UNION ALL SELECT 'process_readings', COUNT(*) FROM process_readings
UNION ALL SELECT 'anomalies', COUNT(*) FROM anomalies
UNION ALL SELECT 'spc_results', COUNT(*) FROM spc_results
UNION ALL SELECT 'quality_incidents', COUNT(*) FROM quality_incidents
UNION ALL SELECT 'rca_hypotheses', COUNT(*) FROM rca_hypotheses
UNION ALL SELECT 'historical_incidents', COUNT(*) FROM historical_incidents
UNION ALL SELECT 'capa_actions', COUNT(*) FROM capa_actions
UNION ALL SELECT 'effectiveness_checks', COUNT(*) FROM effectiveness_checks
UNION ALL SELECT 'agent_runs', COUNT(*) FROM agent_runs
UNION ALL SELECT 'human_decisions', COUNT(*) FROM human_decisions
UNION ALL SELECT 'maintenance_records', COUNT(*) FROM maintenance_records;

-- Query 2: BATCH-0245 anchor batch with product part number, machine code, shift, and quantity.
SELECT 
    b.batch_number,
    p.part_number,
    p.name AS product_name,
    m.code AS machine_code,
    b.shift,
    b.quantity,
    b.material_lot,
    b.status AS batch_status,
    b.start_time
FROM batches b
JOIN products p ON b.product_id = p.id
JOIN machines m ON b.machine_id = m.id
WHERE b.batch_number = 'BATCH-0245';

-- Query 3: BATCH-0245 sample measurements with specification limits, conformance status, and deviations (flagging P003, P004, P005).
SELECT 
    m.component_id AS part_serial,
    m.value AS measured_diameter_mm,
    ic.nominal AS nominal_mm,
    ic.lsl AS lower_spec_limit,
    ic.usl AS upper_spec_limit,
    m.status AS conformance_status,
    m.deviation_from_limit AS limit_deviation_mm,
    CASE 
        WHEN m.status = 'nonconforming' THEN 'NONCONFORMING (EXCEEDS USL)'
        ELSE 'CONFORMING'
    END AS evaluation_label
FROM measurements m
JOIN batches b ON m.batch_id = b.id
JOIN inspection_characteristics ic ON m.characteristic_id = ic.id
WHERE b.batch_number = 'BATCH-0245'
ORDER BY m.component_id ASC;

-- Query 4: Process readings for CNC-04 around BATCH-0245 displaying tool usage cycles, vibration, and cutting speeds.
SELECT 
    pr.ts AS timestamp_utc,
    m.code AS machine_code,
    pr.spindle_speed AS spindle_rpm,
    pr.feed_rate AS feed_mm_rev,
    pr.vibration AS vibration_radial_mms,
    pr.coolant_temp AS coolant_celsius,
    pr.tool_usage_cycles,
    CASE 
        WHEN pr.tool_usage_cycles > 800 THEN 'OVERDUE (+91% TOOL LIFE)'
        ELSE 'NORMAL'
    END AS tool_condition
FROM process_readings pr
JOIN machines m ON pr.machine_id = m.id
JOIN batches b ON pr.batch_id = b.id
WHERE b.batch_number = 'BATCH-0245'
ORDER BY pr.ts DESC
LIMIT 10;

-- Query 5: Statistical and threshold anomalies detected for BATCH-0245 across sensors.
SELECT 
    a.id AS anomaly_id,
    b.batch_number,
    m.code AS machine_code,
    a.parameter,
    a.type AS anomaly_type,
    a.score AS anomaly_score,
    a.method AS detection_algorithm,
    a.ts AS detection_timestamp
FROM anomalies a
JOIN batches b ON a.batch_id = b.id
JOIN machines m ON a.machine_id = m.id
WHERE b.batch_number = 'BATCH-0245'
ORDER BY a.score DESC;

-- Query 6: SPC control results with statistical control limits (UCL/LCL) and engineering specification limits (USL/LSL) in separate columns.
SELECT 
    spc.chart_type,
    ic.nominal AS engineering_nominal,
    ic.lsl AS spec_limit_lsl,
    ic.usl AS spec_limit_usl,
    spc.center_line AS statistical_center_line,
    spc.lcl AS control_limit_lcl,
    spc.ucl AS control_limit_ucl,
    spc.cp,
    spc.cpk,
    spc.n AS sample_size,
    CASE 
        WHEN spc.cpk < 1.0 THEN 'INCAPABLE PROCESS (CPK < 1.0)'
        ELSE 'CAPABLE'
    END AS capability_assessment
FROM spc_results spc
JOIN batches b ON spc.batch_id = b.id
JOIN inspection_characteristics ic ON spc.characteristic_id = ic.id
WHERE b.batch_number = 'BATCH-0245';

-- Query 7: Quality incident and ranked RCA hypotheses with score, epistemic label, and categorized evidence.
SELECT 
    qi.title AS incident_title,
    rh.rank AS hypothesis_rank,
    rh.category AS ishikawa_6m_branch,
    rh.title AS hypothesis_theory,
    rh.label AS epistemic_label,
    rh.evidence_score,
    rh.confidence_text,
    rh.status AS validation_status
FROM rca_hypotheses rh
JOIN quality_incidents qi ON rh.incident_id = qi.id
ORDER BY rh.rank ASC;

-- Query 8: Historical non-conformance incidents matched via vector RAG retrieval (highlighting NCR-019).
SELECT 
    hi.ncr_id,
    hi.title,
    hi.defect_type,
    hi.part_number,
    hi.machine,
    hi.confirmed_root_cause,
    hi.resolution,
    hi.date AS occurrence_date
FROM historical_incidents hi
WHERE hi.ncr_id = 'NCR-019' OR hi.title LIKE '%tool wear%'
ORDER BY hi.ncr_id ASC;

-- Query 9: CAPA actions with 3-tiered type, status, responsible role, approver, and approval timestamp.
SELECT 
    ca.action_code,
    ca.type AS capa_tier,
    ca.description,
    ca.responsible_role,
    ca.due_date,
    ca.status AS execution_status,
    u.name AS approved_by_user,
    ca.approved_at
FROM capa_actions ca
LEFT JOIN users u ON ca.approved_by = u.id
ORDER BY ca.action_code ASC;

-- Query 10: Multi-agent execution trace for workflow showing agent name, tool calls, and execution timings.
SELECT 
    ar.workflow_id,
    ar.agent_name,
    ar.started_at,
    ar.finished_at,
    ar.status AS agent_status,
    ar.tool_calls_json
FROM agent_runs ar
ORDER BY ar.started_at ASC;

-- Query 11: Human-in-the-Loop decision audit trail recording engineering confirmations and batch dispositions.
SELECT 
    hd.workflow_id,
    hd.entity_type,
    hd.entity_id,
    hd.decision AS engineering_decision,
    hd.comment AS engineering_justification,
    u.name AS authorized_engineer,
    u.role AS engineer_role,
    hd.ts AS decision_timestamp
FROM human_decisions hd
JOIN users u ON hd.user_id = u.id
ORDER BY hd.ts DESC;

-- Query 12: CAPA statistical effectiveness checks comparing pre- and post-intervention rejection rates with p-values.
SELECT 
    ec.capa_id,
    ec.rejection_rate_before AS pre_rejection_rate_pct,
    ec.rejection_rate_after AS post_rejection_rate_pct,
    ec.test_used AS hypothesis_test,
    ec.p_value,
    ec.conclusion_label,
    ec.notes AS statistical_disclaimer
FROM effectiveness_checks ec;

-- Query 13: Visual inspection defect findings with model version, defect type, and human engineer confirmation status.
SELECT 
    vf.id AS finding_id,
    ii.component_id AS part_serial,
    vf.defect_detected,
    vf.defect_type,
    vf.confidence,
    vf.model_version,
    vf.human_status AS engineering_review_status,
    u.name AS reviewed_by_engineer
FROM visual_findings vf
JOIN inspection_images ii ON vf.image_id = ii.id
LEFT JOIN users u ON vf.reviewer_id = u.id
ORDER BY vf.id ASC;
