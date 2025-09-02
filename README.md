# IAC Visualizer

**Parse Terraform/Kubernetes/Helm and render an interactive, scalable dependency graph with impact analysis and drift hints.**

A comprehensive infrastructure-as-code visualization tool that automatically discovers dependencies and relationships across Terraform, Kubernetes, and Helm configurations.

##  Features

- **Multi-Format Support**: Parse Terraform plans, Kubernetes manifests, and Helm charts
- **Dependency Discovery**: Automatically detect explicit and implicit relationships
- **Interactive API**: RESTful API for programmatic access
- **CLI Interface**: Command-line tool for local development
- **Graph Export**: Generate JSON graphs for visualization

##  Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd iac-visualizer

# Create virtual environment (optional but recommended)
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Helm CLI (required for Helm parsing)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

iac-visualizer/
├── cli/                 # Command-line interface
├── server/              # FastAPI web server
├── parsers/             # Infrastructure parsing engines
│   ├── terraform/       # Terraform plan parser
│   ├── kubernetes/      # Kubernetes YAML parser  
│   └── helm/            # Helm chart parser
├── graph/               # Graph data models
├── examples/            # Sample infrastructure files
│   ├── terraform/       # Terraform examples
│   ├── kubernetes/      # Kubernetes examples
│   └── helm/            # Helm chart examples
├── tests/               # Test suite
└── requirements.txt     # Python dependencies


## Command Line Interface (CLI)


# Parse Terraform plan
python cli/main.py ingest examples/terraform/complex.plan.json --type terraform

# Parse Kubernetes manifests
python cli/main.py ingest examples/kubernetes/deployment.yaml --type kubernetes

# Parse Helm chart
python cli/main.py ingest examples/helm/web-app-0.1.0.tgz --type helm

# Parse with custom output file
python cli/main.py ingest plan.json --type terraform --out custom-graph.json

# Use server API instead of local parsing
python cli/main.py ingest plan.json --type terraform --server http://localhost:8000



## Web Server API
# Start the web server
python -m server.app
# Server runs on http://localhost:8000

# API endpoints:
curl -X POST -F "file=@plan.json" http://localhost:8000/api/parse/terraform
curl -X POST -F "files=@deployment.yaml" http://localhost:8000/api/parse/kubernetes
curl -X POST -F "chart=@chart.tgz" http://localhost:8000/api/parse/helm

# Get health status
curl http://localhost:8000/health

# Get example files
curl http://localhost:8000/api/examples/terraform
curl http://localhost:8000/api/examples/kubernetes
curl http://localhost:8000/api/examples/helm


## Examples 
# Test with provided examples

# Terraform - AWS infrastructure
python cli/main.py ingest examples/terraform/complex.plan.json --type terraform

# Kubernetes - Microservices deployment
python cli/main.py ingest examples/kubernetes/deployment.yaml --type kubernetes

# Helm - Web application chart
python cli/main.py ingest examples/helm/web-app-0.1.0.tgz --type helm

# Multiple Kubernetes files
python cli/main.py ingest "examples/kubernetes/*.yaml" --type kubernetes