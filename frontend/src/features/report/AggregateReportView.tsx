import { useEffect, useState } from "react";
import {
  AggregateReport,
  AggregateTheme,
  getMainReport,
  getTestReport,
} from "../../api/reports";
import StorefrontOverview from "../game/StorefrontOverview";
import { analysisFailureMessage, extendMainReport } from "../../api/shell";
import { deleteReport } from "../../api/storage";

interface AggregateReportViewProps {
  appId: number;
  kind?: "main" | "test";
}

export default function AggregateReportView(
  { appId, kind = "test" }: AggregateReportViewProps,
): JSX.Element {
  const [report, setReport] = useState<AggregateReport | null>(null);
  const [error, setError] = useState<string>("");
  const [extensionState, setExtensionState] = useState<"idle" | "starting" | "failed">("idle");
  const [extensionError, setExtensionError] = useState<string>("");
  const [deleteState, setDeleteState] = useState<"idle" | "deleting" | "failed">("idle");

  useEffect(() => {
    let active: boolean = true;
    (kind === "main" ? getMainReport(appId) : getTestReport(appId))
      .then((value) => { if (active) setReport(value); })
      .catch(() => { if (active) setError(`Unable to load this ${kind === "main" ? "Main" : "Test"} Report.`); });
    return () => { active = false; };
  }, [appId, kind]);

  if (error) return <main className="report-state"><p role="alert">{error}</p></main>;
  if (!report) return <main className="report-state"><p role="status">Loading report…</p></main>;
  const reportId: string = report.report_id;

  function extendReport(): void {
    setExtensionState("starting");
    setExtensionError("");
    extendMainReport(appId)
      .then((run) => {
        window.localStorage.setItem("active-analysis-run", run.id);
        const returnLink: HTMLAnchorElement = document.createElement("a");
        returnLink.href = `/?appid=${appId}`;
        returnLink.click();
      })
      .catch((error: unknown) => {
        setExtensionState("failed");
        setExtensionError(
          error instanceof Error
            ? analysisFailureMessage(error.message)
            : "Unable to extend this report.",
        );
      });
  }

  function removeReport(): void {
    setDeleteState("deleting");
    deleteReport(reportId, reportId)
      .then(() => {
        const returnLink: HTMLAnchorElement = document.createElement("a");
        returnLink.href = `/?appid=${appId}`;
        returnLink.click();
      })
      .catch(() => setDeleteState("failed"));
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
          <span>English Reviews</span>
          <p className="report-review-value">
            <strong>{report.scope.review_count}</strong>
            {kind === "main" && (
              <button type="button" onClick={extendReport} disabled={extensionState !== "idle"}>
                {extensionState === "starting"
                  ? "Starting..."
                  : `Extend Report${report.unseen_review_count === null
                    ? ""
                    : ` · ${report.unseen_review_count} unseen`}`}
              </button>
            )}
          </p>
        </div>
        <div><span>Created</span><strong>{formatDate(report.created_at)}</strong></div>
        <div><span>Oldest cohort</span><strong>{report.scope.oldest_review_count}</strong></div>
        <div><span>Newest cohort</span><strong>{report.scope.newest_review_count}</strong></div>
        {report.scope.oversized_review_count > 0 && (
          <div><span>Oversized reviews skipped</span><strong>{report.scope.oversized_review_count}</strong></div>
        )}
      </section>
      {extensionState === "failed" && <p className="error" role="alert">{extensionError}</p>}
      {report.positive_themes.length === 0 && report.negative_themes.length === 0 ? (
        <section className="empty-report" role="status">
          <h2>No main Theme met the 5% threshold</h2>
        </section>
      ) : (
        <div className="theme-columns aggregate-theme-columns">
          <ThemeList title="Positive themes" themes={report.positive_themes} />
          <ThemeList title="Negative themes" themes={report.negative_themes} />
        </div>
      )}
      {report.metadata.storefront_source_status !== "unavailable" && (
        <StorefrontOverview metadata={report.metadata} />
      )}
      <section className="report-delete" aria-label="Delete report">
        <button type="button" disabled={deleteState === "deleting"} onClick={removeReport}>
          {deleteState === "deleting" ? "Deleting..." : "Delete Report"}
        </button>
        {deleteState === "failed" && <p className="error" role="alert">Report deletion was rejected.</p>}
      </section>
    </main>
  );
}

interface ThemeListProps {
  title: string;
  themes: AggregateTheme[];
}

function ThemeList({ title, themes }: ThemeListProps): JSX.Element {
  return (
    <section className="theme-section">
      <div className="theme-section-heading"><h2>{title}</h2></div>
      {themes.length === 0 ? <p className="empty-themes">No qualifying Themes.</p> : (
        <ol className="theme-list">
          {themes.map((theme) => (
            <ThemeItem key={theme.theme_id} theme={theme} />
          ))}
        </ol>
      )}
    </section>
  );
}

interface ThemeItemProps {
  theme: AggregateTheme;
}

function ThemeItem({ theme }: ThemeItemProps): JSX.Element {
  const difference: string = theme.percentage_point_difference > 0
    ? `+${formatPercentage(theme.percentage_point_difference)}`
    : formatPercentage(theme.percentage_point_difference);
  return (
    <li className="aggregate-theme">
      <h3>{theme.title}</h3>
      <p>{theme.summary}</p>
      <strong>{theme.support_count} reviews · {formatPercentage(theme.total_support_percentage)}% total</strong>
      <small>
        Oldest {formatPercentage(theme.oldest_support_percentage)}% · Newest {formatPercentage(theme.newest_support_percentage)}% · {difference} percentage points
      </small>
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
