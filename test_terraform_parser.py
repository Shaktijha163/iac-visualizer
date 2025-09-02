# test_final.py
from parsers.terraform.parser import TerraformParser
import json

# Test the reference extraction
parser = TerraformParser()

test_values = [
    "main-vpc-${data.aws_region.current.name}",
    "${aws_vpc.main.id}", 
    "${module.network.aws_subnet.public.id}",
    "echo ${aws_vpc.main.cidr_block}"
]

print("=== TESTING REFERENCE EXTRACTION ===")
for value in test_values:
    refs = parser._extract_references_from_string(value)
    print(f"'{value}' -> {refs}")

# Test with updated plan data
with open('examples/terraform/complex.plan.json', 'r') as f:
    plan_data = json.load(f)

graph = parser.parse_plan(plan_data)
print(f"\n=== PARSER RESULTS ===")
print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
for edge in graph.edges:
    print(f"  {edge.from_id} -> {edge.to_id} ({edge.reason})")

print("\n=== CACHE CONTENTS ===")
for address, node_id in parser._resource_cache.items():
    print(f"  {address} -> {node_id}")