.PHONY: test render-slo check-slo validate compose-up compose-down deploy rollback drill

test:
	PYTHONPATH=service python -m unittest discover -s tests -v

render-slo:
	python scripts/render_slo_rules.py

check-slo:
	python scripts/render_slo_rules.py --check

validate: test check-slo
	python scripts/validate_configs.py
	python -m compileall -q service sre_tools scripts tools tests

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down

deploy:
	./scripts/deploy.sh

rollback:
	./scripts/rollback.sh

drill:
	CONFIRM_CHAOS=sre-observatory ./scripts/chaos-drill.sh

