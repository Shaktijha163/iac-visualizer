#!/usr/bin/env python3
"""
IAC Visualizer CLI tool
"""
import argparse
import json
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="IAC Visualizer CLI")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest IaC files')
    ingest_parser.add_argument('file', help='Path to the IaC file')
    ingest_parser.add_argument('--type', choices=['terraform', 'kubernetes', 'helm'], 
                              help='Type of IaC file')
    ingest_parser.add_argument('--out', default='graph.json', help='Output file')
    
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
        else:
            print("Error: Could not determine file type. Please specify --type")
            sys.exit(1)
    
    print(f"Ingesting {args.type} file: {args.file}")
    
    # For now, just create a dummy graph
    dummy_graph = {
        "nodes": [
            {
                "id": "dummy:node:1",
                "type": "dummy.type",
                "name": "dummy-node",
                "attributes": {"source_file": str(args.file)}
            }
        ],
        "edges": [],
        "meta": {
            "source": args.file,
            "type": args.type
        }
    }
    
    # Write output
    with open(args.out, 'w') as f:
        json.dump(dummy_graph, f, indent=2)
    
    print(f"Graph saved to {args.out}")

def handle_serve(args):
    """Handle the serve command"""
    print(f"Starting server on {args.host}:{args.port}")
    print("Note: Server functionality will be implemented in Week 2")
    # This will be implemented later with FastAPI

if __name__ == '__main__':
    main()
