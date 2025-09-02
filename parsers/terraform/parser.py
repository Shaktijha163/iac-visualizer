import json
from typing import Dict, Any
from graph.models import ResourceGraph, Node, Edge

class TerraformParser:
    def __init__(self):
        self.graph = ResourceGraph()
        
    def parse_plan(self, plan_json: Dict[str, Any]) -> ResourceGraph:
        # Parse Terraform plan JSON
        if 'resource_changes' not in plan_json:
            raise ValueError("Invalid Terraform plan JSON")
            
        # Process each resource change
        for resource in plan_json['resource_changes']:
            self._process_resource(resource)
            
        return self.graph
    
    def _process_resource(self, resource: Dict[str, Any]):
        # Create node for resource
        address = resource.get('address', '')
        resource_type = resource.get('type', '')
        resource_name = resource.get('name', '')
        
        node_id = f"tf:{resource_type}:{address}"
        
        node = Node(
            id=node_id,
            type=f"tf.{resource_type}",
            name=resource_name,
            attributes={
                "change": resource.get('change', {}),
                "provider": resource.get('provider_name', '')
            }
        )
        
        self.graph.add_node(node)
        
        # Process dependencies
        for dep in resource.get('depends_on', []):
            edge = Edge(
                from_id=node_id,
                to_id=dep,
                reason="depends_on"
            )
            self.graph.add_edge(edge)
