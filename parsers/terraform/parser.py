import json
import re
from typing import Dict, Any, List, Optional
from graph.models import ResourceGraph, Node, Edge


class TerraformParser:
    def __init__(self):
        self.graph = ResourceGraph()
        self.graph.meta = {"parser": "terraform"}
        self._resource_cache = {}  # Cache for quick lookup
        
    def parse_plan(self, plan_json: Dict[str, Any]) -> ResourceGraph:
        """Parse Terraform plan JSON into a resource graph"""
        if 'resource_changes' not in plan_json:
            raise ValueError("Invalid Terraform plan JSON")
            
        # Clear previous state
        self.graph = ResourceGraph()
        self.graph.meta = {
            "parser": "terraform",
            "terraform_version": plan_json.get('terraform_version', 'unknown'),
            "format_version": plan_json.get('format_version', 'unknown')
        }
        self._resource_cache = {}
            
        # Process each resource change
        for resource in plan_json['resource_changes']:
            self._process_resource(resource)
            
        # Second pass to find implicit dependencies
        self._find_implicit_dependencies()
            
        return self.graph
    
    def _process_resource(self, resource: Dict[str, Any]):
        """Process a single Terraform resource"""
        address = resource.get('address', '')
        resource_type = resource.get('type', '')
        resource_name = resource.get('name', '')
        module_address = resource.get('module_address', '')
        
        # Create unique node ID
        node_id = f"tf:{resource_type}:{address}"
        
        # Extract change information
        change = resource.get('change', {})
        actions = change.get('actions', [])
        change_type = self._get_change_type(actions)
        
        # Create node with change data
        node = Node(
            id=node_id,
            type=f"tf.{resource_type}",
            name=resource_name,
            namespace=module_address or "root",
            attributes={
                "change_actions": actions,
                "change_type": change_type,
                "provider": resource.get('provider_name', ''),
                "address": address,
                "module": module_address,
                "source": self._get_source_info(resource),
                "change_after": change.get('after', {}),
                "change_before": change.get('before', {})
            }
        )
        
        self.graph.add_node(node)
        
        # FIXED: Better cache key management
        # Always store the bare address
        self._resource_cache[address] = node_id
        
        # For module resources, also store the full qualified name
        if module_address:
            # For resources in modules, store both ways:
            # 1. module.network.aws_vpc.main (full qualified)
            # 2. aws_vpc.main (for internal module references)
            full_qualified = f"{module_address}.{address}"
            self._resource_cache[full_qualified] = node_id
        
        # Process explicit dependencies
        for dep_address in resource.get('depends_on', []):
            self._add_dependency_edge(node_id, dep_address, "depends_on")

    
    def _find_implicit_dependencies(self):
        """Find implicit dependencies by analyzing resource attributes"""
        for node in self.graph.nodes:
            if not node.attributes.get('change_actions'):
                continue
                
            # Look for references in resource attributes
            change_after = node.attributes.get('change_after', {})
            if isinstance(change_after, dict):
                self._scan_attributes_for_references(node.id, change_after)
    
    def _scan_attributes_for_references(self, source_node_id: str, attributes: Dict[str, Any]):
        """Recursively scan attributes for resource references"""
        for key, value in attributes.items():
            if isinstance(value, str):
                # Look for Terraform references like aws_vpc.main.id
                references = self._extract_references_from_string(value)
                for ref in references:
                    self._add_dependency_edge(source_node_id, ref, "attribute_reference")
            elif isinstance(value, dict):
                self._scan_attributes_for_references(source_node_id, value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._scan_attributes_for_references(source_node_id, item)
                    elif isinstance(item, str):
                        references = self._extract_references_from_string(item)
                        for ref in references:
                            self._add_dependency_edge(source_node_id, ref, "attribute_reference")

    def _extract_references_from_string(self, value: str) -> List[str]:
        """Extract Terraform resource references from string values"""
        # Skip values that are clearly not references
        if not isinstance(value, str) or len(value) < 3:
            return []
        
        # FIXED: Use a set to avoid duplicates and more precise patterns
        references = set()
        
        # Pattern 1: ${reference} - interpolation syntax
        interpolation_pattern = r'\$\{([^}]+)\}'
        interpolation_matches = re.findall(interpolation_pattern, value)
        
        for match in interpolation_matches:
            # Clean up the reference (remove function calls, attributes, etc.)
            ref = self._clean_reference(match)
            if ref:
                references.add(ref)
        
        # Pattern 2: Direct references (less common in JSON, but possible)
        # Only look for this if no interpolation was found
        if not references:
            direct_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\b'
            direct_matches = re.findall(direct_pattern, value)
            
            for match in direct_matches:
                # Skip obvious non-references
                if self._is_likely_reference(match):
                    ref = self._clean_reference(match)
                    if ref:
                        references.add(ref)
        
        return list(references)
    
    def _clean_reference(self, ref_string: str) -> Optional[str]:
        """Clean and validate a reference string"""
        if not ref_string or ref_string.isdigit():
            return None
        
        # Split into parts
        parts = ref_string.split('.')
        
        # Filter out obvious non-references
        if len(parts) < 2 or parts[0] in ['true', 'false', 'null']:
            return None
        
        # Handle different reference types
        if parts[0] == 'module':
            # module.network.aws_subnet.public.id -> module.network.aws_subnet.public
            if len(parts) >= 4:
                return '.'.join(parts[:4])
        elif parts[0] == 'data':
            # data.aws_region.current.name -> data.aws_region.current  
            if len(parts) >= 3:
                return '.'.join(parts[:3])
        elif parts[0] in ['var', 'local']:
            # Skip variables and locals
            return None
        else:
            # aws_vpc.main.id -> aws_vpc.main
            if len(parts) >= 2:
                return '.'.join(parts[:2])
        
        return None
    
    def _is_likely_reference(self, value: str) -> bool:
        """Determine if a string is likely a Terraform resource reference"""
        # Simple heuristics to avoid false positives
        parts = value.split('.')
        
        # Must have at least 2 parts
        if len(parts) < 2:
            return False
        
        # First part should look like a resource type or module/data
        first_part = parts[0]
        if first_part in ['module', 'data']:
            return True
        
        # Should start with a letter and contain underscores (typical resource type pattern)
        if first_part[0].isalpha() and '_' in first_part:
            return True
        
        return False
    
    def _add_dependency_edge(self, source_node_id: str, target_address: str, reason: str):
        """Add a dependency edge between nodes"""
        # FIXED: Better lookup logic for cross-module references
        target_node_id = self._find_target_node(source_node_id, target_address)
        
        if target_node_id:
            # Check if edge already exists
            existing_edge = any(
                edge.from_id == source_node_id and edge.to_id == target_node_id and edge.reason == reason
                for edge in self.graph.edges
            )
            if not existing_edge:
                edge = Edge(
                    from_id=source_node_id,
                    to_id=target_node_id,
                    reason=reason
                )
                self.graph.add_edge(edge)
        else:
            # Debug: Print missing references with more context
            print(f"DEBUG: Could not resolve reference '{target_address}' from '{source_node_id}'")
            print(f"       Available addresses: {sorted(self._resource_cache.keys())}")
    
    def _find_target_node(self, source_node_id: str, target_address: str) -> Optional[str]:
        """Find the target node ID for a given address, considering module context"""
        # Direct lookup first
        if target_address in self._resource_cache:
            return self._resource_cache[target_address]
        
        # Get source node's module context
        source_node = next((node for node in self.graph.nodes if node.id == source_node_id), None)
        if not source_node:
            return None
        
        source_module = source_node.namespace if source_node.namespace != "root" else None
        
        # If target starts with module.X and source is not in a module, direct lookup
        if target_address.startswith('module.'):
            return self._resource_cache.get(target_address)
        
        # If source is in a module and target doesn't specify module, try module-qualified lookup
        if source_module and not target_address.startswith('module.'):
            qualified_address = f"{source_module}.{target_address}"
            if qualified_address in self._resource_cache:
                return self._resource_cache[qualified_address]
        
        return None
    
    def _get_change_type(self, actions: List[str]) -> str:
        """Determine the type of change from actions"""
        if not actions:
            return "no-op"
        if actions == ["create"]:
            return "create"
        if actions == ["delete"]:
            return "delete"
        if actions == ["update"]:
            return "update"
        if "create" in actions and "delete" in actions:
            return "replace"
        return "unknown"
    
    def _get_source_info(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Extract source information from resource"""
        # This would be enhanced with actual source file parsing
        return {
            "address": resource.get('address', ''),
            "module": resource.get('module_address', '')
        }
    
    def _get_resource_type_from_address(self, address: str) -> str:
        """Extract resource type from Terraform address"""
        parts = address.split('.')
        return parts[0] if len(parts) > 0 else 'unknown'