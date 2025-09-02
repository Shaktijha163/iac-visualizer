from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class Node(BaseModel):
    id: str
    type: str
    name: str
    namespace: Optional[str] = None
    group: Optional[str] = None
    attributes: Dict[str, Any] = {}
    
class Edge(BaseModel):
    from_id: str
    to_id: str
    reason: str
    
class ResourceGraph(BaseModel):
    nodes: List[Node] = []
    edges: List[Edge] = []
    meta: Dict[str, Any] = {}
    
    def add_node(self, node: Node):
        self.nodes.append(node)
        
    def add_edge(self, edge: Edge):
        self.edges.append(edge)
