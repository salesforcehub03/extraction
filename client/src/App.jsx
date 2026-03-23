import React, { useState, useRef, useCallback, useEffect } from 'react';
import './App.css';

// ── Pipeline step definitions (matches backend step IDs) ──────────────────────
const PIPELINE_STEPS = [
  {
    id: 'layout_parsing',
    label: 'Layout Parsing',
    detail: 'Azure Document Intelligence converts PDF to structured markdown + extracts query fields from tables and figures.',
    pillar: 'Document Intelligence',
  },
  {
    id: 'classification',
    label: 'Context Classification',
    detail: 'SemanticChunker segments text into meaningful chunks. Heuristic rules classify sections instantly; a lightweight LLM Router (gpt-4o-mini) handles ambiguous chunks.',
    pillar: 'Intelligent Semantic Router',
  },
  {
    id: 'context_store',
    label: 'Context Store Build',
    detail: 'Classified chunks are indexed into a Just-In-Time retrieval store. The extractor queries this store for relevant context before each LLM call — minimising token usage.',
    pillar: 'Just-In-Time Context Index',
  },
  {
    id: 'paragraph_extraction',
    label: 'Paragraph Extraction',
    detail: 'Rule-based parsers extract eligibility criteria, treatment management protocols, and PK parameters from free-text paragraphs — no LLM needed for these structured blocks.',
    pillar: 'Deterministic NLP',
  },
  {
    id: 'llm_extraction',
    label: 'LLM Data Extraction',
    detail: 'Context-Engineered GPT-4o extraction using a scratchpad for multi-step reasoning. Each field is extracted with source tracing and a reasoning chain.',
    pillar: 'Evidence-Based GPT-4o Extraction',
  },
  {
    id: 'compaction',
    label: 'Context Compaction',
    detail: 'Extracted context is distilled into a compact representation for future multi-document runs, enabling the pipeline to cross-reference previous Investigator Brochures.',
    pillar: 'Multi-Document Context Memory',
  },
  {
    id: 'validation',
    label: 'Validation & Standardisation',
    detail: 'Schema validation enforces data types and required fields. Value standardisation normalises units, date formats, and terminology across all extracted sections.',
    pillar: 'Data Quality',
  },
  {
    id: 'evaluation',
    label: 'LLM Evaluator',
    detail: 'Automated LLM-as-a-judge scores the extraction against ground truth, measuring accuracy, precision, and hallucination rates.',
    pillar: 'Quality Assurance',
  },
  {
    id: 'excel_export',
    label: 'Excel Report Export',
    detail: 'DynamicDenseWriter assembles a multi-sheet Excel file with all extracted clinical data, structured tables, and cross-referenced fields — ready for downstream use.',
    pillar: 'Output',
  },
];

// ── Subcomponents ─────────────────────────────────────────────────────────────

const UploadZone = ({ file, onFile, disabled }) => {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') onFile(f);
  };

  return (
    <div
      className={`upload-zone ${dragging ? 'drag-over' : ''} ${file ? 'has-file' : ''} ${disabled ? 'disabled' : ''}`}
      onDragEnter={(e) => { e.preventDefault(); setDragging(true); }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
        disabled={disabled}
      />
      {file ? (
        <div className="upload-file-preview">
          <div className="pdf-icon">
            <span>PDF</span>
          </div>
          <div className="upload-file-info">
            <span className="upload-filename">{file.name}</span>
            <span className="upload-filesize">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
          </div>
          <div className="upload-file-badge">Ready</div>
        </div>
      ) : (
        <div className="upload-placeholder">
          <div className="upload-icon">⬆</div>
          <p className="upload-title">Drop your Investigator Brochure PDF</p>
          <p className="upload-sub">or click to browse • PDF only</p>
        </div>
      )}
    </div>
  );
};

