// frontend/src/App.js
import React, { useState } from 'react';
import GraphVisualizer from './components/GraphVisualizer';
import FileUpload from './components/FileUpload';
import Header from './components/Header';
import './App.css';

function App() {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGraphData = (data) => {
    setGraphData(data);
    setError(null);
  };

  const handleError = (errorData) => {
    // Ensure error is always a string to prevent React rendering errors
    if (typeof errorData === 'object' && errorData !== null) {
      setError(JSON.stringify(errorData));
    } else {
      setError(errorData);
    }
  };

  return (
    <div className="App">
      <Header />
      <div className="container">
        <FileUpload 
          onGraphData={handleGraphData}
          onLoading={setLoading}
          onError={handleError}
        />
        
        {loading && <div className="loading">Processing infrastructure code...</div>}
        
        {error && (
          <div className="error">
            <h3>Error</h3>
            <p>{String(error)}</p>
          </div>
        )}

        {graphData && (
          <GraphVisualizer 
            graphData={graphData}
            onError={handleError}
          />
        )}
      </div>
    </div>
  );
}

export default App;