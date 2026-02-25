import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const WRITE_API_KEY = import.meta.env.VITE_WRITE_API_KEY || "";
const THEME_KEY = "rag_ui_theme";

function Sparkline({
  points,
  labels = [],
  color = "#2563eb",
  id = "trend",
  valueSuffix = "",
  xAxisLabel = "Time",
  yAxisLabel = "Value",
  yMin = null,
  yMax = null,
  yTicks = [],
  forceConnectedLine = false,
}) {
  const [hoverIndex, setHoverIndex] = useState(null);
  if (!points || points.length === 0) {
    return <div className="apple-empty">No trend data yet</div>;
  }
  const seriesPoints = points.length === 1 ? [points[0], points[0]] : points;
  const seriesLabels = labels.length === 1 ? [labels[0], labels[0]] : labels;

  const width = 320;
  const height = 120;
  const margin = { top: 8, right: 8, bottom: 22, left: 34 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const min = yMin == null ? Math.min(...seriesPoints) : Number(yMin);
  const max = yMax == null ? Math.max(...seriesPoints) : Number(yMax);
  const spread = Math.max(0.00001, max - min);
  const step = seriesPoints.length > 1 ? chartWidth / (seriesPoints.length - 1) : chartWidth;
  const coords = seriesPoints
    .map((value, idx) => {
      const x = margin.left + idx * step;
      const y = margin.top + chartHeight - ((value - min) / spread) * chartHeight;
      return { x, y };
    });
  const activeIdx = hoverIndex == null ? coords.length - 1 : Math.max(0, Math.min(coords.length - 1, hoverIndex));
  const active = coords[activeIdx];
  const activeLabel = seriesLabels[activeIdx] || `Point ${activeIdx + 1}`;
  const activeValue = Number(seriesPoints[activeIdx] || 0);
  const isHovering = hoverIndex !== null;
  const tooltipText = `${activeLabel} | ${activeValue.toFixed(1)}${valueSuffix}`;
  const tooltipWidth = Math.max(86, Math.min(220, tooltipText.length * 5.6));
  const tooltipHeight = 18;
  const tooltipX = Math.min(width - margin.right - tooltipWidth, Math.max(margin.left, active.x + 8));
  const tooltipY = Math.max(margin.top, active.y - 22);

  const d = coords.map((p) => `${p.x},${p.y}`).join(" ");
  const glowId = `spark-glow-${id}`;

  const markerEvery = Math.max(1, Math.floor(coords.length / 5));
  const markers = coords.filter((_, idx) => idx % markerEvery === 0 || idx === coords.length - 1);
  function setHoverFromClientX(clientX, target) {
    const rect = target.getBoundingClientRect();
    const ratio = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
    const clamped = Math.max(0, Math.min(1, ratio));
    const idx = Math.round(clamped * Math.max(0, seriesPoints.length - 1));
    setHoverIndex(idx);
  }

  return (
    <div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="h-36 w-full rounded-2xl bg-white/80 shadow-sm dark:bg-slate-900/80"
        role="img"
        aria-label="Metric trend chart"
        onMouseMove={(e) => setHoverFromClientX(e.clientX, e.currentTarget)}
        onMouseLeave={() => setHoverIndex(null)}
        onTouchMove={(e) => {
          const touch = e.touches?.[0];
          if (touch) setHoverFromClientX(touch.clientX, e.currentTarget);
        }}
      >
        <defs>
          <filter id={glowId} x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation="1.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <line x1={margin.left} y1={margin.top + chartHeight} x2={width - margin.right} y2={margin.top + chartHeight} stroke="#cbd5e1" strokeWidth="1" />
        <line x1={margin.left} y1={margin.top} x2={margin.left} y2={margin.top + chartHeight} stroke="#cbd5e1" strokeWidth="1" />
        {yTicks.map((tick) => {
          const y = margin.top + chartHeight - ((Number(tick) - min) / spread) * chartHeight;
          return (
            <g key={`${id}-tick-${tick}`}>
              <line x1={margin.left} y1={y} x2={width - margin.right} y2={y} stroke="#e2e8f0" strokeWidth="1" />
              <text x={margin.left - 4} y={y + 3} textAnchor="end" className="fill-slate-500 text-[8px]">{tick}</text>
            </g>
          );
        })}
        {coords.length > 1 ? (
          <>
            {forceConnectedLine
              ? coords.slice(1).map((point, idx) => {
                const prev = coords[idx];
                return (
                  <line
                    key={`${id}-seg-${idx}`}
                    x1={prev.x}
                    y1={prev.y}
                    x2={point.x}
                    y2={point.y}
                    stroke={color}
                    strokeWidth="3"
                    strokeLinecap="round"
                    filter={`url(#${glowId})`}
                  />
                );
              })
              : <polyline fill="none" stroke={color} strokeWidth="2.75" points={d} className="sparkline-line" filter={`url(#${glowId})`} />}
          </>
        ) : (
          <line
            x1={margin.left}
            y1={coords[0].y}
            x2={width - margin.right}
            y2={coords[0].y}
            stroke={color}
            strokeWidth="2.75"
            filter={`url(#${glowId})`}
          />
        )}
        {markers.map((p, idx) => (
          <circle key={`${id}-${idx}`} cx={p.x} cy={p.y} r="2.2" fill={color} className="sparkline-dot" />
        ))}
        {isHovering ? <line x1={active.x} y1={margin.top} x2={active.x} y2={margin.top + chartHeight} stroke={color} strokeOpacity="0.25" strokeWidth="1" /> : null}
        {isHovering ? <circle cx={active.x} cy={active.y} r="4" fill={color} /> : null}
        {isHovering ? (
          <g>
            <rect x={tooltipX} y={tooltipY} width={tooltipWidth} height={tooltipHeight} rx="4" fill="#0f172a" fillOpacity="0.88" />
            <text x={tooltipX + 6} y={tooltipY + 12} className="fill-white text-[8.5px]">{tooltipText}</text>
          </g>
        ) : null}
        <text x={width / 2} y={height - 4} textAnchor="middle" className="fill-slate-500 text-[9px]">{xAxisLabel}</text>
        <text
          x="12"
          y={margin.top + chartHeight / 2}
          transform={`rotate(-90 12 ${margin.top + chartHeight / 2})`}
          textAnchor="middle"
          className="fill-slate-500 text-[9px]"
        >
          {yAxisLabel}
        </text>
      </svg>
    </div>
  );
}

function metricTone(type, value) {
  if (value == null || Number.isNaN(Number(value))) {
    return {
      label: "No Data",
      chip: "bg-slate-100 text-slate-600",
      bar: "bg-slate-300",
    };
  }

  const v = Number(value);
  if (type === "latency") {
    if (v <= 3000) return { label: "Good", chip: "bg-emerald-100 text-emerald-700", bar: "bg-emerald-500" };
    if (v <= 8000) return { label: "Watch", chip: "bg-amber-100 text-amber-700", bar: "bg-amber-500" };
    return { label: "Low", chip: "bg-rose-100 text-rose-700", bar: "bg-rose-500" };
  }

  if (v >= 0.9) return { label: "Good", chip: "bg-emerald-100 text-emerald-700", bar: "bg-emerald-500" };
  if (v >= 0.75) return { label: "Watch", chip: "bg-amber-100 text-amber-700", bar: "bg-amber-500" };
  return { label: "Low", chip: "bg-rose-100 text-rose-700", bar: "bg-rose-500" };
}

function InfoDot({ text }) {
  return (
    <span title={text} className="ml-2 inline-flex h-4 w-4 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-600">
      i
    </span>
  );
}

function ThemeSwitch({ isDark, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`theme-switch ${isDark ? "theme-switch-dark" : ""}`}
      role="switch"
      aria-checked={isDark}
      aria-label="Toggle dark mode"
      title="Toggle light or dark mode"
    >
      <span className="theme-switch-track" />
      <span className={`theme-switch-thumb ${isDark ? "theme-switch-thumb-dark" : ""}`} />
      <span className="theme-switch-icon-left" aria-hidden="true">
        ☀
      </span>
      <span className="theme-switch-icon-right" aria-hidden="true">
        ☾
      </span>
    </button>
  );
}