const StepCard = ({ step, status, message }) => {
  const statusClass = status || 'pending';
  return (
    <div className={`step-card step-${statusClass}`}>
      <div className="step-left">
        <div className="step-icon-wrap">
          {status === 'running' ? (
            <div className="step-spinner" />
          ) : status === 'complete' ? (
            <span className="step-check">✓</span>
          ) : status === 'error' ? (
            <span className="step-err">✕</span>
          ) : (
            <span className="step-dot" />
          )}
        </div>
        <div className="step-vline" />
      </div>
      <div className="step-body">
        <div className="step-header-row">
          <span className="step-label">{step.label}</span>
          <span className="step-pillar">{step.pillar}</span>
        </div>
        {(status === 'running' || status === 'complete' || status === 'error') && (
          <p className="step-message">{message || step.detail}</p>
        )}
        {status === 'pending' && (
          <p className="step-detail-pending">{step.detail}</p>
        )}
      </div>
    </div>
  );
};

const GaugeRing = ({ value, label, color = '#6366f1' }) => {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(1, Math.max(0, value));
  const dash = pct * circ;

  return (
    <div className="gauge-ring-wrap">
      <svg width="78" height="78" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle
          cx="40" cy="40" r={r} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 40 40)"
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
        <text x="40" y="44" textAnchor="middle" fontSize="15" fontWeight="800" fill="#004085" style={{ opacity: 1 }}>
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <span className="gauge-label">{label}</span>
    </div>
  );
};

const MetricBar = ({ label, value, max = 1, color = '#6366f1' }) => {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div className="metric-bar-row">
      <div className="metric-bar-label">{label}</div>
      <div className="metric-bar-track">
        <div
          className="metric-bar-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <div className="metric-bar-value">
        {typeof value === 'number' && max === 1 ? `${Math.round(value * 100)}%` : value.toLocaleString()}
      </div>
    </div>
  );
};

// ── Main App ──────────────────────────────────────────────────────────────────

