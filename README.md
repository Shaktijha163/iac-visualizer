# IAC Visualizer

Parse Terraform/Kubernetes/Helm and render an interactive, scalable dependency graph with impact analysis and drift hints.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Parse Terraform plan
python -m cli.main ingest plan.json

# Start the web server
python -m server.app
```
