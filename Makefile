.PHONY: setup test run ui clean version version-patch version-minor version-major

PYTHON := python3

setup:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Setup complete."

test:
	@echo "Running Tests..."
	uv run pytest tests/ -v


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

version:
	@echo "Current version:"
	@$(PYTHON) -c "from src.__version__ import __version__; print(__version__)"

version-patch:
	@echo "Bumping patch version..."
	$(PYTHON) scripts/bump_version.py patch

version-minor:
	@echo "Bumping minor version..."
	$(PYTHON) scripts/bump_version.py minor

version-major:
	@echo "Bumping major version..."
	$(PYTHON) scripts/bump_version.py major
