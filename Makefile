.PHONY: setup test run ui clean

PYTHON := python3

setup:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Setup complete."

test:
	@echo "Running Tests..."
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) -m pytest tests/ || echo "Pytest not found, running scripts individually..."
	# Fallback if pytest isn't installed, though we should probably add it.
	# For now, run our verification scripts
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) tests/test_silver.py
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) tests/test_loader.py
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) tests/test_mcp_manager.py
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) tests/test_scout.py

run:
	@echo "Running Pipeline Orchestrator..."
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) -m src run

run-once:
	@echo "Processing one task..."
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) -m src run --once

status:
	@echo "Pipeline Status..."
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) -m src status

ui:
	@echo "Starting Control Center..."
	export PYTHONPATH=$PYTHONPATH:. && $(PYTHON) -m streamlit run src/ui/app.py

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf src/*/__pycache__
	rm -f data/*.db
	rm -f data/bronze/*.json
