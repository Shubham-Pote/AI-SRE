import { useEffect, useRef, useState } from "react";
import AnimatedContent from "./components/react-bits/AnimatedContent";
import SplitText from "./components/react-bits/SplitText";
import SpotlightCard from "./components/react-bits/SpotlightCard";
import { Button } from "./components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Activity, ArrowUpRight, ChevronRight, CircleAlert, FlaskConical, Gauge, Layers, RefreshCw, ShieldCheck, X } from "lucide-react";
import { api, type Status, type Telemetry, type Incident, type IncidentDetail, type Fault, type Mode } from "./heallab-api";
import "./index.css";
import { LiveValue } from "./components/LiveValue";


const title = (s: string) => s.replaceAll("_", " ").replace(/\b\w/g, c => c.toUpperCase());
const date = (n: number) => new Date(n * 1000).toLocaleString();
const faults: Record<Fault, string> = { errors: "Return HTTP 500 from work requests while probes remain healthy.", memory: "Grow memory gradually. Pod replacement may only provide temporary relief.", cpu: "Add CPU work to requests. Diagnosis depends on sustained load.", none: "Restore the normal revision and two desired replicas." };

function Chart({ rows, field }: { rows: Telemetry[]; field: "latency" | "memory" }) {
  const values = rows.map(r => r[field]).filter(Number.isFinite);
  const max = Math.max(...values, 0.001) * 1.15;
  const points = values.map((v, i) => `${i / Math.max(values.length - 1, 1) * 600},${140 - v / max * 125}`).join(" ");
  return values.length < 2 ? <div className="chart-empty">Waiting for observations</div> : <svg viewBox="0 0 600 150" preserveAspectRatio="none" role="img" aria-label={`${title(field)} over the latest ${values.length} observations`}><path d="M0 145 H600 M0 75 H600" stroke="#e7e8e3" fill="none"/><polygon points={`0,150 ${points} 600,150`} fill="currentColor" opacity=".08"/><polyline points={points} stroke="currentColor" strokeWidth="2.5" fill="none" vectorEffect="non-scaling-stroke"/></svg>;
}

function Badge({ value }: { value: string }) { return <span className={`badge ${value}`}><i/>{title(value)}</span>; }

