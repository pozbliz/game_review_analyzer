import { useEffect, useState } from "react";
import {
  getReport,
  getReportHistory,
  getThemeEvidence,
  MixedReception,
  ReportSummary,
  ReportHistoryEntry,
  ReportTheme,
  ThemeEvidence,
} from "../../api/reports";
import {
  AnalysisJob,
  cancelJob,
  getJob,
  retryJob,
  startFullImport,
  startReconciliation,
  startRefresh,
} from "../../api/shell";
import StorageControls from "../storage/StorageControls";

interface ReportViewProps {
  reportId: string;
}

export default function ReportView({ reportId }: ReportViewProps): JSX.Element {
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [error, setError] = useState<string>("");
  const [openThemeId, setOpenThemeId] = useState<string | null>(null);
  const [category, setCategory] = useState<string>("All categories");
  const [evidence, setEvidence] = useState<Record<string, ThemeEvidence>>({});
  const [evidenceLoading, setEvidenceLoading] = useState<string | null>(null);
  const [history, setHistory] = useState<ReportHistoryEntry[]>([]);
  const [refreshJob, setRefreshJob] = useState<AnalysisJob | null>(null);
  const [refreshError, setRefreshError] = useState<string>("");

  useEffect(() => {
    let active: boolean = true;
    getReport(reportId)
      .then((value) => {
        if (!active) return;
        setReport(value);
        void getReportHistory(value.game.app_id)
          .then((items) => { if (active) setHistory(items); })
          .catch(() => { if (active) setRefreshError("Unable to load report history."); });
      })
      .catch(() => {
        if (active) setError("Unable to load this report.");
      });
    return () => { active = false; };
  }, [reportId]);

  useEffect(() => {
    if (!refreshJob || !["queued", "running"].includes(refreshJob.state)) return;
    let active: boolean = true;
    const refresh = (): void => {
      getJob(refreshJob.id)
        .then((job) => { if (active) setRefreshJob(job); })
        .catch(() => { if (active) setRefreshError("Unable to refresh progress."); });
    };
    refresh();
    const timer: number = window.setInterval(refresh, 500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [refreshJob?.id, refreshJob?.state]);

  const allThemes: ReportTheme[] = report
    ? [...report.positive_themes, ...report.negative_themes, ...report.technical_themes]
    : [];
  const categories: string[] = [
    ...new Set(allThemes.map((theme) => theme.primary_category)),
  ].sort();
  const themeById: Map<string, ReportTheme> = new Map(
    allThemes.map((theme) => [theme.theme_id, theme]),
  );

  if (error) return <main className="report-state"><p role="alert">{error}</p></main>;
  if (!report) return <main className="report-state"><p role="status">Loading report…</p></main>;
  const appId: number = report.game.app_id;

  const visible = (themes: ReportTheme[]): ReportTheme[] => category === "All categories"
    ? themes
    : themes.filter((theme) => theme.primary_category === category);

  async function revealEvidence(theme: ReportTheme): Promise<void> {
    if (evidence[theme.theme_id]) return;
    setEvidenceLoading(theme.theme_id);
    try {
      const result: ThemeEvidence = await getThemeEvidence(reportId, theme.theme_id);
      setEvidence((current) => ({ ...current, [theme.theme_id]: result }));
    } catch {
      setError("Unable to load complete evidence.");
    } finally {
      setEvidenceLoading(null);
    }
  }

  function beginRefresh(): void {
    setRefreshError("");
    startRefresh(appId, 5000)
      .then(setRefreshJob)
      .catch(() => setRefreshError("Unable to start refresh."));
  }

  function retryRefresh(): void {
    if (!refreshJob) return;
    setRefreshError("");
    retryJob(refreshJob.id)
      .then(setRefreshJob)
      .catch(() => setRefreshError("Unable to retry refresh."));
  }

  function cancelRefresh(): void {
    if (!refreshJob) return;
    cancelJob(refreshJob.id)
      .then(setRefreshJob)
      .catch(() => setRefreshError("Unable to cancel refresh."));
  }

  function beginFullImport(): void {
    setRefreshError("");
    startFullImport(appId)
      .then(setRefreshJob)
      .catch(() => setRefreshError("Unable to start Full import."));
  }

  function beginReconciliation(): void {
    setRefreshError("");
    startReconciliation(appId)
      .then(setRefreshJob)
      .catch(() => setRefreshError("Unable to start reconciliation."));
  }

  const activeJob: boolean = Boolean(
    refreshJob && ["queued", "running"].includes(refreshJob.state),
  );
  const jobLabel: string = refreshJob?.scope === "full"
    ? "Full import"
    : refreshJob?.scope === "reconciliation"
      ? "Reconciliation"
      : "Refresh";

  const sharedThemeProps: SharedThemeProps = {
    report,
    openThemeId,
    setOpenThemeId,
    themeById,
    evidence,
    evidenceLoading,
    revealEvidence,
  };

  return (
    <main className="report-shell">
      <header className="report-header">
        <a className="back-link" href="/">← Game catalog</a>
        <div>
          <p className="eyebrow">RESEARCH REPORT</p>
          <h1>{report.game.title}</h1>
          <p className="report-subtitle">Steam AppID {report.game.app_id} · Report {report.report_version_id}</p>
        </div>
        <div className="report-actions">
          <span className={`calibration ${report.scope.thresholds_calibrated ? "calibrated" : "provisional"}`}>
            {report.scope.thresholds_calibrated ? "Calibrated thresholds" : "Provisional thresholds"}
          </span>
          <details className="report-history">
            <summary>Report history ({history.length})</summary>
            <ul>
              {history.map((entry) => (
                <li key={entry.report_version_id}>
                  <a
                    href={`/reports/${encodeURIComponent(entry.report_version_id)}`}
                    aria-current={entry.report_version_id === report.report_version_id ? "page" : undefined}
                  >
                    {entry.report_version_id} · {entry.review_count.toLocaleString()} reviews
                  </a>
                </li>
              ))}
            </ul>
          </details>
          <button type="button" className="refresh-button" onClick={beginRefresh}>
            Refresh reviews
          </button>
          <details className="dataset-maintenance">
            <summary>Dataset maintenance</summary>
            <p>Full import scans every eligible review and may take a long time. Reconciliation scans the current corpus only to record reviews Steam no longer returns.</p>
            <button type="button" disabled={activeJob} onClick={beginFullImport}>Start Full import</button>
            <button type="button" disabled={activeJob} onClick={beginReconciliation}>Reconcile deleted reviews</button>
          </details>
        </div>
      </header>

      {(refreshJob || refreshError) && (
        <section className="refresh-status" aria-live="polite">
          {refreshError && <p role="alert">{refreshError}</p>}
          {refreshJob?.state === "failed" && (
            <><p>{jobLabel} failed. Existing reports are unchanged.</p><button type="button" onClick={retryRefresh}>Retry {jobLabel.toLowerCase()}</button></>
          )}
          {refreshJob?.state === "cancelled" && (
            <><p>{jobLabel} cancelled. Existing reports are unchanged.</p><button type="button" onClick={retryRefresh}>Retry {jobLabel.toLowerCase()}</button></>
          )}
          {["queued", "running"].includes(refreshJob?.state ?? "") && (
            <><p>{jobLabel} in progress…</p><button type="button" onClick={cancelRefresh}>Cancel {jobLabel.toLowerCase()}</button></>
          )}
          {refreshJob?.state === "completed" && refreshJob.scope === "refresh" && <p>Reviews refreshed. Create a report to analyze the latest corpus.</p>}
          {refreshJob?.state === "completed" && refreshJob.scope === "full" && <p>Full import complete. Create a report to analyze the complete corpus.</p>}
          {refreshJob?.state === "completed" && refreshJob.scope === "reconciliation" && <p>Reconciliation complete. Missing reviews were recorded without deleting historical evidence.</p>}
        </section>
      )}

      <section className="report-facts" aria-label="Report scope and provenance">
        <div><span>Review scope</span><strong>{report.scope.review_count.toLocaleString()} reviews</strong></div>
        <div><span>Provider</span><strong>{report.provenance.provider}</strong></div>
        <div><span>Model</span><strong>{report.provenance.model}</strong></div>
        <div><span>Scope digest</span><code title={report.provenance.scope_sha256}>{report.provenance.scope_sha256.slice(0, 12)}…</code></div>
      </section>

      <div className="report-toolbar">
        <div>
          <p className="eyebrow">THEME EXPLORER</p>
          <h2>What players consistently mention</h2>
        </div>
        <label>
          Category
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option>All categories</option>
            {categories.map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
      </div>

      <div className="theme-columns">
        <ThemeSection
          heading="Positive themes"
          symbol="+"
          themes={visible(report.positive_themes)}
          {...sharedThemeProps}
        />
        <ThemeSection
          heading="Negative themes"
          symbol="−"
          themes={visible(report.negative_themes)}
          {...sharedThemeProps}
        />
      </div>

      <ThemeSection
        heading="Technical themes"
        symbol="!"
        themes={visible(report.technical_themes)}
        technical
        {...sharedThemeProps}
      />

      <StorageControls
        appId={appId}
        reportId={report.report_version_id}
        incompleteJobId={refreshJob && ["failed", "cancelled"].includes(refreshJob.state) ? refreshJob.id : undefined}
      />
    </main>
  );
}

interface SharedThemeProps {
  report: ReportSummary;
  openThemeId: string | null;
  setOpenThemeId: (themeId: string | null) => void;
  themeById: Map<string, ReportTheme>;
  evidence: Record<string, ThemeEvidence>;
  evidenceLoading: string | null;
  revealEvidence: (theme: ReportTheme) => Promise<void>;
}

interface ThemeSectionProps extends SharedThemeProps {
  heading: string;
  symbol: string;
  themes: ReportTheme[];
  technical?: boolean;
}

function ThemeSection({ heading, symbol, themes, technical = false, ...shared }: ThemeSectionProps): JSX.Element {
  return (
    <section className={`theme-section${technical ? " technical-section" : ""}`}>
      <div className="theme-section-heading">
        <span aria-hidden="true">{symbol}</span>
        <h2>{heading}</h2>
        <small>{themes.length}</small>
      </div>
      {themes.length === 0 ? <p className="empty-themes">No Themes in this category.</p> : (
        <ol className="theme-list">
          {themes.map((theme, index) => (
            <li key={theme.theme_id}>
              <ThemeRow theme={theme} rank={index + 1} {...shared} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

interface ThemeRowProps extends SharedThemeProps {
  theme: ReportTheme;
  rank: number;
}

function ThemeRow({
  theme, rank, report, openThemeId, setOpenThemeId, themeById,
  evidence, evidenceLoading, revealEvidence,
}: ThemeRowProps): JSX.Element {
  const expanded: boolean = openThemeId === theme.theme_id;
  const detailId: string = `theme-${theme.theme_id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const mixed: MixedReception | undefined = report.mixed_reception.find(
    (item) => item.positive_theme_id === theme.theme_id || item.negative_theme_id === theme.theme_id,
  );
  const opposing: ReportTheme | undefined = theme.opposes_theme_id
    ? themeById.get(theme.opposes_theme_id)
    : undefined;
  const completeEvidence: ThemeEvidence | undefined = evidence[theme.theme_id];
  return (
    <article className={`theme-row polarity-${theme.polarity}`}>
      <button
        type="button"
        className="theme-toggle"
        aria-expanded={expanded}
        aria-controls={detailId}
        onClick={() => setOpenThemeId(expanded ? null : theme.theme_id)}
      >
        <span className="theme-rank" aria-label={`Rank ${rank}`}>{String(rank).padStart(2, "0")}</span>
        <span className="theme-title"><strong>{theme.title}</strong><small>{theme.primary_category}</small></span>
        <span className="theme-support">
          <strong>{formatPercent(theme.support.percentage)}</strong>
          <small>{theme.support.count} reviews · {formatPercent(theme.support.percentage)} of {theme.support.denominator}</small>
        </span>
        <span className="chevron" aria-hidden="true">⌄</span>
      </button>
      {expanded && (
        <div className="theme-detail" id={detailId}>
          <p>{theme.summary}</p>
          {theme.related_categories.length > 0 && (
            <p className="related-categories">Also relates to {theme.related_categories.join(", ")}</p>
          )}
          {mixed && (
            <div className="mixed-reception">
              <strong>Mixed reception</strong>
              <span>{mixed.liked_count} liked · {mixed.disliked_count} disliked · {mixed.mixed_count} mixed</span>
              <span>Mentioned by {formatPercent(mixed.mentioned_percentage)} ({mixed.mentioned_review_count}/{mixed.scope_review_count})</span>
              {opposing && (
                <button type="button" onClick={() => setOpenThemeId(opposing.theme_id)}>
                  View opposing: {opposing.title}
                </button>
              )}
            </div>
          )}
          <div className="representative-evidence">
            <h3>Representative evidence</h3>
            {theme.representative_evidence.map((item) => (
              <blockquote key={item.opinion_point_id}>“{item.excerpt}”</blockquote>
            ))}
          </div>
          <button
            type="button"
            className="evidence-button"
            disabled={evidenceLoading === theme.theme_id}
            onClick={() => void revealEvidence(theme)}
          >
            {evidenceLoading === theme.theme_id ? "Loading evidence…" : `View all ${theme.evidence_count} evidence`}
          </button>
          {completeEvidence && (
            <div className="complete-evidence" aria-live="polite">
              <h3>Complete evidence</h3>
              {completeEvidence.items.map((item) => (
                <article className="review-evidence" key={item.opinion_point_id}>
                  <p className="review-context">
                    {item.review.recommended ? "Recommended" : "Not recommended"} · {formatHours(item.review.playtime_at_review_minutes)} at review · {item.review.votes_helpful} helpful votes
                  </p>
                  <strong>“{item.excerpt}”</strong>
                  <p>{item.review.text}</p>
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function formatPercent(value: number): string {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}%`;
}

function formatHours(minutes: number): string {
  const hours: number = minutes / 60;
  return `${Number.isInteger(hours) ? hours : hours.toFixed(1)}h`;
}