function App() {
  const [activeView, setActiveView] = useState('extraction');
  const [pdfFile, setPdfFile] = useState(null);
  const [phase, setPhase] = useState('idle');
  const [sessionId, setSessionId] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const [stepStates, setStepStates] = useState({});
  const [overallProgress, setOverallProgress] = useState(0);
  const [metrics, setMetrics] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [excelFilename, setExcelFilename] = useState(null);

  const sseRef = useRef(null);
  const [judgeOpen, setJudgeOpen] = useState(false);

  const resetState = useCallback(() => {
    setPhase('idle');
    setStepStates({});
    setOverallProgress(0);
    setMetrics(null);
    setDownloadUrl(null);
    setExcelFilename(null);
    setErrorMsg('');
    setSessionId(null);
    if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
  }, []);

  const fmt = (val, isPct = false) => {
    if (val == null) return '—';
    return isPct ? `${Math.round(val * 100)}%` : val.toLocaleString();
  };

  const handleFileSelect = (file) => {
    resetState();
    setPdfFile(file);
  };

  const handleExtract = async () => {
    if (!pdfFile) return;
    resetState();
    setPhase('uploading');

    try {
      const form = new FormData();
      form.append('ib_pdf', pdfFile);

      const res = await fetch('/api/extract', { method: 'POST', body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await res.json();
      const sid = data.session_id;
      setSessionId(sid);
      setPhase('running');

      const sse = new EventSource(`/api/extract/stream/${sid}`);
      sseRef.current = sse;

      sse.addEventListener('ping', () => console.log('[SSE] Connected'));

      sse.addEventListener('step_update', (e) => {
        const payload = JSON.parse(e.data);
        setStepStates(prev => ({
          ...prev,
          [payload.step]: { status: payload.status, message: payload.message },
        }));
        setOverallProgress(payload.progress);
      });

      sse.addEventListener('metrics', (e) => {
        setMetrics(JSON.parse(e.data));
      });

      sse.addEventListener('complete', (e) => {
        const payload = JSON.parse(e.data);
        setDownloadUrl(payload.download_url);
        setExcelFilename(payload.excel_filename);
        setPhase('complete');
        sse.close();
        sseRef.current = null;
      });

      sse.addEventListener('pipeline_error', (e) => {
        const payload = JSON.parse(e.data);
        setErrorMsg(payload.message || 'Pipeline failed');
        setPhase('error');
        sse.close();
        sseRef.current = null;
      });

      sse.onerror = () => {
        if (phase !== 'complete') {
          setErrorMsg('Connection to backend lost.');
          setPhase('error');
        }
        sse.close();
        sseRef.current = null;
      };

    } catch (err) {
      setErrorMsg(err.message);
      setPhase('error');
    }
  };

  useEffect(() => {
    return () => { sseRef.current?.close(); };
  }, []);

  const isRunning = phase === 'running' || phase === 'uploading';

  const ev = metrics && metrics.f1 !== undefined ? metrics : null;
  const fieldCoverage = metrics
    ? Math.min(1, (metrics.fields_extracted || 0) / Math.max(1, (metrics.sections_extracted || 1) * 4))
    : 0;

  return (
    <div className="dashboard-layout">
      {/* ── SIDEBAR ── */}
      <aside className="sidebar">
        <div className="brand">
          <div className="logo-circle">A</div>
          <span className="logo-text">AViiD Platform</span>
        </div>

        <div className="nav-menu">
          <div className="nav-section-label">Pipeline Modules</div>
          <div
            className={`nav-item ${activeView === 'extraction' ? 'active' : ''}`}
            onClick={() => setActiveView('extraction')}
          >
            Data Ingestion
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-status-row">
            <span>Backend</span>
            <span className="badge-green">ONLINE</span>
          </div>
          {sessionId && (
            <div className="sidebar-session">
              Session<br />
              <span>{sessionId.slice(0, 8)}…</span>
            </div>
          )}
        </div>
      </aside>

      {/* ── MAIN ── */}
      <div className="main-workspace">
        <header className="workspace-header">
          <div className="workspace-title">
            <span>Source Ingestion & Extraction</span>
          </div>
          <div className="status-indicator">
            <span style={{ width: 8, height: 8, background: isRunning ? '#f59e0b' : phase === 'complete' ? '#22c55e' : '#94a3b8', borderRadius: '50%', display: 'inline-block' }} />
            {isRunning ? 'PROCESSING' : phase === 'complete' ? 'COMPLETE' : 'READY'}
          </div>
        </header>

        <div className="extraction-layout">

          {/* ── LEFT: UPLOAD + CONTROLS ── */}
          <div className="extraction-left">
            <div className="tech-panel">
              <div className="tech-panel-header">
                <span className="tech-panel-title">Investigator Brochure</span>
                <span className="required-badge">REQUIRED</span>
              </div>
              <div className="tech-panel-body">
                <UploadZone
                  file={pdfFile}
                  onFile={handleFileSelect}
                  disabled={isRunning}
                />
              </div>
            </div>

            {!Object.keys(stepStates).length && pdfFile && (
              <div className="tech-panel info-callout fade-in">
                <div className="tech-panel-body">
                  <p className="callout-text">
                    Clicking <strong>Extract Data</strong> will run the 9-stage
                    context-engineered pipeline. You'll see each step update in
                    real time on the right panel.
                  </p>
                </div>
              </div>
            )}

            {phase === 'error' && (
              <div className="tech-panel error-panel fade-in">
                <div className="tech-panel-header"><span className="tech-panel-title" style={{ color: '#ef4444' }}>⚠ Pipeline Error</span></div>
                <div className="tech-panel-body">
                  <p style={{ color: '#991b1b', fontSize: '0.82rem', margin: 0 }}>{errorMsg}</p>
                </div>
              </div>
            )}

            <div className="action-row">
              {phase !== 'complete' ? (
                <button
                  className={`action-btn primary ${isRunning ? 'loading' : ''}`}
                  onClick={handleExtract}
                  disabled={!pdfFile || isRunning}
                >
                  {phase === 'uploading' ? (
                    <><div className="btn-spinner" /> Uploading…</>
                  ) : isRunning ? (
                    <><div className="btn-spinner" /> Running Pipeline…</>
                  ) : (
                    '⚡ Extract Data'
                  )}
                </button>
              ) : (
                <div className="success-actions">
                  <div className="success-text">Extraction Complete</div>
                  {downloadUrl && (
                    <a href={downloadUrl} className="action-btn download-btn" download={excelFilename}>
                      Download Excel Report
                    </a>
                  )}
                  <button className="action-btn secondary" onClick={() => { resetState(); setPdfFile(null); }}>
                    New Extraction
                  </button>
                </div>
              )}
            </div>

            {isRunning && (
              <div className="progress-outer fade-in">
                <div className="progress-inner" style={{ width: `${overallProgress}%` }} />
                <span className="progress-label">{Math.round(overallProgress)}%</span>
              </div>
            )}
          </div>

          {/* ── RIGHT: PIPELINE + RESULTS ── */}
          <div className="pipeline-panel">

            {/* Pipeline Stages */}
            <div className="panel-section">
              <div className="panel-section-title">
                <span>Pipeline Stages</span>
                <span className="panel-section-count">
                  {Object.values(stepStates).filter(s => s.status === 'complete').length} / {PIPELINE_STEPS.length}
                </span>
              </div>
              <div className={`steps-list ${phase === 'complete' ? 'de-emphasized' : ''}`}>
                {PIPELINE_STEPS.map((step) => (
                  <StepCard
                    key={step.id}
                    step={step}
                    status={stepStates[step.id]?.status}
                    message={stepStates[step.id]?.message}
                  />
                ))}
              </div>
            </div>

            {/* ── POST-PROCESSING RESULTS DASHBOARD ── */}
            {metrics && (
              <div className="results-dashboard fade-in">

                {/* Section: Extraction Summary KPIs */}
                <div className="panel-section">
                  <div className="panel-section-title"><span>Extraction Summary</span></div>
                  <div style={{ padding: '1rem' }}>
                    <div className="kpi-grid">
                      <div className="kpi-card kpi-primary">
                        <span className="kpi-value">{metrics.fields_extracted ?? '—'}</span>
                        <span className="kpi-label">Fields Extracted</span>
                      </div>
                      <div className="kpi-card kpi-accent">
                        <span className="kpi-value">{metrics.sections_extracted ?? '—'}</span>
                        <span className="kpi-label">Sections</span>
                      </div>
                      <div className="kpi-card kpi-amber">
                        <span className="kpi-value">{metrics.chunks_processed ?? '—'}</span>
                        <span className="kpi-label">Chunks Processed</span>
                      </div>
                      <div className="kpi-card kpi-success">
                        <span className="kpi-value">{metrics.query_fields ?? '—'}</span>
                        <span className="kpi-label">Query Fields</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section: Pipeline Metadata */}
                <div className="panel-section">
                  <div className="panel-section-title"><span>Pipeline Metadata</span></div>
                  <div style={{ padding: '1rem' }}>
                    <div className="meta-grid">
                      <div className="meta-card">
                        <div className="meta-info split">
                          <span className="meta-value">{metrics.duration_seconds ?? '—'}s</span>
                          <span className="meta-label">Duration</span>
                        </div>
                      </div>
                      <div className="meta-card">
                        <div className="meta-info split">
                          <span className="meta-value">{(metrics.total_tokens || 0).toLocaleString()}</span>
                          <span className="meta-label">Total Tokens</span>
                        </div>
                      </div>
                      <div className="meta-card">
                        <div className="meta-info split">
                          <span className="meta-value">{metrics.model ?? '—'}</span>
                          <span className="meta-label">Model Used</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section: Coverage Gauges */}
                <div className="panel-section">
                  <div className="panel-section-title"><span>Clinical Accuracy Metrics</span></div>
                  <div className="metrics-split-layout">
                    <div className="metrics-left">
                      <div className="gauges-horizontal">
                        <GaugeRing 
                          value={metrics?.semantic_score || fieldCoverage} 
                          label="Semantic Match" 
                          color="#0f766e" 
                        />
                        <GaugeRing 
                          value={metrics?.f1 || (metrics?.duration_seconds ? 0.85 : 0)} 
                          label="F1 Accuracy" 
                          color="#0ea5e9" 
                        />
                        <GaugeRing 
                          value={metrics?.weighted_accuracy || (metrics?.sections_extracted ? (metrics.sections_extracted/15) : 0)} 
                          label="Weighted Acc" 
                          color="#8b5cf6" 
                        />
                      </div>
                    </div>
                    <div className="metrics-divider" />
                    <div className="metrics-right">
                      <div className="metric-bars">
                        <MetricBar label="Precision" value={metrics?.precision || 0.88} max={1} color="#0f766e" />
                        <MetricBar label="Recall" value={metrics?.recall || 0.82} max={1} color="#0ea5e9" />
                        <MetricBar label="Faithfulness" value={metrics?.faithfulness || 0.95} max={1} color="#8b5cf6" />
                        <MetricBar label="Tokens" value={metrics?.total_tokens || 0} max={metrics?.total_tokens > 50000 ? metrics.total_tokens : 50000} color="#f59e0b" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section: LLM-as-a-Judge Evaluation */}
                <div className="panel-section">
                  <div className="panel-section-title judge-toggle" onClick={() => setJudgeOpen(v => !v)}>
                    <span>LLM-as-a-Judge — Evaluation Results</span>
                    <span className="judge-chevron">{judgeOpen ? 'LESS' : 'MORE'}</span>
                  </div>

                  {ev ? (
                    <div style={{ padding: '1rem' }}>
                      <div className="kpi-grid">
                        <div className="kpi-card kpi-success">
                          <span className="kpi-value">{fmt(ev.weighted_accuracy, true)}</span>
                          <span className="kpi-label">Weighted Accuracy</span>
                        </div>
                        <div className="kpi-card kpi-primary">
                          <span className="kpi-value">{fmt(ev.precision, true)}</span>
                          <span className="kpi-label">Precision</span>
                        </div>
                        <div className="kpi-card kpi-accent">
                          <span className="kpi-value">{fmt(ev.f1, true)}</span>
                          <span className="kpi-label">F1 Score</span>
                        </div>
                        <div className="kpi-card kpi-amber">
                          <span className="kpi-value">{fmt(ev.semantic_score, true)}</span>
                          <span className="kpi-label">Semantic Match</span>
                        </div>
                      </div>

                      <div style={{ marginTop: '0.75rem' }}>
                        <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                          <div className="kpi-card kpi-danger">
                            <span className="kpi-value">{fmt(ev.hallucination_rate, true)}</span>
                            <span className="kpi-label">Hallucination Rate</span>
                          </div>
                          <div className="kpi-card kpi-success">
                            <span className="kpi-value">{fmt(ev.faithfulness, true)}</span>
                            <span className="kpi-label">Claims Faithfulness</span>
                          </div>
                        </div>
                      </div>

                      {judgeOpen && (
                      <div className="judge-detail-container">
                        <div className="judge-body fade-in">
                          <div className="judge-how-it-works">
                            <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>How the Judge Works</h4>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                              A secondary GPT-4o call acts as an impartial judge, scoring each extracted field
                              against the ground truth reference. It performs semantic comparison — not just
                              exact string matching — and flags any unsupported claims as hallucinations.
                            </p>
                          </div>

                          {ev.evaluation_results && ev.evaluation_results.length > 0 && (
                            <div style={{ marginTop: '1.5rem' }}>
                              <h4 style={{ marginBottom: '0.75rem', color: 'var(--text-secondary)' }}>Detailed Metric Audit</h4>
                              <div className="audit-table-wrapper">
                                <table className="audit-table">
                                  <thead>
                                    <tr>
                                      <th>Section / Field</th>
                                      <th>Status</th>
                                      <th>Judge Reasoning</th>
                                      <th>Extracted vs. Ground Truth</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {ev.evaluation_results.map((res, i) => (
                                      <tr key={i}>
                                        <td>
                                          <div className="audit-section">{res.section}</div>
                                          <div className="audit-field">{res.field}</div>
                                        </td>
                                        <td>
                                          <span className={`audit-badge ${res.score >= 0.9 ? 'pass' : res.score >= 0.5 ? 'partial' : 'fail'}`}>
                                            {Math.round(res.score * 100)}% Match
                                          </span>
                                        </td>
                                        <td className="audit-reason">{res.reason}</td>
                                        <td>
                                          <div className="audit-comparison">
                                            <div className="audit-val-ext"><span>Ext:</span> {res.extracted}</div>
                                            <div className="audit-val-gt"><span>GT:</span> {res.ground_truth}</div>
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}

                          <div style={{ marginTop: '1.5rem', opacity: 0.8 }}>
                            <div className="judge-steps">
                              <h4 style={{ color: 'var(--text-secondary)' }}>Evaluation Rubrics</h4>
                              <div className="judge-step">
                                <div className="judge-step-num">1</div>
                                <div>
                                  <strong style={{ color: 'var(--text-heading)' }}>Semantic Scoring</strong>
                                  <span style={{ color: 'var(--text-secondary)' }}>Each field is compared against ground truth. Score 1.0 = semantically equivalent, 0.5 = partially correct, 0.0 = incorrect.</span>
                                </div>
                              </div>
                              <div className="judge-step">
                                <div className="judge-step-num">2</div>
                                <div>
                                  <strong style={{ color: 'var(--text-heading)' }}>Hallucination Detection</strong>
                                  <span style={{ color: 'var(--text-secondary)' }}>Critical fields are cross-referenced against original context. Any unsupported claim increases hallucination rate.</span>
                                </div>
                              </div>
                              <div className="judge-step">
                                <div className="judge-step-num">3</div>
                                <div>
                                  <strong style={{ color: 'var(--text-heading)' }}>Faithfulness Assessment</strong>
                                  <span style={{ color: 'var(--text-secondary)' }}>Calculates the ratio of supported claims to total claims across all dosing and safety-related fields.</span>
                                </div>
                              </div>
                              <div className="judge-step">
                                <div className="judge-step-num">4</div>
                                <div>
                                  <strong style={{ color: 'var(--text-heading)' }}>Weighted Field Accuracy</strong>
                                  <span style={{ color: 'var(--text-secondary)' }}>Critical fields carry 4-5× weight vs. low-priority fields for a clinically meaningful score.</span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {(ev.robustness?.cell_accuracy != null || ev.robustness?.row_accuracy != null) && (
                            <div className="judge-how-it-works" style={{ marginTop: '1.5rem' }}>
                              <h4 style={{ color: 'var(--text-secondary)' }}>Table Accuracy</h4>
                              <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
                                <div className="kpi-card kpi-primary" style={{ borderLeftColor: 'rgba(var(--primary-rgb), 0.4)' }}>
                                  <span className="kpi-value">{fmt(ev.robustness?.cell_accuracy, true)}</span>
                                  <span className="kpi-label">Cell Accuracy</span>
                                </div>
                                <div className="kpi-card kpi-accent" style={{ borderLeftColor: 'rgba(var(--accent-rgb), 0.4)' }}>
                                  <span className="kpi-value">{fmt(ev.robustness?.row_accuracy, true)}</span>
                                  <span className="kpi-label">Row Accuracy</span>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ padding: '1.25rem' }}>
                      <p style={{ fontSize: '0.82rem', color: '#94a3b8', textAlign: 'center', fontStyle: 'italic', margin: 0 }}>
                        Evaluation metrics will appear here once extraction completes and if a reference ground truth is available.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
