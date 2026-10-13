.PHONY: train-cv test test-cv audit

audit:
	python scripts/audit/run_all_audit.py

train-cv:
	python scripts/train_cv.py

test-cv:
	pytest backend/tests/test_phase2.py backend/tests/test_universal_llm_and_yolo.py -v

test:
	pytest backend/tests/ -v