function Panel({ title, subtitle, actions, children, className = "" }) {
  return (
    <section className={`apple-panel ${className}`}>
      <div className="apple-panel-accent" />
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="apple-title">{title}</h2>
          {subtitle ? <p className="apple-subtitle">{subtitle}</p> : null}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

function MetricCard({ title, info, value, subtitle, tone }) {
  return (
    <article className="apple-panel overflow-hidden p-0">
      <div className={`h-1.5 w-full ${tone.bar}`} />
      <div className="p-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-sm font-semibold text-slate-700">
            {title}
            <InfoDot text={info} />
          </p>
          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${tone.chip}`}>{tone.label}</span>
        </div>
        <p className="text-2xl font-semibold tracking-tight text-slate-900">{value}</p>
        <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
      </div>
    </article>
  );
}

function sourceLabelFromValue(source) {
  const raw = String(source || "").trim();
  if (!raw) return "this source";
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    try {
      const url = new URL(raw);
      const pathPart = url.pathname.split("/").filter(Boolean).pop();
      if (pathPart) return decodeURIComponent(pathPart).replace(/[-_]+/g, " ");
      return url.hostname.replace(/^www\./, "");
    } catch {
      return raw;
    }
  }
  const filePart = raw.split(/[\\/]/).pop() || raw;
  return filePart.replace(/\.[a-z0-9]+$/i, "").replace(/[-_]+/g, " ");
}

function buildSourceSuggestions(items, maxCount = 6) {
  const templates = [
    "Give me a concise summary of {label}.",
    "What are the key facts and definitions in {label}?",
    "What should I know first from {label}?",
    "List the most important takeaways from {label}.",
  ];
  const seen = new Set();
  const suggestions = [];
  for (const src of items) {
    const label = sourceLabelFromValue(src?.source).trim();
    if (!label) continue;
    const key = label.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    const first = templates[0].replace("{label}", label);
    const second = templates[1].replace("{label}", label);
    suggestions.push({
      id: `${src?.id || label}-q1`,
      question: first,
    });
    if (suggestions.length >= maxCount) break;
    suggestions.push({
      id: `${src?.id || label}-q2`,
      question: second,
    });
    if (suggestions.length >= maxCount) break;
  }
  return suggestions;
}

export default function App() {
  const initialView = window.location.hash === "#/dashboard" ? "dashboard" : window.location.hash === "#/history" ? "history" : "home";
  const [view, setView] = useState(initialView);
  const [theme, setTheme] = useState(() => {
    const saved = window.localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  const [question, setQuestion] = useState("");
  const [contextScope, setContextScope] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const [linkUrl, setLinkUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [ingestMessage, setIngestMessage] = useState("");

  const [metrics, setMetrics] = useState(null);
  const [metricsError, setMetricsError] = useState("");
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [modelSelectValue, setModelSelectValue] = useState("");
  const [modelSelectLoading, setModelSelectLoading] = useState(false);

  const [jobs, setJobs] = useState([]);
  const [jobsError, setJobsError] = useState("");
  const [sources, setSources] = useState([]);
  const [sourceState, setSourceState] = useState({ total_sources: 0, last_reset_utc: null, reset_count: 0 });
  const [sourcesError, setSourcesError] = useState("");

  const [history, setHistory] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [expandedCitations, setExpandedCitations] = useState({});
  const [queryHistory, setQueryHistory] = useState([]);
  const [queryRuns, setQueryRuns] = useState([]);
  const [queryRunsLoading, setQueryRunsLoading] = useState(false);
  const [queryRunsError, setQueryRunsError] = useState("");
  const [historySearch, setHistorySearch] = useState("");
  const [historyCitationFilter, setHistoryCitationFilter] = useState("all");
  const [historyWindowHours, setHistoryWindowHours] = useState("all");
  const [readyToast, setReadyToast] = useState("");
  const answerPanelRef = useRef(null);
  const questionInputRef = useRef(null);
  const withWriteApiKey = (headers = {}) => (WRITE_API_KEY ? { ...headers, "X-API-Key": WRITE_API_KEY } : headers);

  const canSubmit = useMemo(() => question.trim().length >= 3 && !loading, [question, loading]);
  const topPanelClass = "sm:min-h-[430px] h-full";
  const processSteps = [
    ["1. Ingest", "Upload or link docs into the vector index"],
    ["2. Retrieve", "Find relevant chunks from Chroma"],
    ["3. Generate", "Ollama answers with grounded context"],
    ["4. Measure", "Track latency, retrieval quality, and reliability"],
  ];
  const ingestSummary = useMemo(() => {
    const total = jobs.length;
    const success = jobs.filter((j) => j.status === "success").length;
    const running = jobs.filter((j) => j.status === "running" || j.status === "queued").length;
    const failed = jobs.filter((j) => j.status === "error").length;
    return { total, success, running, failed };
  }, [jobs]);

  const latencyTone = metrics ? metricTone("latency", metrics.latency_p95_ms) : metricTone("latency", null);
  const retrievalTone = metrics ? metricTone("rate", metrics.recall_at_5) : metricTone("rate", null);
  const reliabilityTone = metrics ? metricTone("rate", metrics.success_rate) : metricTone("rate", null);
  const coverageTone = metrics ? metricTone("rate", metrics.eval_coverage) : metricTone("rate", null);
  const confidenceTone = metrics ? metricTone("rate", metrics.calibrated_quality_24h) : metricTone("rate", null);
  const sourceSuggestions = useMemo(() => buildSourceSuggestions(sources, 6), [sources]);
  const requestTrend = history?.request_trend || [];
  const evalTrend = history?.eval_trend || [];
  const answerQualityTrend = useMemo(() => {
    const ordered = [...queryRuns].reverse().slice(-30);
    return ordered.map((run) => {
      const fromFeedback = typeof run.feedback_is_correct === "boolean";
      const value = fromFeedback ? (run.feedback_is_correct ? 100 : 0) : Number(run.correctness_probability || 0) * 100;
      return {
        label: new Date(run.ts_utc).toLocaleTimeString(),
        value,
      };
    });
  }, [queryRuns]);
  const filteredQueryRuns = useMemo(() => {
    const search = historySearch.trim().toLowerCase();
    const hours = historyWindowHours === "all" ? null : Number(historyWindowHours);
    const cutoffMs = hours ? Date.now() - hours * 60 * 60 * 1000 : null;

    return queryRuns.filter((run) => {
      const hasCitations = Array.isArray(run.citations) && run.citations.length > 0;
      if (historyCitationFilter === "with" && !hasCitations) return false;
      if (historyCitationFilter === "without" && hasCitations) return false;

      if (cutoffMs) {
        const tsMs = new Date(run.ts_utc).getTime();
        if (Number.isFinite(tsMs) && tsMs < cutoffMs) return false;
      }

      if (!search) return true;
      const citationText = (Array.isArray(run.citations) ? run.citations : [])
        .map((c) => `${c.source || ""} ${c.doc_id || ""} ${c.text_preview || ""}`)
        .join(" ")
        .toLowerCase();
      const haystack = `${run.question || ""}\n${run.answer || ""}\n${citationText}`.toLowerCase();
      return haystack.includes(search);
    });
  }, [queryRuns, historySearch, historyCitationFilter, historyWindowHours]);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    if (!result || loading) return;
    const node = answerPanelRef.current;
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "nearest" });
    window.setTimeout(() => {
      node.focus({ preventScroll: true });
    }, 220);
  }, [result, loading]);

  useEffect(() => {
    const onHashChange = () => {
      if (window.location.hash === "#/dashboard") setView("dashboard");
      else if (window.location.hash === "#/history") setView("history");
      else setView("home");
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  async function fetchMetrics() {
    setMetricsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/metrics/summary`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setMetrics(await response.json());
      setMetricsError("");
    } catch (err) {
      setMetricsError(err instanceof Error ? err.message : "Metrics request failed");
    } finally {
      setMetricsLoading(false);
    }
  }

  async function fetchJobs() {
    try {
      const response = await fetch(`${API_BASE}/ingest/jobs?limit=8`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setJobs(payload.jobs || []);
      setJobsError("");
    } catch (err) {
      setJobsError(err instanceof Error ? err.message : "Job request failed");
    }
  }

  async function fetchModelInfo() {
    try {
      const response = await fetch(`${API_BASE}/models`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setModelInfo(payload);
      if (!modelSelectValue) {
        setModelSelectValue(payload.active_chat_model || payload.chat_model || "");
      }
    } catch {
      // Optional endpoint for UI metadata.
    }
  }

  async function applyModelSelection() {
    if (!modelSelectValue) return;
    setModelSelectLoading(true);
    try {
      const response = await fetch(`${API_BASE}/models/select`, {
        method: "POST",
        headers: withWriteApiKey({ "Content-Type": "application/json" }),
        body: JSON.stringify({ chat_model: modelSelectValue }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `HTTP ${response.status}`);
      }
      const payload = await response.json();
      setModelInfo(payload);
      setReadyToast(`Model switched to ${payload.active_chat_model || payload.chat_model}`);
      window.setTimeout(() => setReadyToast(""), 2200);
      await Promise.all([fetchMetrics(), fetchQueryRuns()]);
    } catch (err) {
      setReadyToast(`Model switch failed: ${err instanceof Error ? err.message : "Unknown error"}`);
      window.setTimeout(() => setReadyToast(""), 2600);
    } finally {
      setModelSelectLoading(false);
    }
  }

  async function fetchSources() {
    try {
      const response = await fetch(`${API_BASE}/ingest/sources?limit=50`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setSources(Array.isArray(payload.items) ? payload.items : []);
      setSourceState({
        total_sources: Number(payload.total_sources || 0),
        last_reset_utc: payload.last_reset_utc || null,
        reset_count: Number(payload.reset_count || 0),
      });
      setSourcesError("");
    } catch (err) {
      setSourcesError(err instanceof Error ? err.message : "Sources request failed");
    }
  }

  async function fetchHistory() {
    setHistoryLoading(true);
    try {
      const response = await fetch(`${API_BASE}/metrics/history?hours=24&bucket_minutes=60`);
      if (response.status === 404) {
        setHistory(null);
        setHistoryUnavailable(true);
        setHistoryError("");
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setHistory(await response.json());
      setHistoryError("");
      setHistoryUnavailable(false);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "History request failed");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function fetchQueryHistory() {
    try {
      const response = await fetch(`${API_BASE}/query/history?limit=8`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const items = Array.isArray(payload.items) ? payload.items : [];
      setQueryHistory(
        items.map((item) => ({
          question: item.question,
          topK: Number(item.top_k),
          ts: item.ts_utc,
          hit: Boolean(item.hit),
          error: item.error || null,
        })),
      );
    } catch {
      // Keep local in-memory history if endpoint is unavailable.
    }
  }

  async function fetchQueryRuns() {
    setQueryRunsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/query/runs?limit=100`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setQueryRuns(Array.isArray(payload.items) ? payload.items : []);
      setQueryRunsError("");
    } catch (err) {
      setQueryRunsError(err instanceof Error ? err.message : "Query runs request failed");
    } finally {
      setQueryRunsLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    async function poll() {
      if (!active) return;
      await Promise.all([fetchMetrics(), fetchJobs(), fetchHistory(), fetchQueryHistory(), fetchQueryRuns(), fetchSources(), fetchModelInfo()]);
    }
    poll();
    const timer = setInterval(poll, 60000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  function navigate(nextView) {
    if (nextView === "dashboard") window.location.hash = "/dashboard";
    else if (nextView === "history") window.location.hash = "/history";
    else window.location.hash = "/";
  }

  function toggleTheme() {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }

  async function submitQuery(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    setExpandedCitations({});
    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: withWriteApiKey({ "Content-Type": "application/json" }),
        body: JSON.stringify({ question, top_k: Number(contextScope) }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `HTTP ${response.status}`);
      }
      const payload = await response.json();
      setResult(payload);
      setReadyToast("Your answer is ready!");
      window.setTimeout(() => setReadyToast(""), 2600);
      setQueryHistory((prev) => [{ question, topK: Number(contextScope), ts: new Date().toISOString() }, ...prev].slice(0, 8));
      await Promise.all([fetchMetrics(), fetchHistory(), fetchQueryHistory(), fetchQueryRuns()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown request error");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  async function pollIngestJob(jobId) {
    const maxAttempts = 30;
    const delayMs = 1000;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const response = await fetch(`${API_BASE}/ingest/jobs/${jobId}`);
      if (!response.ok) throw new Error(`Job polling failed with HTTP ${response.status}`);
      const job = await response.json();
      if (job.status === "success") {
        const summary = job.summary || {};
        setIngestMessage(
          `Job ${jobId} completed in ${Number(job.latency_ms || 0).toFixed(1)} ms after ${job.attempt_count}/${job.max_attempts} attempts. Docs: ${summary.docs ?? 0}, chunks: ${summary.chunks ?? 0}, vectors: ${summary.vector_count ?? 0}.`,
        );
        return;
      }
      if (job.status === "error") throw new Error(job.error || "Ingestion job failed");
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
    throw new Error(`Job ${jobId} timed out`);
  }

  async function ingestUpload(event) {
    event.preventDefault();
    if (!selectedFile) return;
    setIngestLoading(true);
    setIngestMessage("");
    try {
      const form = new FormData();
      form.append("file", selectedFile);
      const response = await fetch(`${API_BASE}/ingest/upload`, { method: "POST", headers: withWriteApiKey(), body: form });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setIngestMessage(`Job ${payload.job_id} queued. Waiting...`);
      await pollIngestJob(payload.job_id);
      setSelectedFile(null);
      await Promise.all([fetchJobs(), fetchSources()]);
    } catch (err) {
      setIngestMessage(`Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIngestLoading(false);
    }
  }

  async function ingestLink(event) {
    event.preventDefault();
    if (!linkUrl.trim()) return;
    setIngestLoading(true);
    setIngestMessage("");
    try {
      const response = await fetch(`${API_BASE}/ingest/link`, {
        method: "POST",
        headers: withWriteApiKey({ "Content-Type": "application/json" }),
        body: JSON.stringify({ url: linkUrl.trim() }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setIngestMessage(`Job ${payload.job_id} queued. Waiting...`);
      await pollIngestJob(payload.job_id);
      setLinkUrl("");
      await Promise.all([fetchJobs(), fetchSources()]);
    } catch (err) {
      setIngestMessage(`Ingest failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIngestLoading(false);
    }
  }

  async function resetIndexedKnowledge() {
    const ok = window.confirm("Reset indexed knowledge now? This clears the current vector index and citations context.");
    if (!ok) return;
    setResetLoading(true);
    setIngestMessage("");
    try {
      const response = await fetch(`${API_BASE}/ingest/reset`, {
        method: "POST",
        headers: withWriteApiKey({ "Content-Type": "application/json" }),
        body: JSON.stringify({ confirm: true }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `HTTP ${response.status}`);
      }
      const payload = await response.json();
      setResult(null);
      setExpandedCitations({});
      setIngestMessage(`Reset complete. Vector count: ${payload.vector_count}. Sources cleared: ${payload.sources_cleared}.`);
      await Promise.all([fetchJobs(), fetchMetrics(), fetchHistory(), fetchSources()]);
    } catch (err) {
      setIngestMessage(`Reset failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setResetLoading(false);
    }
  }

  function rerunFromHistory(item) {
    setQuestion(item.question);
    setContextScope(item.topK);
  }

  async function copyAnswer() {
    if (!result?.answer) return;
    try {
      await navigator.clipboard.writeText(result.answer);
    } catch {
      // ignore clipboard failures
    }
  }

  async function copyRunDetails(run) {
    const citations = Array.isArray(run.citations) ? run.citations : [];
    const citationLines = citations.length
      ? citations.map((c, idx) => {
        const source = c?.source || c?.doc_id || `Citation ${idx + 1}`;
        const preview = c?.text_preview ? ` | ${String(c.text_preview).slice(0, 180)}` : "";
        return `- [${idx + 1}] ${source}${preview}`;
      }).join("\n")
      : "- none";
    const text = [
      `Run #${run.id}`,
      `Timestamp: ${new Date(run.ts_utc).toLocaleString()}`,
      `Context Scope: ${run.top_k ?? "--"}`,
      `Latency: ${Number(run.latency_ms).toFixed(1)} ms`,
      `Correctness Probability (estimated): ${run.correctness_probability != null ? `${(Number(run.correctness_probability) * 100).toFixed(1)}%` : "--"}`,
      `Model: ${run.chat_model || modelInfo?.chat_model || "--"}`,
      "",
      `Question: ${run.question}`,
      "",
      "Answer:",
      String(run.answer || ""),
      "",
      "Citations:",
      citationLines,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setReadyToast("Run details copied");
      window.setTimeout(() => setReadyToast(""), 2200);
    } catch {
      // ignore clipboard failures
    }
  }

  async function submitRunFeedback(runId, isCorrect) {
    try {
      const response = await fetch(`${API_BASE}/query/runs/${runId}/feedback`, {
        method: "POST",
        headers: withWriteApiKey({ "Content-Type": "application/json" }),
        body: JSON.stringify({ is_correct: isCorrect }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      setQueryRuns((prev) => prev.map((run) => (
        run.id === runId
          ? { ...run, feedback_is_correct: Boolean(payload.is_correct), feedback_note: payload.note || null, feedback_ts_utc: payload.ts_utc || null }
          : run
      )));
      setReadyToast(isCorrect ? "Marked as correct" : "Marked as incorrect");
      window.setTimeout(() => setReadyToast(""), 1800);
      await fetchMetrics();
    } catch {
      setReadyToast("Feedback save failed");
      window.setTimeout(() => setReadyToast(""), 1800);
    }
  }

  function toggleCitation(key) {
    setExpandedCitations((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function applySuggestedQuestion(item) {
    setQuestion(item.question);
    questionInputRef.current?.focus();
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#dbeafe_0%,#eff6ff_35%,#e2e8f0_100%)] dark:bg-[radial-gradient(circle_at_top,#1e3a8a_0%,#0f172a_42%,#020617_100%)]">
      <div className="mx-auto w-full max-w-7xl px-3 py-4 sm:px-5 sm:py-6 lg:px-8">
        <header className="apple-panel apple-panel-glass mb-3 sm:mb-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl lg:text-4xl">RAG Assistant</h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-600">Query your knowledge base, monitor reliability, and track eval quality live.</p>
              {modelInfo ? (
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-slate-600">
                    Model: <strong>{modelInfo.active_chat_model || modelInfo.chat_model}</strong> | Embeddings: <strong>{modelInfo.embed_model}</strong>
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={modelSelectValue}
                      onChange={(e) => setModelSelectValue(e.target.value)}
                      className="apple-input py-1 text-xs"
                    >
                      {(modelInfo.available_chat_models || []).length > 0
                        ? modelInfo.available_chat_models.map((name) => (
                          <option key={name} value={name}>{name}</option>
                        ))
                        : <option value={modelInfo.active_chat_model || modelInfo.chat_model}>{modelInfo.active_chat_model || modelInfo.chat_model}</option>}
                    </select>
                    <button
                      type="button"
                      onClick={applyModelSelection}
                      disabled={modelSelectLoading || !modelSelectValue || modelSelectValue === (modelInfo.active_chat_model || modelInfo.chat_model)}
                      className="apple-button-secondary disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {modelSelectLoading ? "Switching..." : "Switch Model"}
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${metricsError ? "bg-rose-100 text-rose-700" : "bg-emerald-100 text-emerald-700"}`}>
                {metricsError ? "Metrics Offline" : "Metrics Live"}
              </span>
              <button type="button" onClick={() => navigate("home")} className={`apple-segment ${view === "home" ? "apple-segment-active" : ""}`}>
                Home
              </button>
              <button type="button" onClick={() => navigate("dashboard")} className={`apple-segment ${view === "dashboard" ? "apple-segment-active" : ""}`}>
                Dashboard
              </button>
              <button type="button" onClick={() => navigate("history")} className={`apple-segment ${view === "history" ? "apple-segment-active" : ""}`}>
                History
              </button>
              <ThemeSwitch isDark={theme === "dark"} onToggle={toggleTheme} />
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
            <span>{metrics?.updated_at ? `Last update ${new Date(metrics.updated_at).toLocaleTimeString()}` : "Waiting for metrics sync"}</span>
            <button type="button" onClick={fetchMetrics} disabled={metricsLoading} className="apple-button-secondary">
              {metricsLoading ? "Refreshing..." : "Refresh Metrics"}
            </button>
            <button type="button" onClick={fetchJobs} className="apple-button-secondary">
              Refresh Jobs
            </button>
          </div>
        </header>

        <section className="mb-3 grid grid-cols-1 gap-2.5 sm:mb-4 sm:grid-cols-2 sm:gap-3 xl:grid-cols-5">
          <MetricCard
            title="Response Speed"
            info="95% of requests are this fast or faster. Lower is better."
            value={metrics ? `${Number(metrics.latency_p95_ms).toFixed(1)} ms` : "--"}
            subtitle="End-user response time"
            tone={latencyTone}
          />
          <MetricCard
            title="Retrieval Quality"
            info="How often relevant documents are retrieved for benchmark prompts."
            value={metrics ? `${(Number(metrics.recall_at_5) * 100).toFixed(1)}%` : "--"}
            subtitle="Relevant context retrieval"
            tone={retrievalTone}
          />
          <MetricCard
            title="System Reliability"
            info="Percent of successful query calls in the last 24 hours."
            value={metrics ? `${(Number(metrics.success_rate) * 100).toFixed(1)}%` : "--"}
            subtitle="24-hour request success rate"
            tone={reliabilityTone}
          />
          <MetricCard
            title="Eval Coverage"
            info="Share of benchmark cases included in the latest evaluation run."
            value={metrics ? `${(Number(metrics.eval_coverage) * 100).toFixed(1)}%` : "--"}
            subtitle="Benchmark scenario coverage"
            tone={coverageTone}
          />
          <MetricCard
            title="Answer Quality"
            info="Calibrated quality using retrieval confidence plus your correct/incorrect feedback."
            value={metrics ? `${(Number(metrics.calibrated_quality_24h || 0) * 100).toFixed(1)}%` : "--"}
            subtitle={metrics ? `24h feedback ${Number(metrics.feedback_samples_24h || 0)} | model runs ${Number(metrics.confidence_samples_24h || 0)}` : "24h average"}
            tone={confidenceTone}
          />
        </section>

        {metricsError ? <p className="mb-3 text-sm text-rose-700">Metrics poll failed: {metricsError}</p> : null}
        {historyError ? <p className="mb-3 text-sm text-rose-700">Trend poll failed: {historyError}</p> : null}
        {historyUnavailable ? <p className="mb-3 text-sm text-amber-700">Trend data endpoint unavailable (`/metrics/history` returned 404). Restart the API server to load the latest routes.</p> : null}
        {readyToast ? (
          <div className="mb-3">
            <div className="toast-ready">{readyToast}</div>
          </div>
        ) : null}

        {view === "home" ? (
          <main className="space-y-3 sm:space-y-4">
            <section className="grid grid-cols-1 gap-2.5 sm:gap-3 md:grid-cols-2 xl:grid-cols-4">
              {processSteps.map(([title, text]) => (
                <div key={title} className="apple-panel">
                  <p className="text-lg font-semibold tracking-tight text-slate-900">{title}</p>
                  <p className="mt-1 text-sm text-slate-500">{text}</p>
                </div>
              ))}
            </section>
            <section className="grid grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-12">
              <div className="space-y-3 sm:space-y-4 xl:col-span-6">
              <Panel title="Ask a Question" subtitle="Generate grounded answers from your indexed docs." className={`apple-panel-primary ${topPanelClass}`}>
                {loading ? <div className="mb-3 h-1.5 w-full animate-pulse rounded-full bg-blue-200" /> : null}
                <form onSubmit={submitQuery} className="space-y-3">
                  <label className="block text-sm font-medium text-slate-700">
                    Question
                    <textarea ref={questionInputRef} value={question} onChange={(e) => setQuestion(e.target.value)} rows={4} className="apple-input mt-1" placeholder="Start your question here..." />
                  </label>
                  {sourceSuggestions.length > 0 ? (
                    <div>
                      <p className="mb-1 text-xs font-semibold text-slate-600">Suggested from indexed sources</p>
                      <div className="flex flex-wrap gap-1.5 sm:gap-2">
                        {sourceSuggestions.map((item) => (
                          <button key={item.id} type="button" onClick={() => applySuggestedQuestion(item)} className="apple-chip" title={item.question}>
                            {item.question}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">Index documents to unlock source-based suggested questions.</p>
                  )}

                  <label className="block text-sm font-medium text-slate-700">
                    Context Scope
                    <InfoDot text="How many retrieved chunks are used to answer. Higher can improve recall but can increase latency." />
                    <div className="mt-2">
                      <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
                        <span>Focused (1)</span>
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 font-semibold text-blue-700">Current: {contextScope}</span>
                        <span>Broad (15)</span>
                      </div>
                      <input
                        type="range"
                        min={1}
                        max={15}
                        step={1}
                        value={contextScope}
                        onChange={(e) => setContextScope(Number(e.target.value))}
                        className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-200 accent-blue-600"
                      />
                    </div>
                  </label>

                  <div className="flex flex-wrap gap-1.5 sm:gap-2">
                    <button type="submit" disabled={!canSubmit} className="apple-button-primary disabled:cursor-not-allowed disabled:opacity-50">
                      {loading ? <span className="inline-flex items-center gap-2"><span className="loading-dot" />Thinking...</span> : "Run Query"}
                    </button>
                  </div>
                </form>

                {error ? <p className="mt-3 text-sm text-rose-700">Error: {error}</p> : null}
                <p className="mt-3 text-xs text-slate-500">API: {API_BASE}</p>
              </Panel>
              </div>

              <div className="space-y-3 sm:space-y-4 xl:col-span-6">
              <div ref={answerPanelRef} tabIndex={-1} className="outline-none">
              <Panel
                title="Answer"
                subtitle="Generated output with latency and retrieved source IDs."
                className={topPanelClass}
                actions={
                  <div className="flex gap-2">
                    <button type="button" onClick={() => navigate("history")} className="apple-button-secondary">
                      View History
                    </button>
                    {result ? (
                      <button type="button" onClick={copyAnswer} className="apple-button-secondary">
                        Copy
                      </button>
                    ) : null}
                  </div>
                }
              >
                {loading ? <div className="h-24 animate-pulse rounded-2xl bg-slate-100" /> : null}
                {result && !loading ? (
                  <div className="answer-enter">
                    <div className="mb-2 flex flex-wrap gap-2">
                      <span className="apple-kpi-pill">Latency {Number(result.latency_ms).toFixed(1)} ms</span>
                      <span className="apple-kpi-pill">Citations {Array.isArray(result.citations) ? result.citations.length : 0}</span>
                      <span className="apple-kpi-pill">Confidence {(Number(result.correctness_probability || 0) * 100).toFixed(1)}%</span>
                      <span className="apple-kpi-pill">Model {result.chat_model || modelInfo?.chat_model || "--"}</span>
                    </div>
                    <p className="whitespace-pre-wrap text-sm text-slate-800">{result.answer}</p>
                    <p className="mt-2 text-xs text-slate-500">Latency {Number(result.latency_ms).toFixed(1)} ms | Retrieved {result.retrieved_doc_ids.join(", ") || "none"}</p>
                  </div>
                ) : null}
                {!result && !loading ? <p className="text-sm text-slate-500">Submit a query to see an answer and citations.</p> : null}
              </Panel>
              </div>
              </div>
            </section>

            {result ? (
              <section>
                <Panel title="Citations" subtitle="Inspect chunks used by the answer.">
                  {result?.citations?.length ? (
                    <ul className="space-y-2">
                      {result.citations.map((c) => {
                        const key = `${c.doc_id}-${c.chunk_index}-${c.rank}`;
                        const open = Boolean(expandedCitations[key]);
                        const preview = String(c.text_preview || "");
                        return (
                          <li key={key} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-bold text-slate-700">[{c.rank}]</span>
                              <span className="text-sm font-semibold text-slate-900">{c.source}</span>
                              <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-700">distance {c.distance}</span>
                              <button type="button" onClick={() => toggleCitation(key)} className="apple-chip">
                                {open ? "Collapse" : "Expand"}
                              </button>
                            </div>
                            <p className="mt-1 text-xs text-slate-500">doc_id {c.doc_id} | chunk {c.chunk_index}</p>
                            <p className="mt-1 text-sm text-slate-700">{open ? preview : `${preview.slice(0, 180)}...`}</p>
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500">No citations returned for this answer.</p>
                  )}
                </Panel>
              </section>
            ) : null}

            <section className="grid grid-cols-1 gap-3 sm:gap-4 xl:grid-cols-2">
              <Panel
                title="Knowledge Ingestion"
                subtitle="Upload files or index from links."
                actions={
                  <button type="button" onClick={resetIndexedKnowledge} disabled={resetLoading || ingestLoading} className="apple-button-secondary disabled:cursor-not-allowed disabled:opacity-50">
                    {resetLoading ? "Resetting..." : "Reset Indexed Knowledge"}
                  </button>
                }
              >
                <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                  <p>
                    Indexed sources: <strong>{sourceState.total_sources}</strong>
                    {" | "}
                    Resets: <strong>{sourceState.reset_count}</strong>
                  </p>
                  <p className="mt-1">
                    Last reset: {sourceState.last_reset_utc ? new Date(sourceState.last_reset_utc).toLocaleString() : "Never"}
                  </p>
                </div>
                <form onSubmit={ingestUpload} className="space-y-2">
                  <label className="block text-sm font-medium text-slate-700">
                    Upload (`.pdf`, `.md`, `.txt`)
                    <input type="file" accept=".pdf,.md,.txt" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} className="apple-input mt-1" />
                  </label>
                  <button type="submit" disabled={!selectedFile || ingestLoading} className="apple-button-primary disabled:cursor-not-allowed disabled:opacity-50">
                    {ingestLoading ? "Working..." : "Upload + Index"}
                  </button>
                </form>

                <form onSubmit={ingestLink} className="mt-3 space-y-2 border-t border-slate-200 pt-3">
                  <label className="block text-sm font-medium text-slate-700">
                    Link (http/https)
                    <input type="url" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} placeholder="https://example.com/page-or-doc" className="apple-input mt-1" />
                  </label>
                  <button type="submit" disabled={!linkUrl.trim() || ingestLoading} className="apple-button-primary disabled:cursor-not-allowed disabled:opacity-50">
                    {ingestLoading ? "Working..." : "Fetch + Index"}
                  </button>
                </form>

                {ingestMessage ? <p className="mt-2 text-xs text-slate-600">{ingestMessage}</p> : null}
              </Panel>

              <Panel title="Ingestion Monitor" subtitle="Recent ingestion jobs and status.">
                <div className="mb-3 flex flex-wrap gap-2">
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">Total {ingestSummary.total}</span>
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">Success {ingestSummary.success}</span>
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">Running {ingestSummary.running}</span>
                  <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">Failed {ingestSummary.failed}</span>
                </div>
                {jobsError ? <p className="text-sm text-rose-700">Jobs failed to load: {jobsError}</p> : null}
                {sourcesError ? <p className="mb-2 text-sm text-rose-700">Sources failed to load: {sourcesError}</p> : null}
                {jobs.length ? (
                  <ul className="space-y-2">
                    {jobs.map((job) => (
                      <li key={job.job_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                        <div className="flex items-center justify-between">
                          <strong className="text-sm text-slate-800">#{job.job_id}</strong>
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                              job.status === "success"
                                ? "bg-emerald-100 text-emerald-700"
                                : job.status === "error"
                                  ? "bg-rose-100 text-rose-700"
                                  : "bg-amber-100 text-amber-700"
                            }`}
                          >
                            {job.status}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-slate-600">
                          {job.source_type}: {job.source}
                        </p>
                        <p className="text-xs text-slate-500">attempts {job.attempt_count}/{job.max_attempts} | latency {job.latency_ms ? `${Number(job.latency_ms).toFixed(1)} ms` : "--"}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">No ingestion jobs yet.</p>
                )}
                <div className="mt-3 border-t border-slate-200 pt-3">
                  <p className="mb-2 text-sm font-semibold text-slate-700">Indexed Sources</p>
                  {sources.length ? (
                    <ul className="space-y-2">
                      {sources.map((src) => (
                        <li key={`${src.id}-${src.doc_id}`} className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
                          <p className="text-xs font-semibold text-slate-700">
                            {src.source_type === "link" ? "Link" : "Upload"} | {new Date(src.ingested_utc).toLocaleTimeString()}
                          </p>
                          <p className="truncate text-xs text-slate-600">{src.source}</p>
                          <p className="truncate text-[11px] text-slate-500">{src.doc_id}</p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500">No indexed sources tracked yet.</p>
                  )}
                </div>
              </Panel>
            </section>

            <section>
              <Panel title="Recent Queries" subtitle="Reuse previously submitted prompts.">
                {queryHistory.length ? (
                  <ul className="space-y-2">
                    {queryHistory.map((item, idx) => (
                      <li key={`${item.ts}-${idx}`} className="flex items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                        <div>
                          <p className="text-sm font-medium text-slate-800">{item.question}</p>
                          <p className="mt-0.5 text-xs text-slate-500">
                            {new Date(item.ts).toLocaleTimeString()}
                            {item.error ? <span className="ml-2 rounded-full bg-rose-100 px-2 py-0.5 font-semibold text-rose-700">Error</span> : null}
                            {!item.error && typeof item.hit === "boolean" ? (
                              <span className={`ml-2 rounded-full px-2 py-0.5 font-semibold ${item.hit ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{item.hit ? "Hit" : "Miss"}</span>
                            ) : null}
                          </p>
                          {item.error ? <p className="mt-1 text-xs text-rose-700">{String(item.error).slice(0, 110)}</p> : null}
                        </div>
                        <button type="button" onClick={() => rerunFromHistory(item)} className="apple-chip">
                          Reuse
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">Your recent queries will appear here.</p>
                )}
              </Panel>
            </section>
          </main>
        ) : view === "dashboard" ? (
          <main className="space-y-3 sm:space-y-4">
            <section className="grid grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-2">
              <Panel title="Response Speed Trend" subtitle="Latency trend over last 24h (hourly buckets).">
                <Sparkline
                  id="latency"
                  points={requestTrend.map((p) => Number(p.latency_p95_ms || 0))}
                  labels={requestTrend.map((p) => new Date(p.bucket_utc).toLocaleTimeString())}
                  valueSuffix=" ms"
                  xAxisLabel="Time (24h window)"
                  yAxisLabel="Latency ms"
                  yMin={0}
                  color="#f97316"
                />
                {requestTrend.length === 0 ? <p className="mt-1 text-xs text-amber-700">No query traffic in this window yet. Run a few questions on Home to populate.</p> : null}
              </Panel>
              <Panel title="Reliability Trend" subtitle="Successful query request rate trend over last 24h (hourly buckets).">
                <Sparkline
                  id="reliability"
                  points={requestTrend.map((p) => Number(p.success_rate || 0) * 100)}
                  labels={requestTrend.map((p) => new Date(p.bucket_utc).toLocaleTimeString())}
                  valueSuffix="%"
                  xAxisLabel="Time (24h window)"
                  yAxisLabel="Success %"
                  yMin={0}
                  yMax={100}
                  forceConnectedLine
                  color="#14b8a6"
                />
                {requestTrend.length === 0 ? <p className="mt-1 text-xs text-amber-700">No query traffic in this window yet. Run a few questions on Home to populate.</p> : null}
              </Panel>
              <Panel title="Retrieval Quality Trend" subtitle="Retrieval quality trend from eval runs (%).">
                <Sparkline
                  id="retrieval"
                  points={evalTrend.map((p) => Number(p.recall_at_5 || 0) * 100)}
                  labels={evalTrend.map((p) => new Date(p.ts_utc).toLocaleString())}
                  valueSuffix="%"
                  xAxisLabel="Eval Run Time"
                  yAxisLabel="Recall@5 %"
                  yMin={0}
                  yMax={100}
                  color="#3b82f6"
                />
                {evalTrend.length === 0 ? <p className="mt-1 text-xs text-amber-700">No eval runs yet. Run `python -m scripts.run_eval` to generate this chart.</p> : null}
              </Panel>
              <Panel title="Eval Pass Trend" subtitle="Eval pass rate trend over time (%).">
                <Sparkline
                  id="eval-pass"
                  points={evalTrend.map((p) => Number(p.eval_pass_rate || 0) * 100)}
                  labels={evalTrend.map((p) => new Date(p.ts_utc).toLocaleString())}
                  valueSuffix="%"
                  xAxisLabel="Eval Run Time"
                  yAxisLabel="Pass Rate %"
                  yMin={0}
                  yMax={100}
                  color="#6366f1"
                />
                {evalTrend.length === 0 ? <p className="mt-1 text-xs text-amber-700">No eval runs yet. Run `python -m scripts.run_eval` to generate this chart.</p> : null}
              </Panel>
              <Panel title="Answer Quality Trend" subtitle="Per-query quality score over recent runs (%)." className="lg:col-span-2">
                <Sparkline
                  id="answer-quality"
                  points={answerQualityTrend.map((p) => Number(p.value || 0))}
                  labels={answerQualityTrend.map((p) => p.label)}
                  valueSuffix="%"
                  xAxisLabel="Query Time"
                  yAxisLabel="Quality %"
                  yMin={0}
                  yMax={100}
                  color="#22c55e"
                />
                {answerQualityTrend.length === 0 ? <p className="mt-1 text-xs text-amber-700">No query runs yet. Run a few questions on Home to generate this chart.</p> : null}
              </Panel>
            </section>

            {historyLoading ? <p className="text-sm text-slate-500">Refreshing trends...</p> : null}
          </main>
        ) : (
          <main className="space-y-3 sm:space-y-4">
            <section>
              <Panel title="Query Run History" subtitle="Full history of submitted questions, answers, and citations.">
                <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-4">
                  <label className="block text-xs font-semibold text-slate-600 md:col-span-2">
                    Search
                    <input
                      type="text"
                      value={historySearch}
                      onChange={(e) => setHistorySearch(e.target.value)}
                      placeholder="Question, answer, source, or citation text"
                      className="apple-input mt-1"
                    />
                  </label>
                  <label className="block text-xs font-semibold text-slate-600">
                    Citations
                    <select value={historyCitationFilter} onChange={(e) => setHistoryCitationFilter(e.target.value)} className="apple-input mt-1">
                      <option value="all">All</option>
                      <option value="with">With citations</option>
                      <option value="without">Without citations</option>
                    </select>
                  </label>
                  <label className="block text-xs font-semibold text-slate-600">
                    Time Window
                    <select value={historyWindowHours} onChange={(e) => setHistoryWindowHours(e.target.value)} className="apple-input mt-1">
                      <option value="all">All time</option>
                      <option value="24">Last 24h</option>
                      <option value="168">Last 7d</option>
                    </select>
                  </label>
                </div>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                  <span>
                    Showing <strong>{filteredQueryRuns.length}</strong> of <strong>{queryRuns.length}</strong> runs
                  </span>
                  {(historySearch || historyCitationFilter !== "all" || historyWindowHours !== "all") ? (
                    <button
                      type="button"
                      className="apple-chip"
                      onClick={() => {
                        setHistorySearch("");
                        setHistoryCitationFilter("all");
                        setHistoryWindowHours("all");
                      }}
                    >
                      Clear Filters
                    </button>
                  ) : null}
                </div>
                {queryRunsError ? <p className="mb-2 text-sm text-rose-700">History load failed: {queryRunsError}</p> : null}
                {queryRunsLoading ? <p className="text-sm text-slate-500">Loading query history...</p> : null}
                {!queryRunsLoading && queryRuns.length === 0 ? <p className="text-sm text-slate-500">No query runs recorded yet.</p> : null}
                {!queryRunsLoading && queryRuns.length > 0 && filteredQueryRuns.length === 0 ? (
                  <p className="text-sm text-slate-500">No runs match the selected filters.</p>
                ) : null}
                {filteredQueryRuns.length > 0 ? (
                  <ul className="space-y-3">
                    {filteredQueryRuns.map((run) => (
                      <li key={run.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                        <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full bg-blue-100 px-2 py-0.5 font-semibold text-blue-700">Run #{run.id}</span>
                            <span>{new Date(run.ts_utc).toLocaleString()}</span>
                            <span>Latency {Number(run.latency_ms).toFixed(1)} ms</span>
                            <span className="rounded-full bg-indigo-100 px-2 py-0.5 font-semibold text-indigo-700">Context {run.top_k ?? "--"}</span>
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-700">
                              Confidence {run.correctness_probability != null ? `${(Number(run.correctness_probability) * 100).toFixed(1)}%` : "--"}
                            </span>
                            <span className="rounded-full bg-slate-200 px-2 py-0.5 font-semibold text-slate-700">Model {run.chat_model || modelInfo?.chat_model || "--"}</span>
                          </div>
                          <button type="button" onClick={() => copyRunDetails(run)} className="apple-chip">
                            Copy
                          </button>
                        </div>
                        <p className="text-sm font-semibold text-slate-800">Q: {run.question}</p>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">A: {run.answer}</p>
                        <div className="mt-2">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <span className="text-xs font-semibold text-slate-700">Was this answer correct?</span>
                            <button
                              type="button"
                              onClick={() => submitRunFeedback(run.id, true)}
                              className={`apple-chip ${run.feedback_is_correct === true ? "ring-2 ring-emerald-300" : ""}`}
                            >
                              Correct
                            </button>
                            <button
                              type="button"
                              onClick={() => submitRunFeedback(run.id, false)}
                              className={`apple-chip ${run.feedback_is_correct === false ? "ring-2 ring-rose-300" : ""}`}
                            >
                              Incorrect
                            </button>
                            {typeof run.feedback_is_correct === "boolean" ? (
                              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${run.feedback_is_correct ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                                {run.feedback_is_correct ? "Marked Correct" : "Marked Incorrect"}
                              </span>
                            ) : null}
                          </div>
                          <p className="mb-1 text-xs font-semibold text-slate-700">Citations</p>
                          {Array.isArray(run.citations) && run.citations.length > 0 ? (
                            <ul className="space-y-1">
                              {run.citations.map((c, idx) => (
                                <li key={`${run.id}-${idx}`} className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-600">
                                  <span className="font-semibold text-slate-700">{c.source || c.doc_id || `Citation ${idx + 1}`}</span>
                                  {c.text_preview ? <span> | {String(c.text_preview).slice(0, 140)}...</span> : null}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-xs text-slate-500">No citations stored for this run.</p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </Panel>
            </section>
          </main>
        )}
      </div>
    </div>
  );
}
