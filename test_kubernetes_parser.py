# test_kubernetes.py
from parsers.kubernetes.parser import KubernetesParser

# Test the Kubernetes parser
parser = KubernetesParser()

# Parse the example files
file_paths = [
    'examples/kubernetes/deployment.yaml',
    'examples/kubernetes/configs.yaml', 
    'examples/kubernetes/ingress.yaml'
]

graph = parser.parse_files(file_paths)

print("=== KUBERNETES PARSER RESULTS ===")
print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")

print("\nNodes found:")
for node in graph.nodes:
    print(f"  {node.id}")

print("\nEdges found:")
for edge in graph.edges:
    print(f"  {edge.from_id} -> {edge.to_id} ({edge.reason})")

print("\n=== RELATIONSHIP SUMMARY ===")
# Count edges by type
edge_types = {}
for edge in graph.edges:
    edge_types[edge.reason] = edge_types.get(edge.reason, 0) + 1

for reason, count in edge_types.items():
    print(f"  {reason}: {count} edges")