# parsers/kubernetes/parser.py
import yaml
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from graph.models import ResourceGraph, Node, Edge


class KubernetesParser:
    def __init__(self):
        self.graph = ResourceGraph()
        self.graph.meta = {"parser": "kubernetes"}
        self._resource_cache = {}  # Cache for quick lookup
        
    def parse_files(self, file_paths: List[str]) -> ResourceGraph:
        """Parse one or more Kubernetes YAML files"""
        # Clear previous state
        self.graph = ResourceGraph()
        self.graph.meta = {"parser": "kubernetes", "sources": file_paths}
        self._resource_cache = {}
        
        # Process each file
        for file_path in file_paths:
            self._parse_file(file_path)
            
        # Infer relationships between resources
        self._infer_relationships()
            
        return self.graph
    
    def _parse_file(self, file_path: str):
        """Parse a single YAML file (may contain multiple resources)"""
        try:
            with open(file_path, 'r') as f:
                documents = list(yaml.safe_load_all(f))
                
            for doc in documents:
                if doc and isinstance(doc, dict):  # Skip empty documents
                    self._process_resource(doc, file_path)
                    
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
    
    def _process_resource(self, resource: Dict[str, Any], source_file: str):
        """Process a single Kubernetes resource"""
        if not resource.get('kind') or not resource.get('metadata'):
            return  # Not a valid Kubernetes resource
            
        kind = resource['kind'].lower()
        metadata = resource['metadata']
        name = metadata.get('name', 'unknown')
        namespace = metadata.get('namespace', 'default')
        
        # Create unique node ID
        node_id = f"k8s:{kind}:{namespace}/{name}"
        
        # Create node
        node = Node(
            id=node_id,
            type=f"k8s.{kind}",
            name=name,
            namespace=namespace,
            attributes={
                "kind": kind,
                "namespace": namespace,
                "source_file": source_file,
                "spec": resource.get('spec', {}),
                "metadata": metadata
            }
        )
        
        self.graph.add_node(node)
        
        # Add to cache for quick lookup
        self._resource_cache[node_id] = node
        self._resource_cache[f"{namespace}/{name}"] = node  # For selector matching
        
    def _infer_relationships(self):
        """Infer relationships between Kubernetes resources"""
        # Service -> Pod/Deployment via selectors
        self._infer_service_selectors()
        
        # Ingress -> Service via backend rules
        self._infer_ingress_backends()
        
        # Pod -> ConfigMap/Secret via volumes and env
        self._infer_config_references()
    
    def _infer_service_selectors(self):
        """Find Service -> Workload relationships via selectors"""
        services = [node for node in self.graph.nodes if node.type == 'k8s.service']
        
        for service in services:
            spec = service.attributes.get('spec', {})
            selector = spec.get('selector', {})
            
            if selector:
                # Find workloads that match these labels
                matching_workloads = self._find_workloads_by_labels(selector)
                
                for workload in matching_workloads:
                    edge = Edge(
                        from_id=service.id,
                        to_id=workload.id,
                        reason="selector_match"
                    )
                    self.graph.add_edge(edge)
    
    def _find_workloads_by_labels(self, selector_labels: Dict[str, str]) -> List[Node]:
        """Find workloads (Deployment, StatefulSet, Pod) that match selector labels"""
        workloads = []
        workload_types = ['k8s.deployment', 'k8s.statefulset', 'k8s.daemonset', 'k8s.pod']
        
        for node in self.graph.nodes:
            if node.type in workload_types:
                metadata = node.attributes.get('metadata', {})
                labels = metadata.get('labels', {})
                
                # Check if all selector labels match
                if all(labels.get(k) == v for k, v in selector_labels.items()):
                    workloads.append(node)
        
        return workloads
    
    
    def _infer_ingress_backends(self):
        """Find Ingress -> Service relationships"""
        ingresses = [node for node in self.graph.nodes if node.type == 'k8s.ingress']
        
        for ingress in ingresses:
            spec = ingress.attributes.get('spec', {})
            rules = spec.get('rules', [])
            
            for rule in rules:
                http = rule.get('http', {})
                for path in http.get('paths', []):
                    backend = path.get('backend', {})
                    
                    # Handle different API versions
                    if 'service' in backend:
                        # networking.k8s.io/v1 format
                        service_name = backend['service'].get('name')
                        service_namespace = backend['service'].get('namespace', ingress.namespace)
                    else:
                        # Older extensions/v1beta1 format
                        service_name = backend.get('serviceName')
                        service_namespace = ingress.namespace
                    
                    if service_name:
                        service_node = self._find_service(service_name, service_namespace)
                        
                        if service_node:
                            edge = Edge(
                                from_id=ingress.id,
                                to_id=service_node.id,
                                reason="ingress_backend"
                            )
                            self.graph.add_edge(edge)
    
    def _find_service(self, name: str, namespace: str = 'default') -> Optional[Node]:
        """Find a service by name and namespace"""
        service_id = f"k8s:service:{namespace}/{name}"
        return self._resource_cache.get(service_id)
    
    def _infer_config_references(self):
        """Find Pod -> ConfigMap/Secret relationships"""
        pods = [node for node in self.graph.nodes if node.type == 'k8s.pod']
        deployments = [node for node in self.graph.nodes if node.type == 'k8s.deployment']
        
        # Check all pods and deployment templates
        for workload in pods + deployments:
            self._find_config_references_in_workload(workload)
    
    def _find_config_references_in_workload(self, workload: Node):
        """Find ConfigMap/Secret references in a workload"""
        spec = workload.attributes.get('spec', {})
        
        # Check containers for envFrom and env references
        containers = spec.get('template', {}).get('spec', {}).get('containers', []) if workload.type == 'k8s.deployment' else spec.get('containers', [])
        
        for container in containers:
            # Check envFrom (for ConfigMaps and Secrets)
            for env_from in container.get('envFrom', []):
                config_map_ref = env_from.get('configMapRef', {}).get('name')
                secret_ref = env_from.get('secretRef', {}).get('name')
                
                if config_map_ref:
                    self._add_config_reference(workload, config_map_ref, 'configmap', 'envFrom')
                if secret_ref:
                    self._add_config_reference(workload, secret_ref, 'secret', 'envFrom')
            
            # Check env (for valueFrom references)
            for env_var in container.get('env', []):
                value_from = env_var.get('valueFrom', {})
                config_map_ref = value_from.get('configMapKeyRef', {}).get('name')
                secret_ref = value_from.get('secretKeyRef', {}).get('name')
                
                if config_map_ref:
                    self._add_config_reference(workload, config_map_ref, 'configmap', 'env')
                if secret_ref:
                    self._add_config_reference(workload, secret_ref, 'secret', 'env')
            
            # Check volume mounts
            for volume_mount in container.get('volumeMounts', []):
                # This will be handled by volume checking below
                pass
        
        # Check volumes for ConfigMap and Secret references
        volumes = spec.get('template', {}).get('spec', {}).get('volumes', []) if workload.type == 'k8s.deployment' else spec.get('volumes', [])
        
        for volume in volumes:
            config_map_ref = volume.get('configMap', {}).get('name')
            secret_ref = volume.get('secret', {}).get('name')
            
            if config_map_ref:
                self._add_config_reference(workload, config_map_ref, 'configmap', 'volume')
            if secret_ref:
                self._add_config_reference(workload, secret_ref, 'secret', 'volume')
    
    def _add_config_reference(self, workload: Node, config_name: str, config_type: str, reason: str):
        """Add a reference edge from workload to config"""
        # Assume same namespace as workload
        namespace = workload.namespace
        config_id = f"k8s:{config_type}:{namespace}/{config_name}"
        config_node = self._resource_cache.get(config_id)
        
        if config_node:
            edge = Edge(
                from_id=workload.id,
                to_id=config_node.id,
                reason=f"{reason}_{config_type}"
            )
            self.graph.add_edge(edge)