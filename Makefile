.PHONY: setup test run run-once status ui api clean version version-patch version-minor version-major

PYTHON := python3

setup:
	@echo "Installing dependencies..."
	uv pip install -r requirements.txt
	@echo "Setup complete."

test:
	@echo "Running Tests..."
	uv run pytest tests/ -v

run:
	@echo "Running Pipeline Orchestrator..."
	uv run python -m src run

run-once:
	@echo "Processing one task..."
	uv run python -m src run --once

status:
	@echo "Pipeline Status..."
	uv run python -m src status

ui:
	@echo "Starting Control Center..."
	uv run streamlit run src/ui/app.py

api:
	@echo "Starting API Server..."
	uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

clean:
	@echo "Cleaning up..."
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf src/*/__pycache__
	rm -f data/*.db
	rm -f data/bronze/*.json

version:
	@echo "Current version:"
	@uv run python -c "from src.__version__ import __version__; print(__version__)"

version-patch:
	@echo "Bumping patch version..."
	uv run python scripts/bump_version.py patch

version-minor:
	@echo "Bumping minor version..."
	uv run python scripts/bump_version.py minor

version-major:
	@echo "Bumping major version..."
	uv run python scripts/bump_version.py major
