import { useEffect, useState } from "react";
import {
  AggregateReport,
  AggregateTheme,
  getTestReport,
} from "../../api/reports";
import StorefrontOverview from "../game/StorefrontOverview";

interface AggregateReportViewProps {
  appId: number;
}

export default function AggregateReportView(
  { appId }: AggregateReportViewProps,
): JSX.Element {
  const [report, setReport] = useState<AggregateReport | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let active: boolean = true;
    getTestReport(appId)
      .then((value) => { if (active) setReport(value); })
      .catch(() => { if (active) setError("Unable to load this Test Report."); });
    return () => { active = false; };
  }, [appId]);

  if (error) return <main className="report-state"><p role="alert">{error}</p></main>;
  if (!report) return <main className="report-state"><p role="status">Loading report…</p></main>;

  return (
    <main className="report-shell">
      <header className="report-header">
        <a className="back-link" href={`/?appid=${appId}`}>← Game catalog</a>
        <div>
          <p className="eyebrow">Test Report</p>
          <h1>{report.game.title}</h1>
          <p className="report-subtitle">Steam AppID {report.game.app_id}</p>
        </div>
      </header>
      <section className="report-facts" aria-label="Report scope and provenance">
        <div><span>Reviews</span><strong>{report.scope.review_count}</strong></div>
        <div><span>Oldest cohort</span><strong>{report.scope.oldest_review_count}</strong></div>
        <div><span>Newest cohort</span><strong>{report.scope.newest_review_count}</strong></div>
        <div><span>Provider</span><strong>{report.provider} · {report.model}</strong></div>
      </section>
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
    </main>
  );
}

function ThemeList(
  { title, themes }: { title: string; themes: AggregateTheme[] },
): JSX.Element {
  return (
    <section className="theme-section">
      <div className="theme-section-heading"><h2>{title}</h2></div>
      {themes.length === 0 ? <p className="empty-themes">No qualifying Themes.</p> : (
        <ol className="theme-list">
          {themes.map((theme) => <ThemeItem key={theme.theme_id} theme={theme} />)}
        </ol>
      )}
    </section>
  );
}

function ThemeItem({ theme }: { theme: AggregateTheme }): JSX.Element {
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
