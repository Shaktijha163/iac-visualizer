# debug_parser.py
from parsers.terraform.parser import TerraformParser
import json

with open('examples/terraform/complex.plan.json', 'r') as f:
    plan_data = json.load(f)

parser = TerraformParser()
graph = parser.parse_plan(plan_data)

print("=== DEBUGGING IMPLICIT DEPENDENCIES ===")

# Check if change_after data is present
for node in graph.nodes:
    print(f"\nNode: {node.id}")
    if 'change_after' in node.attributes:
        print(f"  change_after: {node.attributes['change_after']}")
        
        # Manually test reference extraction
        if node.id == 'tf:aws_vpc:aws_vpc.main':
            print("  Testing reference extraction on VPC tags:")
            tags = node.attributes['change_after'].get('tags', {})
            if 'Name' in tags:
                test_value = tags['Name']
                print(f"  Tag value: {test_value}")
                references = parser._extract_references_from_string(test_value)
                print(f"  Found references: {references}")
    else:
        print("  No change_after data found!")