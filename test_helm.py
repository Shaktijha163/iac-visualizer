# test_helm.py
from parsers.helm.parser import HelmParser

def test_helm_parser():
    """Test the Helm parser"""
    # Create a simple test without requiring helm CLI
    parser = HelmParser()
    
    # Test values parsing
    values_path = "examples/helm/web-app/values.yaml"
    values = parser.parse_values(values_path)
    
    print("Helm values parsing:")
    print(f"Replica count: {values.get('replicaCount', 'N/A')}")
    print(f"Image: {values.get('image', {}).get('repository', 'N/A')}:{values.get('image', {}).get('tag', 'N/A')}")
    print(f"Redis enabled: {values.get('redis', {}).get('enabled', 'N/A')}")
    
    # Test chart metadata extraction
    chart_path = "examples/helm/web-app"
    parser._extract_helm_metadata(chart_path)
    
    print("\nChart metadata:")
    if "chart_metadata" in parser.graph.meta:
        metadata = parser.graph.meta["chart_metadata"]
        print(f"Name: {metadata.get('name', 'N/A')}")
        print(f"Version: {metadata.get('version', 'N/A')}")
        print(f"Dependencies: {len(metadata.get('dependencies', []))}")
        
        # Show dependency nodes
        print("\nDependency nodes:")
        for node in parser.graph.nodes:
            if node.type == "helm.dependency":
                print(f"  {node.name} (version: {node.attributes.get('version', 'N/A')})")

if __name__ == "__main__":
    test_helm_parser()