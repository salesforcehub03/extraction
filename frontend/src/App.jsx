import React, { useState } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api';

function App() {
  const [activeTab, setActiveTab] = useState('extraction');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [downloadLink, setDownloadLink] = useState(null);

  // EXTRACTION STATE
  const [ibPdf, setIbPdf] = useState(null);
  const [clinicalFiles, setClinicalFiles] = useState([]);
  const [preclinicalFiles, setPreclinicalFiles] = useState([]);
  const [extraFiles, setExtraFiles] = useState([]);

  // HARMONIZATION STATE
  const [ibExcel, setIbExcel] = useState(null); // The output from extraction
  const [otherExcels, setOtherExcels] = useState([]);

  const handleFileChange = (e, setter, multiple = false) => {
    if (multiple) {
      setter(Array.from(e.target.files));
    } else {
      setter(e.target.files[0]);
    }
  };

  const handleExtraction = async () => {
    if (!ibPdf) {
      alert("Please upload the IB PDF.");
      return;
    }

    setIsLoading(true);
    setMessage("Running Data Extraction Pipeline... This may take a few minutes.");
    setDownloadLink(null);

    const formData = new FormData();
    formData.append('ib_pdf', ibPdf);
    clinicalFiles.forEach(f => formData.append('clinical_files', f));
    preclinicalFiles.forEach(f => formData.append('preclinical_files', f));
    extraFiles.forEach(f => formData.append('extra_files', f));

    try {
      const response = await fetch(`${API_BASE_URL}/extract`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Extraction failed');

      const data = await response.json();
      setDownloadLink(`${API_BASE_URL}${data.download_url}`);
      setMessage("Extraction Complete! Download your files below.");
    } catch (error) {
      console.error(error);
      setMessage(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleHarmonization = async () => {
    if (!ibExcel) {
      alert("Please upload the Consolidated/IB Excel file.");
      return;
    }

    setIsLoading(true);
    setMessage("Building Knowledge Graph...");
    setDownloadLink(null);

    const formData = new FormData();
    formData.append('ib_excel', ibExcel);
    otherExcels.forEach(f => formData.append('other_files', f));

    try {
      const response = await fetch(`${API_BASE_URL}/harmonize`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Harmonization failed');

      const data = await response.json();
      setDownloadLink(`${API_BASE_URL}${data.download_url}`);
      setMessage("Knowledge Graph Built! Download JSON below.");
    } catch (error) {
      console.error(error);
      setMessage(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>AViiD Data Pipeline</h1>
      </header>

      <div className="tabs">
        <button
          className={activeTab === 'extraction' ? 'active' : ''}
          onClick={() => { setActiveTab('extraction'); setMessage(''); setDownloadLink(null); }}
        >
          1. Data Extraction
        </button>
        <button
          className={activeTab === 'harmonization' ? 'active' : ''}
          onClick={() => { setActiveTab('harmonization'); setMessage(''); setDownloadLink(null); }}
        >
          2. Data Harmonization
        </button>
      </div>

      <div className="content">
        {activeTab === 'extraction' && (
          <div className="tab-pane">
            <h2>Extraction Input</h2>
            <div className="form-group">
              <label>Investigator Brochure (PDF) *</label>
              <input type="file" accept=".pdf" onChange={(e) => handleFileChange(e, setIbPdf)} />
            </div>

            <div className="form-group">
              <label>Clinical Data (CSV/Excel)</label>
              <input type="file" multiple accept=".csv,.xlsx" onChange={(e) => handleFileChange(e, setClinicalFiles, true)} />
            </div>

            <div className="form-group">
              <label>Pre-clinical Data (CSV/Excel)</label>
              <input type="file" multiple accept=".csv,.xlsx" onChange={(e) => handleFileChange(e, setPreclinicalFiles, true)} />
            </div>

            <div className="form-group">
              <label>Extra Data (CSV/Excel)</label>
              <input type="file" multiple accept=".csv,.xlsx" onChange={(e) => handleFileChange(e, setExtraFiles, true)} />
            </div>

            <button className="primary-btn" onClick={handleExtraction} disabled={isLoading}>
              {isLoading ? 'Processing...' : 'Run Extraction'}
            </button>
          </div>
        )}

        {activeTab === 'harmonization' && (
          <div className="tab-pane">
            <h2>Harmonization Input</h2>
            <div className="info-box">
              <p>Upload the <strong>Excel file</strong> you downloaded from Step 1.</p>
            </div>

            <div className="form-group">
              <label>IB / Consolidated Excel *</label>
              <input type="file" accept=".xlsx" onChange={(e) => handleFileChange(e, setIbExcel)} />
            </div>

            <div className="form-group">
              <label>Additional Excels (Clinical/Pre-clinical)</label>
              <input type="file" multiple accept=".xlsx,.csv" onChange={(e) => handleFileChange(e, setOtherExcels, true)} />
            </div>

            <button className="primary-btn" onClick={handleHarmonization} disabled={isLoading}>
              {isLoading ? 'Processing...' : 'Build Knowledge Graph'}
            </button>
          </div>
        )}

        {/* Status Area */}
        <div className="status-area">
          {isLoading && <div className="spinner"></div>}
          {message && <p className="status-msg">{message}</p>}

          {downloadLink && (
            <a href={downloadLink} className="download-btn" target="_blank" rel="noopener noreferrer">
              Download Result
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
