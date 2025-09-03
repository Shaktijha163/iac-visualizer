// frontend/src/components/GraphVisualizer.js
import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  ConnectionLineType,
} from 'react-flow-renderer';
import { Eye, Download, Expand } from 'lucide-react';

const GraphVisualizer = ({ graphData, onError }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const getNodeColor = (nodeType) => {
    if (nodeType.includes('tf.')) return '#ff6b6b';
    if (nodeType.includes('k8s.')) return '#4ecdc4';
    if (nodeType.includes('helm.')) return '#45b7d1';
    return '#95e1d3';
  };

  const getEdgeColor = (reason) => {
    const colors = {
      'depends_on': '#ff9ff3',
      'selector_match': '#feca57',
      'attribute_reference': '#48dbfb',
      'ingress_backend': '#00d2d3',
      'default': '#c8d6e5'
    };
    return colors[reason] || colors.default;
  };
  // -----------------------------------

  // Transform graph data to React Flow format
  useMemo(() => {
    try {
      const newNodes = graphData.nodes.map((node, index) => ({
        id: node.id,
        type: 'custom',
        position: { x: Math.random() * 500, y: Math.random() * 500 },
        data: {
          label: node.name,
          type: node.type,
          attributes: node.attributes,
          namespace: node.namespace,
        },
        style: {
          background: getNodeColor(node.type),
          color: 'white',
          border: '2px solid #333',
          borderRadius: '8px',
          padding: '10px',
        },
      }));

      const newEdges = graphData.edges.map(edge => ({
        id: `${edge.from_id}-${edge.to_id}-${edge.reason}`,
        source: edge.from_id,
        target: edge.to_id,
        label: edge.reason,
        type: 'smoothstep',
        animated: true,
        style: { stroke: getEdgeColor(edge.reason) },
      }));

      setNodes(newNodes);
      setEdges(newEdges);
    } catch (err) {
      onError('Failed to render graph: ' + err.message);
    }
  }, [graphData, setNodes, setEdges, onError]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: 'smoothstep' }, eds)),
    [setEdges]
  );

  if (!graphData || graphData.nodes.length === 0) {
    return <div className="no-data">No graph data to display</div>;
  }

  return (
    <div className="graph-visualizer">
      <div className="graph-header">
        <h3>
          <Eye size={20} />
          Infrastructure Graph
        </h3>
        <div className="graph-stats">
          <span>{graphData.nodes.length} nodes</span>
          <span>{graphData.edges.length} edges</span>
        </div>
        <div className="graph-actions">
          <button className="action-btn">
            <Download size={16} />
            Export
          </button>
          <button className="action-btn">
            <Expand size={16} />
            Fit View
          </button>
        </div>
      </div>

      <div className="react-flow-container">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          connectionLineType={ConnectionLineType.SmoothStep}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>

      <div className="legend">
        <h4>Legend</h4>
        <div className="legend-items">
          <div className="legend-item">
            <span className="color-box" style={{ background: '#ff6b6b' }}></span>
            <span>Terraform Resources</span>
          </div>
          <div className="legend-item">
            <span className="color-box" style={{ background: '#4ecdc4' }}></span>
            <span>Kubernetes Resources</span>
          </div>
          <div className="legend-item">
            <span className="color-box" style={{ background: '#45b7d1' }}></span>
            <span>Helm Resources</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphVisualizer;