export function App() {
  const [page, setPage] = useState(location.hash.slice(1) || "overview");
  const [status, setStatus] = useState<Status | null>(null);
  const [rows, setRows] = useState<Telemetry[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [detail, setDetail] = useState<IncidentDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState("all");
  const [fault, setFault] = useState<Fault>("errors");
  const [lastExperiment, setLastExperiment] = useState("");
  const [pending, setPending] = useState<{ kind: "mode" | "fault"; value: Mode | Fault } | null>(null);
  const [busy, setBusy] = useState(false);
  const shell = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const drawer = useRef<HTMLDialogElement>(null);
  const latestRequest = useRef(0);
  const detailRequest = useRef(0);

  async function refresh(signal?: AbortSignal) {
    const request = ++latestRequest.current;
    try {
      const [s, h, i, e] = await Promise.all([api.status(signal), api.history(signal), api.incidents(signal), api.experiment(signal)]);
      if (signal?.aborted || request !== latestRequest.current) return;
      setStatus(s); setRows(h); setIncidents(i); setError("");
      setLastExperiment(e.fault ? `${title(e.fault)} · ${date(e.timestamp!)}` : "No experiment recorded through the API.");
    } catch (e) { if (!signal?.aborted && request === latestRequest.current) setError(e instanceof Error ? e.message : "Connection failed"); }
    finally { if (!signal?.aborted) setLoading(false); }
  }
  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    const timer = setInterval(() => { if (!document.hidden) void refresh(controller.signal); }, 5000);
    const hash = () => setPage(location.hash.slice(1) || "overview");
    window.addEventListener("hashchange", hash);
    return () => { controller.abort(); clearInterval(timer); window.removeEventListener("hashchange", hash); };
  }, []);
  useEffect(() => { if (pending) dialog.current?.showModal(); else dialog.current?.close(); }, [pending]);
  useEffect(() => { if (detail) drawer.current?.showModal(); else drawer.current?.close(); }, [detail]);
  useEffect(() => { content.current?.scrollTo({ top: 0 }); }, [page]);

  async function apply() {
    if (!pending) return;
    setBusy(true);
    try {
      if (pending.kind === "mode") await api.setMode(pending.value as Mode);
      else await api.setFault(pending.value as Fault);
      setNotice(pending.kind === "mode" ? "Recovery mode updated. Existing verification continues." : "Demo experiment applied. Watch the incident timeline for its outcome.");
      setPending(null); await refresh();
    } catch (e) { setNotice(e instanceof Error ? e.message : "Action failed"); setPending(null); }
    finally { setBusy(false); }
  }
  async function openIncident(id: number) {
    const request = ++detailRequest.current;
    try { const result = await api.incident(id); if (request === detailRequest.current) setDetail(result); }
    catch { setNotice("Unable to load this incident. Please retry."); }
  }
  const w = status?.telemetry ?? {};
  const online = !!status && !error;
  const healthy = online && !status?.stale && !status?.worker_error && w.rollout_complete && (w.rps ?? 0) > 0 && (w.ready ?? 0) >= 2 && (w.errors ?? 1) < .02 && (w.latency ?? 1) < .4 && (w.memory ?? Infinity) / (w.memory_limit ?? 268435456) < .8;
  const number = (v?: number, digits = 1) => typeof v === "number" ? v.toFixed(digits) : "—";
  const metric = [
    ["Requests / sec", number(w.rps), "Actual work traffic"], ["Error rate", w.errors == null ? "—" : `${(w.errors * 100).toFixed(1)}%`, "Last minute"],
    ["P95 latency", w.latency == null ? "—" : `${Math.round(w.latency * 1000)} ms`, "Last minute"], ["Ready replicas", `${w.ready ?? "—"} / ${w.replicas ?? "—"}`, "Desired capacity"],
    ["Memory", w.memory == null ? "—" : `${Math.round(w.memory / 1048576)} MiB`, "Highest pod usage"], ["CPU cores", number(w.cpu, 3), "Highest pod usage"],
  ];
  function incidentList(list: Incident[]) {
    return list.length ? list.map(i => <Button variant="ghost" className="incident-row" key={i.id} onClick={() => void openIncident(i.id)}><span className="incident-id">#{String(i.id).padStart(3, "0")}</span><span className="incident-name"><strong>{title(i.payload.cause)}</strong><small>{i.payload.evidence}</small></span><span className="incident-action">{title(i.payload.action)}</span><Badge value={i.status}/><ChevronRight size={16}/></Button>) : <div className="empty"><Layers size={26}/><h3>No incidents to show</h3><p>Detected conditions and recovery outcomes will appear here.</p></div>;
  }

  return <div className="app-shell" ref={shell}>
    <aside className="sidebar"><a className="brand" href="#overview"><span className="brand-mark"><Activity size={22}/></span><span>heal<span className="brand-light">lab</span><small>CONTROL ROOM</small></span></a><span className="nav-label">WORKSPACE</span><nav aria-label="Main navigation">{[["overview", Gauge], ["incidents", Layers], ["experiments", FlaskConical]].map(([name, Icon]) => { const label = name as string; const Symbol = Icon as typeof Gauge; return <a key={label} href={`#${label}`} className={page === label ? "nav-link active" : "nav-link"} aria-current={page === label ? "page" : undefined}><Symbol size={18}/>{title(label)}</a>; })}</nav><div className="sidebar-bottom"><div className="environment"><span>ENVIRONMENT</span><strong>Local laboratory</strong><small><i/>kind-heal-lab · heal-demo</small></div><a href="http://localhost:3000/d/heallab" target="_blank" rel="noreferrer">Open Grafana <ArrowUpRight size={16}/></a><a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API reference <ArrowUpRight size={16}/></a><small className="sidebar-caption">HEALLAB / LOCAL PROTOTYPE</small></div></aside>
    <main><header className="topbar"><div>Workspace <ChevronRight size={14}/><strong>{title(page)}</strong></div><div><span className={`connection ${online ? "connected" : ""}`}><i/>{online ? "API connected" : loading ? "Connecting" : "API offline"}</span><Button variant="ghost" className="icon-button" aria-label="Refresh data" onClick={() => void refresh()}><RefreshCw size={16}/></Button></div></header><div className="content" ref={content} tabIndex={0} role="region" aria-label="Workspace content"><AnimatedContent key={page} trigger="mount" distance={12} duration={0.45} className="page-content">
      {error && <div className="alert" role="alert"><CircleAlert size={19}/><span><strong>Control plane unavailable.</strong> {error} Existing readings may be old.</span><Button variant="ghost" onClick={() => void refresh()}>Retry</Button></div>}
      {notice && <div className="notice" role="status"><span>{notice}</span><Button variant="ghost" className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice("")}><X size={17}/></Button></div>}
      <div className="page-heading"><div><div className="eyebrow">{page === "overview" ? "LIVE OPERATIONS" : page === "incidents" ? "DECISIONS & OUTCOMES" : "CONTROLLED LABORATORY"}<span/>KIND-HEAL-LAB</div><SplitText key={page} tag="h1" text={`${page === "overview" ? "System overview" : title(page)}.`} trigger="load" effect="rise" mask splitType="chars" delay={24} duration={0.7} textAlign="left" className="workspace-title" /><p>{page === "overview" ? "Every signal, decision, and recovery. One clear view." : page === "incidents" ? "Follow the evidence from detection to verified recovery." : "Introduce a known fault. Understand how the system responds."}</p></div>{page === "overview" && <a className="button secondary" href="#incidents">View incidents <ArrowUpRight size={16}/></a>}</div>
      {page === "overview" && <>
        <SpotlightCard theme="dark" spotlightColor="#b4a6ff" spotlightSize={360} intensity={0.3} borderGlow={0.85} className={`health-panel ${healthy ? "healthy" : ""}`}><div className="health-main"><span className="health-symbol">{healthy ? <ShieldCheck size={27}/> : <Activity size={27}/>}</span><div><span className="eyebrow">WORKLOAD STATE</span><h2>{loading ? "Connecting to the control plane" : !online ? "Waiting for live observations" : status?.stale ? "Telemetry is stale" : healthy ? "The workload is healthy" : "Workload needs attention"}</h2><p>{!online ? "Start the API service to see your workload’s live state." : status?.worker_error || (healthy ? "Real traffic is flowing through ready replicas." : "Review the signals and recent decisions below.")}</p></div></div><div className="health-mode"><span>RECOVERY MODE</span><strong>{status?.mode === "automatic" ? "Automatic" : "Observe only"}</strong><a href="#experiments">Manage mode <ChevronRight size={14}/></a></div></SpotlightCard>
        <div className="section-heading"><div><span className="eyebrow">01 / SIGNALS</span><h2>What the system sees</h2></div><span className="subtle">{w.timestamp ? `Observed ${new Date(w.timestamp * 1000).toLocaleTimeString()}` : "Awaiting first observation"}</span></div><div className="metrics">{metric.map(([label, value, note]) => <div className="metric" key={label}><span>{label}</span><strong><LiveValue value={value ?? "—"}/></strong><small>{note}</small></div>)}</div>
        <div className="charts">{(["latency", "memory"] as const).map(field => <section className={`panel chart ${field}`} key={field}><div className="panel-heading"><div><span className="eyebrow">{field === "latency" ? "PERFORMANCE" : "RESOURCES"}</span><h3>{field === "latency" ? "Request latency" : "Resident memory"}</h3></div><span>{field === "latency" ? "P95" : "MAX POD"}</span></div><Chart rows={rows} field={field}/><div className="chart-axis"><span>OLDER</span><span>RECENT OBSERVATIONS</span></div></section>)}</div>
        <div className="bottom-grid"><SpotlightCard theme="light" spotlightColor="#a78bfa" intensity={0.65} className="panel readiness"><div className="panel-heading"><div><span className="eyebrow">DECISION SUPPORT</span><h3>Recovery readiness</h3></div><ShieldCheck size={20}/></div>{[["Rollback baseline", status?.baseline_ready ? "Available" : "Establishing"], ["Anomaly model", w.model_error ? "Unavailable" : w.model_version ? `v${w.model_version}` : "Not trained"], ["Anomaly signal", w.model_version ? w.anomaly ? "Detected" : "None" : "Unavailable"], ["Memory limit estimate", w.forecast_seconds == null ? "No stable trend" : `${Math.round(w.forecast_seconds)} seconds`]].map(([label, value]) => <div className="fact-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}<p className="footnote">Model scores alone never authorize recovery.</p></SpotlightCard><section className="panel recent"><div className="panel-heading"><div><span className="eyebrow">INCIDENT ACTIVITY</span><h3>Recent decisions</h3></div><a href="#incidents" className="text-link">View all <ArrowUpRight size={15}/></a></div>{incidentList(incidents.slice(0, 3))}</section></div>
      </>}
      {page === "incidents" && <><div className="section-heading"><div><span className="eyebrow">02 / TIMELINE</span><h2>{incidents.length} recorded incidents</h2></div><Select value={filter} onValueChange={setFilter}><SelectTrigger className="incident-filter" aria-label="Filter incidents"><SelectValue /></SelectTrigger><SelectContent>{["all", "resolved", "escalated", "observed", "verifying", "executing", "detected"].map(s => <SelectItem key={s} value={s}>{s === "all" ? "All statuses" : title(s)}</SelectItem>)}</SelectContent></Select></div><section className="panel incident-table">{incidentList(filter === "all" ? incidents : incidents.filter(i => i.status === filter))}</section><p className="footnote">The latest 200 incidents are shown. Older records remain in local storage.</p></>}
      {page === "experiments" && <><div className="experiment-grid"><section className="panel experiment-panel"><span className="eyebrow">03 / RECOVERY</span><h2>Recovery mode</h2><p>Choose whether the worker may act on a supported diagnosis.</p><div className="mode-display"><ShieldCheck size={25}/><div><small>CURRENT MODE</small><strong>{status?.mode === "automatic" ? "Automatic recovery" : "Observe only"}</strong></div></div><Button variant="ghost" className="button primary full" disabled={!online || busy} onClick={() => setPending({ kind: "mode", value: status?.mode === "automatic" ? "observe" : "automatic" })}>{status?.mode === "automatic" ? "Stop new recovery actions" : "Enable automatic recovery"}</Button><p className="footnote">Observation and verification continue when new actions are stopped.</p><div className="policy-notes"><span>Action boundaries</span><p>One attempt per incident</p><p>Five-minute cooldown</p><p>Maximum three replicas</p><p>Three healthy observations to resolve</p></div></section><section className="panel experiment-panel"><span className="eyebrow">04 / FAULT INJECTION</span><h2>Demo workload</h2><p>Changes are limited to the isolated heal-demo workload.</p><fieldset className="faults"><legend className="sr-only">Select a demo fault</legend>{(Object.keys(faults) as Fault[]).map(f => <label key={f} className={fault === f ? "selected" : ""}><input type="radio" name="fault" checked={fault === f} onChange={() => setFault(f)}/><span><strong>{f === "none" ? "Restore baseline" : f === "errors" ? "Faulty revision" : title(f)}</strong><small>{faults[f]}</small></span></label>)}</fieldset><Button variant="ghost" className="button primary full" disabled={!online || busy} onClick={() => setPending({ kind: "fault", value: fault })}><FlaskConical size={17}/>{fault === "none" ? "Restore baseline" : "Apply selected fault"}</Button></section></div><div className="experiment-note"><div><span className="eyebrow">LAST API EXPERIMENT</span><p>{lastExperiment || "No experiment recorded."}</p></div><a href="#incidents" className="button secondary">Review outcomes <ArrowUpRight size={16}/></a></div></>}
    </AnimatedContent></div></main>
    <dialog aria-label="Confirm action" ref={dialog} onCancel={e => { if (busy) e.preventDefault(); else setPending(null); }} className="confirm-dialog"><span className="dialog-symbol"><ShieldCheck size={25}/></span><h2>{pending?.kind === "mode" ? "Change recovery mode?" : "Apply this experiment?"}</h2><p>{pending?.kind === "mode" ? `Set the worker to ${pending.value === "automatic" ? "automatic recovery. Supported actions may run after safety checks pass" : "observe only. Pending verification will continue"}.` : pending ? faults[pending.value as Fault] : ""}</p><div className="dialog-actions"><Button variant="ghost" className="button secondary" disabled={busy} onClick={() => setPending(null)}>Cancel</Button><Button variant="ghost" className="button primary" disabled={busy} onClick={() => void apply()}>{busy ? "Applying…" : "Confirm action"}</Button></div></dialog>
    <dialog aria-label="Incident details" ref={drawer} className="detail-dialog" onCancel={() => setDetail(null)}><div className="detail-top"><span className="eyebrow">INCIDENT #{detail?.id}</span><Button variant="ghost" className="icon-button" aria-label="Close incident" onClick={() => setDetail(null)}><X size={20}/></Button></div>{detail && <><Badge value={detail.status}/><h2>{title(detail.payload.cause)}</h2><p>{detail.payload.evidence}</p><div className="detail-facts"><span>Proposed action<strong>{title(detail.payload.action)}</strong></span><span>Detected<strong>{date(detail.created)}</strong></span><span>Workload<strong>{detail.payload.namespace ?? "heal-demo"} / {detail.payload.workload ?? "demo"}</strong></span></div><h3>Event timeline</h3><ol className="events">{detail.events.map(e => <li key={e.id}><small>{date(e.time)}</small><strong>{title(e.kind)}</strong><p>{Object.entries(e.payload).map(([key, value]) => `${title(key)}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`).join(" · ")}</p></li>)}</ol>{!detail.events.length && <p>No events recorded yet.</p>}<Button variant="ghost" className="button secondary" onClick={() => void openIncident(detail.id)}>Refresh incident <RefreshCw size={15}/></Button></>}</dialog>
  </div>;
}
