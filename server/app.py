# server/app.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any
import json
# Import our parsers
try:
    from parsers.terraform.parser import TerraformParser
    from parsers.kubernetes.parser import KubernetesParser
except ImportError:
    # Handle the case where parsers aren't available
    TerraformParser = None
    KubernetesParser = None

app = FastAPI(
    title="IAC Visualizer API",
    description="API for parsing infrastructure-as-code and generating dependency graphs",
    version="0.1.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "IAC Visualizer API", "version": "0.1.0"}

# Add to health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "parsers_available": {
        "terraform": TerraformParser is not None,
        "kubernetes": KubernetesParser is not None,
        "helm": HelmParser is not None
    }}

@app.post("/api/parse/terraform")
async def parse_terraform(file: UploadFile = File(...)):
    """Parse a Terraform plan JSON file"""
    if not TerraformParser:
        raise HTTPException(status_code=501, detail="Terraform parser not available")
    
    # Check file type
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".json", delete=False) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Parse the Terraform plan
        with open(temp_path, 'r') as f:
            plan_data = json.load(f)
        
        parser = TerraformParser()
        graph = parser.parse_plan(plan_data)
        
        # Convert to serializable format
        result = {
            "nodes": [node.dict() for node in graph.nodes],
            "edges": [edge.dict() for edge in graph.edges],
            "meta": graph.meta
        }
        
        return JSONResponse(content=result)
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing Terraform plan: {str(e)}")
    finally:
        # Clean up temporary file
        os.unlink(temp_path)

@app.post("/api/parse/kubernetes")
async def parse_kubernetes(files: List[UploadFile] = File(...)):
    """Parse one or more Kubernetes YAML files"""
    if not KubernetesParser:
        raise HTTPException(status_code=501, detail="Kubernetes parser not available")
    
    # Save uploaded files to temporary location
    temp_paths = []
    for file in files:
        if not (file.filename.endswith('.yaml') or file.filename.endswith('.yml')):
            raise HTTPException(status_code=400, detail="All files must be YAML files")
        
        with tempfile.NamedTemporaryFile(mode="w+b", suffix=".yaml", delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_paths.append(temp_file.name)
    
    try:
        # Parse the Kubernetes files
        parser = KubernetesParser()
        graph = parser.parse_files(temp_paths)
        
        # Convert to serializable format
        result = {
            "nodes": [node.dict() for node in graph.nodes],
            "edges": [edge.dict() for edge in graph.edges],
            "meta": graph.meta
        }
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing Kubernetes files: {str(e)}")
    finally:
        # Clean up temporary files
        for path in temp_paths:
            os.unlink(path)

@app.get("/api/examples/{example_type}")
async def get_example(example_type: str):
    """Get example files for testing"""
    examples_dir = Path("examples")
    
    if example_type == "terraform":
        example_file = examples_dir / "terraform" / "complex.plan.json"
        if not example_file.exists():
            raise HTTPException(status_code=404, detail="Terraform example not found")
        
        with open(example_file, 'r') as f:
            content = json.load(f)
        
        return JSONResponse(content=content)
    
    elif example_type == "kubernetes":
        example_files = []
        kubernetes_dir = examples_dir / "kubernetes"
        
        for file_path in kubernetes_dir.glob("*.yaml"):
            with open(file_path, 'r') as f:
                content = f.read()
                example_files.append({
                    "filename": file_path.name,
                    "content": content
                })
        
        return JSONResponse(content=example_files)
    
    else:
        raise HTTPException(status_code=404, detail="Example type not found")
    
# server/app.py (add these imports and endpoints)
try:
    from parsers.helm.parser import HelmParser
except ImportError:
    HelmParser = None
from fastapi import Response
@app.post("/api/parse/helm")
async def parse_helm(
    chart: UploadFile = File(...),
    values_files: List[UploadFile] = File([]),
    namespace: str = "default",
    release_name: str = "test-release"
):
    """Parse a Helm chart"""
    if not HelmParser:
        raise HTTPException(status_code=501, detail="Helm parser not available")
    
    # Check file type
    if not chart.filename.endswith('.tgz') and not chart.filename.endswith('.tar.gz'):
        raise HTTPException(status_code=400, detail="Chart must be a .tgz or .tar.gz file")
    
    # Save uploaded files to temporary location
    temp_files = {}
    
    try:
        # Save chart
        chart_content = await chart.read()
        with tempfile.NamedTemporaryFile(mode="w+b", suffix=".tgz", delete=False) as temp_chart:
            temp_chart.write(chart_content)
            temp_files["chart"] = temp_chart.name
        
        # Save values files
        temp_values = []
        for values_file in values_files:
            values_content = await values_file.read()
            with tempfile.NamedTemporaryFile(mode="w+b", suffix=".yaml", delete=False) as temp_values_file:
                temp_values_file.write(values_content)
                temp_values.append(temp_values_file.name)
        
        temp_files["values"] = temp_values
        
        # Parse the Helm chart
        parser = HelmParser()
        graph = parser.parse_chart(
            chart_path=temp_files["chart"],
            values_files=temp_files["values"],
            namespace=namespace,
            release_name=release_name
        )
        
        # Convert to serializable format
        result = {
            "nodes": [node.dict() for node in graph.nodes],
            "edges": [edge.dict() for edge in graph.edges],
            "meta": graph.meta
        }
        
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing Helm chart: {str(e)}")
    # finally:
    #     # Clean up temporary files
    #     for path in temp_files.get("chart", []):
    #         if os.path.exists(path):
    #             os.unlink(path)
    #     for path in temp_files.get("values", []):
    #         if os.path.exists(path):
    #             os.unlink(path)
    finally:
        # Clean up temporary files
        chart_path = temp_files.get("chart")
        if chart_path and os.path.exists(chart_path):
            os.unlink(chart_path)

        for path in temp_files.get("values", []):
            if os.path.exists(path):
                os.unlink(path)


@app.get("/api/examples/helm")
async def get_helm_example():
    """Get example Helm chart for testing"""
    # Create a tarball of the example chart
    import tarfile
    import io
    
    chart_dir = Path("examples") / "helm" / "web-app"
    
    # Create in-memory tarball
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        for file_path in chart_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(chart_dir.parent)
                tar.add(file_path, arcname=arcname)
    
    tar_buffer.seek(0)
    
    return Response(
        content=tar_buffer.getvalue(),
        media_type="application/gzip",
        headers={"Content-Disposition": "attachment; filename=web-app-chart.tgz"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)