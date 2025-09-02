# parsers/helm/parser.py
import yaml
import os
import tempfile
import subprocess
import tarfile
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from graph.models import ResourceGraph, Node, Edge


class HelmParser:
    def __init__(self):
        self.graph = ResourceGraph()
        self.graph.meta = {"parser": "helm"}
        self._resource_cache = {}
        self._debug = True  # Enable debug output

    def parse_chart(
        self,
        chart_path: str,
        values_files: List[str] = None,
        namespace: str = "default",
        release_name: str = "test-release"
    ) -> ResourceGraph:
        """Parse a Helm chart and its values to generate a resource graph"""
        if self._debug:
            print(f"DEBUG: Starting Helm parsing for {chart_path}")
            print(f"DEBUG: Values files: {values_files}")
            print(f"DEBUG: Namespace: {namespace}, Release: {release_name}")
        
        # Reset state
        self.graph = ResourceGraph()
        self.graph.meta = {
            "parser": "helm",
            "chart_path": chart_path,
            "values_files": values_files or [],
            "namespace": namespace,
            "release_name": release_name,
        }
        self._resource_cache = {}

        try:
            # Render Helm chart
            rendered_manifests = self._render_helm_chart(chart_path, values_files, namespace, release_name)
            
            if not rendered_manifests:
                print("ERROR: No manifests rendered from Helm chart")
                return self.graph
            
            if self._debug:
                print(f"DEBUG: Rendered manifests length: {len(rendered_manifests)} chars")
                print(f"DEBUG: First 500 chars of rendered manifests:\n{rendered_manifests[:500]}...")

            # Parse the rendered manifests
            self._parse_rendered_manifests(rendered_manifests, chart_path)
            
            # Extract Helm metadata
            self._extract_helm_metadata(chart_path)
            
            if self._debug:
                print(f"DEBUG: Final graph - Nodes: {len(self.graph.nodes)}, Edges: {len(self.graph.edges)}")
                
        except Exception as e:
            print(f"ERROR: Failed to parse Helm chart: {e}")
            import traceback
            traceback.print_exc()

        return self.graph

    def _render_helm_chart(
        self, chart_path: str, values_files: List[str], namespace: str, release_name: str
    ) -> Optional[str]:
        """Render Helm templates to YAML using helm template"""
        try:
            # Check if helm command is available
            result = subprocess.run(["helm", "version", "--short"], capture_output=True, text=True)
            if result.returncode != 0:
                print("ERROR: Helm CLI not found or not working")
                return None
            
            if self._debug:
                print(f"DEBUG: Helm version: {result.stdout.strip()}")

            cmd = ["helm", "template", release_name, chart_path, "--namespace", namespace]

            # Add values files if provided
            if values_files:
                for values_file in values_files:
                    if os.path.exists(values_file):
                        cmd.extend(["-f", values_file])
                    else:
                        print(f"WARNING: Values file {values_file} not found")

            if self._debug:
                print(f"DEBUG: Running command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"ERROR: Helm template failed (exit code {result.returncode}):")
                print(f"STDERR: {result.stderr}")
                print(f"STDOUT: {result.stdout}")
                return None

            if not result.stdout.strip():
                print("WARNING: Helm template produced empty output")
                return None

            if self._debug:
                print(f"DEBUG: Helm template succeeded, output length: {len(result.stdout)}")

            return result.stdout

        except FileNotFoundError:
            print("ERROR: Helm CLI not found. Please install Helm.")
            return None
        except Exception as e:
            print(f"ERROR: Exception in _render_helm_chart: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_rendered_manifests(self, manifests_yaml: str, chart_path: str):
        """Parse the rendered YAML manifests using KubernetesParser"""
        temp_path = None
        try:
            if self._debug:
                print("DEBUG: Starting to parse rendered manifests")
            
            # Try to import KubernetesParser
            try:
                from parsers.kubernetes.parser import KubernetesParser
                if self._debug:
                    print("DEBUG: Successfully imported KubernetesParser")
            except ImportError as e:
                print(f"ERROR: Could not import KubernetesParser: {e}")
                # Try alternative parsing approach
                self._parse_manifests_directly(manifests_yaml, chart_path)
                return

            # Write rendered manifests to a temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
                temp_file.write(manifests_yaml)
                temp_path = temp_file.name
            
            if self._debug:
                print(f"DEBUG: Wrote manifests to temp file: {temp_path}")

            # Parse with Kubernetes parser
            k8s_parser = KubernetesParser()
            
            # Check if the parser has parse_files method
            if hasattr(k8s_parser, 'parse_files'):
                k8s_graph = k8s_parser.parse_files([temp_path])
            else:
                print("ERROR: KubernetesParser doesn't have expected parse methods")
                return

            if self._debug:
                print(f"DEBUG: K8s parser returned - Nodes: {len(k8s_graph.nodes) if k8s_graph else 0}, Edges: {len(k8s_graph.edges) if k8s_graph else 0}")

            # Merge results into Helm graph
            if k8s_graph:
                for node in k8s_graph.nodes:
                    # Add Helm-specific metadata
                    node.attributes = node.attributes or {}
                    node.attributes["helm_chart"] = chart_path
                    node.attributes["source"] = "helm"
                    self.graph.add_node(node)

                for edge in k8s_graph.edges:
                    self.graph.add_edge(edge)
                    
                if self._debug:
                    print(f"DEBUG: Merged K8s graph into Helm graph")

        except Exception as e:
            print(f"ERROR: Exception in _parse_rendered_manifests: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
                if self._debug:
                    print(f"DEBUG: Cleaned up temp file: {temp_path}")

    def _parse_manifests_directly(self, manifests_yaml: str, chart_path: str):
        """Fallback: Parse YAML manifests directly without KubernetesParser"""
        try:
            if self._debug:
                print("DEBUG: Using direct YAML parsing fallback")
            
            # Split manifests by ---
            documents = []
            for doc in manifests_yaml.split('---'):
                doc = doc.strip()
                if doc and not doc.startswith('#'):
                    try:
                        parsed_doc = yaml.safe_load(doc)
                        if parsed_doc and isinstance(parsed_doc, dict):
                            documents.append(parsed_doc)
                    except yaml.YAMLError as e:
                        if self._debug:
                            print(f"DEBUG: Skipping invalid YAML document: {e}")
                        continue

            if self._debug:
                print(f"DEBUG: Parsed {len(documents)} YAML documents")

            # Create nodes from documents
            for i, doc in enumerate(documents):
                try:
                    kind = doc.get('kind', 'Unknown')
                    metadata = doc.get('metadata', {})
                    name = metadata.get('name', f'unnamed-{i}')
                    namespace = metadata.get('namespace', 'default')
                    
                    node_id = f"helm:{kind.lower()}:{namespace}:{name}"
                    
                    node = Node(
                        id=node_id,
                        type=f"k8s.{kind}",
                        name=name,
                        namespace=namespace,
                        attributes={
                            "helm_chart": chart_path,
                            "source": "helm",
                            "kind": kind,
                            "api_version": doc.get('apiVersion', ''),
                            "raw_manifest": doc
                        }
                    )
                    
                    self.graph.add_node(node)
                    
                except Exception as e:
                    if self._debug:
                        print(f"DEBUG: Error processing document {i}: {e}")
                    continue

        except Exception as e:
            print(f"ERROR: Direct manifest parsing failed: {e}")
            import traceback
            traceback.print_exc()

    def _extract_helm_metadata(self, chart_path: str):
        """Extract metadata from Chart.yaml (works for .tgz and unpacked dirs)"""
        chart_yaml_path = None
        temp_dir = None

        try:
            if self._debug:
                print(f"DEBUG: Extracting metadata from {chart_path}")
            
            if chart_path.endswith((".tgz", ".tar.gz")):
                temp_dir = tempfile.mkdtemp()
                with tarfile.open(chart_path, "r:gz") as tar:
                    tar.extractall(temp_dir)
                # Assume first directory is chart root
                subdirs = [p for p in Path(temp_dir).iterdir() if p.is_dir()]
                if subdirs:
                    chart_yaml_path = subdirs[0] / "Chart.yaml"
                    if self._debug:
                        print(f"DEBUG: Found chart directory: {subdirs[0]}")
            else:
                chart_yaml_path = Path(chart_path) / "Chart.yaml"

            if chart_yaml_path and chart_yaml_path.exists():
                if self._debug:
                    print(f"DEBUG: Reading Chart.yaml from {chart_yaml_path}")
                
                with open(chart_yaml_path, "r") as f:
                    chart_data = yaml.safe_load(f)

                self.graph.meta["chart_metadata"] = {
                    "name": chart_data.get("name", ""),
                    "version": chart_data.get("version", ""),
                    "description": chart_data.get("description", ""),
                    "dependencies": chart_data.get("dependencies", []),
                }

                # Add dependency nodes
                for dep in chart_data.get("dependencies", []):
                    dep_node_id = f"helm:dependency:{dep.get('name', 'unknown')}"
                    dep_node = Node(
                        id=dep_node_id,
                        type="helm.dependency",
                        name=dep.get("name", "unknown"),
                        attributes={
                            "version": dep.get("version", ""),
                            "repository": dep.get("repository", ""),
                            "condition": dep.get("condition", ""),
                            "chart": chart_data.get("name", ""),
                        },
                    )
                    self.graph.add_node(dep_node)
                    
                if self._debug:
                    print(f"DEBUG: Added chart metadata and {len(chart_data.get('dependencies', []))} dependency nodes")
            else:
                if self._debug:
                    print(f"DEBUG: Chart.yaml not found at {chart_yaml_path}")

        except Exception as e:
            print(f"ERROR: Error parsing Chart.yaml: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def parse_values(self, values_path: str) -> Dict[str, Any]:
        """Parse a Helm values.yaml file"""
        try:
            with open(values_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error parsing values file {values_path}: {e}")
            return {}