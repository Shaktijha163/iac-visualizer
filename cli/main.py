import argparse
import sys
import requests
import json
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

# Add to the imports section
try:
    from parsers.terraform.parser import TerraformParser
    print(f"DEBUG: TerraformParser imported successfully: {TerraformParser}")
except ImportError as e:
    print(f"DEBUG: TerraformParser import failed: {e}")
    TerraformParser = None

try:
    from parsers.kubernetes.parser import KubernetesParser
    print(f"DEBUG: KubernetesParser imported successfully: {KubernetesParser}")
except ImportError as e:
    print(f"DEBUG: KubernetesParser import failed: {e}")
    KubernetesParser = None

try:
    from parsers.helm.parser import HelmParser
    print(f"DEBUG: HelmParser imported successfully: {HelmParser}")
except ImportError as e:
    print(f"DEBUG: HelmParser import failed: {e}")
    HelmParser = None

def main():
    parser = argparse.ArgumentParser(description="IAC Visualizer CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest IaC files')
    ingest_parser.add_argument('file', help='Path to the IaC file')
    ingest_parser.add_argument('--type', choices=['terraform', 'kubernetes', 'helm'], 
                              help='Type of IaC file')
    ingest_parser.add_argument('--out', default='graph.json', help='Output file')
    ingest_parser.add_argument('--server', help='Use API server instead of local parsing')
    
    # Add Helm-specific options
    ingest_parser.add_argument('--values', nargs='*', help='Helm values files (for Helm charts)')
    ingest_parser.add_argument('--namespace', default='default', help='Namespace (for Helm charts)')
    ingest_parser.add_argument('--release-name', default='test-release', help='Release name (for Helm charts)')
    
    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Start the web server')
    serve_parser.add_argument('--host', default='localhost', help='Host to bind to')
    serve_parser.add_argument('--port', default=8000, type=int, help='Port to listen on')
    
    args = parser.parse_args()
    
    if args.command == 'ingest':
        handle_ingest(args)
    elif args.command == 'serve':
        handle_serve(args)
    else:
        parser.print_help()
        sys.exit(1)


def handle_serve(args):
    """Handle the serve command"""
    print(f"Starting server on {args.host}:{args.port}")
    
    # Import here to avoid dependency issues if not using serve
    import uvicorn
    from server.app import app
    
    uvicorn.run(app, host=args.host, port=args.port)

def use_server_api(args):
    """Use the web API for parsing"""
    url = f"http://{args.server}/api/parse/{args.type}"
    
    try:
        with open(args.file, 'rb') as f:
            files = {'file': (Path(args.file).name, f, 'application/octet-stream')}
            
            # Add additional data for Helm
            data = {}
            if args.type == 'helm':
                if args.values:
                    data['values'] = args.values
                data['namespace'] = args.namespace
                data['release_name'] = args.release_name
            
            response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            with open(args.out, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Graph saved to {args.out} (via API)")
        else:
            print(f"API error: {response.status_code} - {response.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error calling API: {e}")
        sys.exit(1)

def handle_ingest(args):
    """Handle the ingest command"""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File {args.file} does not exist")
        sys.exit(1)
    
    # Determine file type if not specified
    if not args.type:
        if file_path.suffix == '.json':
            args.type = 'terraform'
        elif file_path.suffix in ['.yaml', '.yml']:
            args.type = 'kubernetes'
        elif file_path.suffix in ['.tgz', '.tar.gz'] or file_path.is_dir():
            args.type = 'helm'
        else:
            print("Error: Could not determine file type. Please specify --type")
            sys.exit(1)
    
    # If server flag is provided, use the API
    if hasattr(args, 'server') and args.server:
        use_server_api(args)
    else:
        # Use local parsing
        use_local_parsing(args)

def use_local_parsing(args):
    """Use local parsing"""
    print(f"Ingesting {args.type} file: {args.file}")
    print(f"DEBUG: args.type = '{args.type}', HelmParser = {HelmParser}")
    
    if args.type == 'terraform' and TerraformParser:
        try:
            with open(args.file, 'r') as f:
                plan_data = json.load(f)
            parser = TerraformParser()
            graph = parser.parse_plan(plan_data)
            
            # Convert to dict for JSON serialization
            graph_dict = {
                "nodes": [node.model_dump() for node in graph.nodes],
                "edges": [edge.model_dump() for edge in graph.edges],
                "meta": graph.meta
            }
            
        except Exception as e:
            print(f"Error parsing Terraform plan: {e}")
            sys.exit(1)
            
    elif args.type == 'kubernetes' and KubernetesParser:
        parser = KubernetesParser()
        # Use parse_files instead of parse_yaml
        graph = parser.parse_files([args.file])
        
        # Convert to dict and save
        graph_dict = {
            "nodes": [node.model_dump() for node in graph.nodes],
            "edges": [edge.model_dump() for edge in graph.edges],
            "meta": graph.meta
        }
        
        with open(args.out, 'w') as f:
            json.dump(graph_dict, f, indent=2)
        
        print(f"Kubernetes graph saved to {args.out}")
        print(f"Found {len(graph.nodes)} nodes and {len(graph.edges)} edges")
            
    elif args.type == 'helm' and HelmParser:
        print(f"DEBUG: Using HelmParser: {HelmParser}")
        try:
            parser = HelmParser()
            graph = parser.parse_chart(
                chart_path=args.file,
                values_files=args.values or [],
                namespace=args.namespace,
                release_name=args.release_name
            )
            
            # Convert to dict and save
            graph_dict = {
                "nodes": [node.model_dump() for node in graph.nodes],
                "edges": [edge.model_dump() for edge in graph.edges],
                "meta": graph.meta
            }
            
        except Exception as e:
            print(f"Error parsing Helm chart: {e}")
            sys.exit(1)
            
    else:
        if args.type == 'terraform' and not TerraformParser:
            print("Error: TerraformParser not available")
        elif args.type == 'kubernetes' and not KubernetesParser:
            print("Error: KubernetesParser not available")
        elif args.type == 'helm' and not HelmParser:
            print("Error: HelmParser not available")
        else:
            print(f"Error: Unknown parser type {args.type}")
        
        # Fallback to dummy data
        graph_dict = {
            "nodes": [
                {
                    "id": f"dummy:{args.type}:1",
                    "type": f"dummy.{args.type}",
                    "name": "dummy-node",
                    "attributes": {"source_file": str(args.file)}
                }
            ],
            "edges": [],
            "meta": {
                "source": args.file,
                "type": args.type,
                "error": f"Parser for {args.type} not available"
            }
        }
    
    # Write output
    with open(args.out, 'w') as f:
        json.dump(graph_dict, f, indent=2)
    
    print(f"Graph saved to {args.out}")


if __name__ == '__main__':
    main()