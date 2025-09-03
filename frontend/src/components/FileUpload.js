import React, { useState } from 'react';
import { Upload, FileText, Server, Package } from 'lucide-react';
import axios from 'axios';

const FileUpload = ({ onGraphData, onLoading, onError }) => {
  const [selectedType, setSelectedType] = useState('terraform');
  const [helmChartFile, setHelmChartFile] = useState(null);
  const [helmValuesFile, setHelmValuesFile] = useState(null);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    onLoading(true);
    onError(null);

    try {
      const formData = new FormData();
      let endpoint;

      switch (selectedType) {
        case 'terraform':
          formData.append('file', file);
          endpoint = '/api/parse/terraform';
          break;
        
        case 'kubernetes':
          formData.append('files', file);
          endpoint = '/api/parse/kubernetes';
          break;
        
        case 'helm':
          // For Helm, we need to handle both chart and values files
          if (event.target.id === 'helm-chart-upload') {
            setHelmChartFile(file);
            return; // Don't submit yet, wait for values file
          } else if (event.target.id === 'helm-values-upload') {
            setHelmValuesFile(file);
            
            // If we already have a chart file, submit both
            if (helmChartFile) {
              formData.append('chart', helmChartFile);
              formData.append('values_files', file);
              endpoint = '/api/parse/helm';
            } else {
              return; // Wait for chart file
            }
          }
          break;
        
        default:
          throw new Error('Invalid file type');
      }

      // Only make the API call if we have all required files
      if (endpoint) {
        const response = await axios.post(endpoint, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        onGraphData(response.data);
        
        // Reset Helm files after successful upload
        if (selectedType === 'helm') {
          setHelmChartFile(null);
          setHelmValuesFile(null);
        }
      }
    } catch (err) {
      let errorMessage = 'Failed to process file';
      
      if (err.response?.data) {
        if (typeof err.response.data === 'string') {
          errorMessage = err.response.data;
        } else if (err.response.data.detail) {
          if (typeof err.response.data.detail === 'string') {
            errorMessage = err.response.data.detail;
          } else if (Array.isArray(err.response.data.detail)) {
            errorMessage = err.response.data.detail
              .map(error => `${error.loc?.join('.')}: ${error.msg}`)
              .join('; ');
          } else {
            errorMessage = JSON.stringify(err.response.data.detail);
          }
        } else if (err.response.data.message) {
          errorMessage = err.response.data.message;
        } else {
          errorMessage = `Server error: ${JSON.stringify(err.response.data)}`;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      onError(errorMessage);
    } finally {
      onLoading(false);
    }
  };

  const handleHelmSubmit = async () => {
    if (!helmChartFile) {
      onError('Please select a Helm chart file first');
      return;
    }

    onLoading(true);
    onError(null);

    try {
      const formData = new FormData();
      formData.append('chart', helmChartFile);
      
      if (helmValuesFile) {
        formData.append('values_files', helmValuesFile);
      }

      const response = await axios.post('/api/parse/helm', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      onGraphData(response.data);
      setHelmChartFile(null);
      setHelmValuesFile(null);
    } catch (err) {
      // Error handling as above
    } finally {
      onLoading(false);
    }
  };

  return (
    <div className="file-upload">
      <h2>
        <Upload size={24} />
        Upload Infrastructure Code
      </h2>
      
      <div className="upload-options">
        <label className={`option ${selectedType === 'terraform' ? 'active' : ''}`}>
          <input
            type="radio"
            name="fileType"
            value="terraform"
            checked={selectedType === 'terraform'}
            onChange={(e) => setSelectedType(e.target.value)}
          />
          <FileText size={20} />
          Terraform Plan
        </label>

        <label className={`option ${selectedType === 'kubernetes' ? 'active' : ''}`}>
          <input
            type="radio"
            name="fileType"
            value="kubernetes"
            checked={selectedType === 'kubernetes'}
            onChange={(e) => setSelectedType(e.target.value)}
          />
          <Server size={20} />
          Kubernetes YAML
        </label>

        <label className={`option ${selectedType === 'helm' ? 'active' : ''}`}>
          <input
            type="radio"
            name="fileType"
            value="helm"
            checked={selectedType === 'helm'}
            onChange={(e) => setSelectedType(e.target.value)}
          />
          <Package size={20} />
          Helm Chart
        </label>
      </div>

      <div className="upload-area">
        {selectedType === 'helm' ? (
          <div className="helm-upload">
            <div className="helm-file-input">
              <input
                type="file"
                id="helm-chart-upload"
                onChange={handleFileUpload}
                accept=".tgz,.tar.gz"
                style={{ display: 'none' }}
              />
              <label htmlFor="helm-chart-upload" className="upload-button">
                <Upload size={20} />
                {helmChartFile ? 'Change Chart File' : 'Choose Helm Chart (.tgz)'}
              </label>
              {helmChartFile && (
                <span className="file-name">{helmChartFile.name}</span>
              )}
            </div>

            <div className="helm-file-input">
              <input
                type="file"
                id="helm-values-upload"
                onChange={handleFileUpload}
                accept=".yaml,.yml"
                style={{ display: 'none' }}
              />
              <label htmlFor="helm-values-upload" className="upload-button">
                <Upload size={20} />
                {helmValuesFile ? 'Change Values File' : 'Choose Values File (Optional)'}
              </label>
              {helmValuesFile && (
                <span className="file-name">{helmValuesFile.name}</span>
              )}
            </div>

            {(helmChartFile || helmValuesFile) && (
              <button 
                className="upload-button primary"
                onClick={handleHelmSubmit}
                disabled={!helmChartFile}
              >
                Process Helm Chart
              </button>
            )}

            <div className="file-info">
              Upload a packaged Helm chart (.tgz file) and optionally a values.yaml file
            </div>
          </div>
        ) : (
          <div>
            <input
              type="file"
              id="file-upload"
              onChange={handleFileUpload}
              accept={selectedType === 'terraform' ? '.json' : '.yaml,.yml'}
              style={{ display: 'none' }}
            />
            <label htmlFor="file-upload" className="upload-button">
              <Upload size={20} />
              Choose {selectedType} file
            </label>
            
            <div className="file-info">
              {selectedType === 'terraform' && 'Upload terraform plan JSON file'}
              {selectedType === 'kubernetes' && 'Upload Kubernetes YAML manifest(s)'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;