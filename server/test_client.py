# server/test_client.py
import requests
import json
from pathlib import Path


def test_terraform_parsing():
    """Test the Terraform parsing endpoint"""
    url = "http://localhost:8000/api/parse/terraform"
    
    # Use our example file
    with open("examples/terraform/complex.plan.json", "rb") as f:
        files = {"file": ("complex.plan.json", f, "application/json")}
        response = requests.post(url, files=files)
    
    print("Terraform parsing result:")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Nodes: {len(result['nodes'])}")
        print(f"Edges: {len(result['edges'])}")
        print("Sample node:", json.dumps(result['nodes'][0], indent=2) if result['nodes'] else "None")
    else:
        print(f"Error: {response.text}")

def test_kubernetes_parsing():
    """Test the Kubernetes parsing endpoint"""
    url = "http://localhost:8000/api/parse/kubernetes"
    
    # Use our example files
    files = []
    kubernetes_files = [
        "examples/kubernetes/deployment.yaml",
        "examples/kubernetes/configs.yaml",
        "examples/kubernetes/ingress.yaml"
    ]
    
    for file_path in kubernetes_files:
        files.append(("files", (Path(file_path).name, open(file_path, "rb"), "application/yaml")))
    
    response = requests.post(url, files=files)
    
    print("\nKubernetes parsing result:")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Nodes: {len(result['nodes'])}")
        print(f"Edges: {len(result['edges'])}")
        print("Sample node:", json.dumps(result['nodes'][0], indent=2) if result['nodes'] else "None")
    else:
        print(f"Error: {response.text}")
    
    # Close files
    for _, (_, file, _) in files:
        file.close()

if __name__ == "__main__":
    # Start the server first, then run these tests
    print("Make sure the server is running on localhost:8000")
    test_terraform_parsing()
    test_kubernetes_parsing()