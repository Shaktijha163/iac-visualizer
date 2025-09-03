import React from 'react';
import { Network, Cloud, Server, Package } from 'lucide-react';

const Header = () => {
  return (
    <header className="header">
      <div className="container">
        <h1>
          <Network size={32} style={{ marginRight: '15px', verticalAlign: 'middle' }} />
          IAC Visualizer
        </h1>
        <p>
          Visualize dependencies across <Cloud size={16} style={{ verticalAlign: 'middle', margin: '0 5px' }} /> Terraform, 
          <Server size={16} style={{ verticalAlign: 'middle', margin: '0 5px' }} /> Kubernetes, and 
          <Package size={16} style={{ verticalAlign: 'middle', margin: '0 5px' }} /> Helm configurations
        </p>
      </div>
    </header>
  );
};

export default Header;

