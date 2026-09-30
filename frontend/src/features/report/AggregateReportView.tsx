import { useEffect, useState } from "react";
import {
  AggregateReport,
  AggregateTheme,
  AggregateThemeEvidence,
  getAggregateThemeEvidence,
  getMainReport,
  getTestReport,
} from "../../api/reports";
import StorefrontOverview from "../game/StorefrontOverview";
import { extendMainReport } from "../../api/shell";

interface AggregateReportViewProps {
  appId: number;
  kind?: "main" | "test";
}

export default function AggregateReportView(
  { appId, kind = "test" }: AggregateReportViewProps,
): JSX.Element {
  const [report, setReport] = useState<AggregateReport | null>(null);
  const [error, setError] = useState<string>("");
  const [openThemeId, setOpenThemeId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Record<string, AggregateThemeEvidence>>({});
  const [evidenceError, setEvidenceError] = useState<string>("");
  const [extensionState, setExtensionState] = useState<"idle" | "starting" | "started" | "failed">("idle");

  useEffect(() => {
    let active: boolean = true;
    (kind === "main" ? getMainReport(appId) : getTestReport(appId))
      .then((value) => { if (active) setReport(value); })
      .catch(() => { if (active) setError(`Unable to load this ${kind === "main" ? "Main" : "Test"} Report.`); });
    return () => { active = false; };
  }, [appId, kind]);

  if (error) return <main className="report-state"><p role="alert">{error}</p></main>;
  if (!report) return <main className="report-state"><p role="status">Loading report…</p></main>;

  function toggleEvidence(theme: AggregateTheme): void {
    if (openThemeId === theme.theme_id) {
      setOpenThemeId(null);
      return;
    }
    setOpenThemeId(theme.theme_id);
    setEvidenceError("");
    if (evidence[theme.theme_id]) return;
    getAggregateThemeEvidence(appId, theme.theme_id, kind)
      .then((value) => setEvidence((current) => ({ ...current, [theme.theme_id]: value })))
      .catch(() => setEvidenceError("Unable to load review evidence."));
  }

  function extendReport(): void {
    setExtensionState("starting");
    extendMainReport(appId)
      .then((run) => {
        window.localStorage.setItem("active-analysis-run", run.id);
        setExtensionState("started");
      })
      .catch(() => setExtensionState("failed"));
  }

  return (
    <main className="report-shell">
      <header className="report-header">
        <a className="back-link" href={`/?appid=${appId}`}>← Game catalog</a>
        <div>
          <p className="eyebrow">{kind === "main" ? "Main Report" : "Test Report"}</p>
          <h1>{report.game.title}</h1>
          <p className="report-subtitle">Steam AppID {report.game.app_id}</p>
        </div>
      </header>
      <section className="report-facts" aria-label="Report scope and provenance">
        <div className="report-review-count">
          <span>Reviews</span>
          <strong>{report.scope.review_count}</strong>
          {kind === "main" && (
            <button type="button" onClick={extendReport} disabled={extensionState !== "idle"}>
              {extensionState === "starting" ? "Startingâ€¦" : "Extend Report"}
            </button>
          )}
        </div>
        <div><span>Created</span><strong>{formatDate(report.created_at)}</strong></div>
        <div><span>Oldest cohort</span><strong>{report.scope.oldest_review_count}</strong></div>
        <div><span>Newest cohort</span><strong>{report.scope.newest_review_count}</strong></div>
        {report.scope.oversized_review_count > 0 && (
          <div><span>Oversized reviews skipped</span><strong>{report.scope.oversized_review_count}</strong></div>
        )}
        <div><span>Provider</span><strong>{report.provider} · {report.model}</strong></div>
      </section>
      {extensionState === "started" && <p role="status">Report extension started. You can return to the game catalog to follow progress.</p>}
      {extensionState === "failed" && <p className="error" role="alert">Unable to extend this report.</p>}
      {report.positive_themes.length === 0 && report.negative_themes.length === 0 ? (
        <section className="empty-report" role="status">
          <h2>No main Theme met the 5% threshold</h2>
        </section>
      ) : (
        <div className="theme-columns aggregate-theme-columns">
          <ThemeList
            title="Positive themes"
            themes={report.positive_themes}
            openThemeId={openThemeId}
            evidence={evidence}
            toggleEvidence={toggleEvidence}
          />
          <ThemeList
            title="Negative themes"
            themes={report.negative_themes}
            openThemeId={openThemeId}
            evidence={evidence}
            toggleEvidence={toggleEvidence}
          />
        </div>
      )}
      {evidenceError && <p className="error" role="alert">{evidenceError}</p>}
      {report.metadata.storefront_source_status !== "unavailable" && (
        <StorefrontOverview metadata={report.metadata} />
      )}
    </main>
  );
}

interface ThemeListProps {
  title: string;
  themes: AggregateTheme[];
  openThemeId: string | null;
  evidence: Record<string, AggregateThemeEvidence>;
  toggleEvidence: (theme: AggregateTheme) => void;
}

function ThemeList(
  { title, themes, openThemeId, evidence, toggleEvidence }: ThemeListProps,
): JSX.Element {
  return (
    <section className="theme-section">
      <div className="theme-section-heading"><h2>{title}</h2></div>
      {themes.length === 0 ? <p className="empty-themes">No qualifying Themes.</p> : (
        <ol className="theme-list">
          {themes.map((theme) => (
            <ThemeItem
              key={theme.theme_id}
              theme={theme}
              expanded={openThemeId === theme.theme_id}
              evidence={evidence[theme.theme_id]}
              toggleEvidence={toggleEvidence}
            />
          ))}
        </ol>
      )}
    </section>
  );
}

interface ThemeItemProps {
  theme: AggregateTheme;
  expanded: boolean;
  evidence: AggregateThemeEvidence | undefined;
  toggleEvidence: (theme: AggregateTheme) => void;
}

function ThemeItem(
  { theme, expanded, evidence, toggleEvidence }: ThemeItemProps,
): JSX.Element {
  const difference: string = theme.percentage_point_difference > 0
    ? `+${formatPercentage(theme.percentage_point_difference)}`
    : formatPercentage(theme.percentage_point_difference);
  return (
    <li className="aggregate-theme">
      <button
        type="button"
        className="aggregate-theme-toggle"
        aria-expanded={expanded}
        aria-label={`${expanded ? "Hide" : "Show"} review evidence for ${theme.title}`}
        onClick={() => toggleEvidence(theme)}
      >
        <h3>{theme.title}</h3>
        <span aria-hidden="true">{expanded ? "▴" : "▾"}</span>
      </button>
      <p>{theme.summary}</p>
      <strong>{theme.support_count} reviews · {formatPercentage(theme.total_support_percentage)}% total</strong>
      <small>
        Oldest {formatPercentage(theme.oldest_support_percentage)}% · Newest {formatPercentage(theme.newest_support_percentage)}% · {difference} percentage points
      </small>
      {expanded && (
        <section
          className="aggregate-theme-evidence"
          aria-label={`Review evidence for ${theme.title}`}
        >
          {!evidence ? <p role="status">Loading review evidence…</p> : evidence.reviews.map((review) => (
            <article key={review.review_revision_id}>
              <p>{review.text}</p>
              <small>
                {review.recommended ? "Recommended" : "Not recommended"} · {review.votes_helpful} helpful votes
              </small>
            </article>
          ))}
        </section>
      )}
    </li>
  );
}

function formatPercentage(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatDate(createdAt: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    new Date(`${createdAt.replace(" ", "T")}Z`),
  );
}
