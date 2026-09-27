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
  ThemeCohortComparison,
} from "../../api/reports";
import StorageControls from "../storage/StorageControls";
import StorefrontOverview from "../game/StorefrontOverview";

interface ReportViewProps {
  reportId: string;
}

interface EvidenceFilterDraft {
  recommendation: string;
  steamPurchase: string;
  receivedForFree: string;
  earlyAccess: string;
  playtimeBasis: string;
  minimumHours: string;
  maximumHours: string;
  reviewCreatedFrom: string;
  reviewCreatedTo: string;
}

const EMPTY_FILTER: EvidenceFilterDraft = {
  recommendation: "all",
  steamPurchase: "",
  receivedForFree: "",
  earlyAccess: "",
  playtimeBasis: "at_review",
  minimumHours: "",
  maximumHours: "",
  reviewCreatedFrom: "",
  reviewCreatedTo: "",
};

export default function ReportView({ reportId }: ReportViewProps): JSX.Element {
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [error, setError] = useState<string>("");
  const [openThemeId, setOpenThemeId] = useState<string | null>(null);
  const [category, setCategory] = useState<string>("All categories");
  const [evidence, setEvidence] = useState<Record<string, ThemeEvidence>>({});
  const [evidenceLoading, setEvidenceLoading] = useState<string | null>(null);
  const [history, setHistory] = useState<ReportHistoryEntry[]>([]);
  const [historyError, setHistoryError] = useState<string>("");
  const [filterDraft, setFilterDraft] = useState<EvidenceFilterDraft>(EMPTY_FILTER);
  const [filterQuery, setFilterQuery] = useState<string>("");
  const [filterError, setFilterError] = useState<string>("");

  useEffect(() => {
    let active: boolean = true;
    setFilterError("");
    setHistoryError("");
    getReport(reportId, filterQuery)
      .then((value) => {
        if (!active) return;
        setReport(value);
        void getReportHistory(value.game.app_id)
          .then((items) => { if (active) setHistory(items); })
          .catch(() => { if (active) setHistoryError("Unable to load report history."); });
      })
      .catch(() => {
        if (!active) return;
        if (filterQuery) setFilterError("These filters are invalid or unavailable.");
        else setError("Unable to load this report.");
      });
    return () => { active = false; };
  }, [reportId, filterQuery]);

  const allThemes: ReportTheme[] = report
    ? [...report.positive_themes, ...report.negative_themes, ...report.technical_themes]
    : [];
  const hasThemes: boolean = allThemes.length > 0;
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
      const result: ThemeEvidence = await getThemeEvidence(
        reportId, theme.theme_id, filterQuery,
      );
      setEvidence((current) => ({ ...current, [theme.theme_id]: result }));
    } catch {
      setError("Unable to load complete evidence.");
    } finally {
      setEvidenceLoading(null);
    }
  }

  function applyFilters(): void {
    setFilterError("");
    setEvidence({});
    setOpenThemeId(null);
    setCategory("All categories");
    setFilterQuery(buildEvidenceFilterQuery(filterDraft));
  }

  function resetFilters(): void {
    setFilterError("");
    setFilterDraft(EMPTY_FILTER);
    setEvidence({});
    setOpenThemeId(null);
    setCategory("All categories");
    setFilterQuery("");
  }

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
                    {formatHistoryDate(entry.created_at)} · {entry.provider} · {entry.model}
                  </a>
                </li>
              ))}
            </ul>
          </details>
          {historyError && <p className="error" role="alert">{historyError}</p>}
          <a className="new-report-link" href={`/?appid=${appId}`}>Create new report</a>
        </div>
      </header>

      <section className="report-facts" aria-label="Report scope and provenance">
        <div><span>Review scope</span><strong>{report.scope.review_count.toLocaleString()} reviews</strong></div>
        {report.scope.early && <div><span>Early cohort</span><strong>{report.scope.early.review_count.toLocaleString()} reviews</strong><small>{formatReviewDate(report.scope.early.source_created_from)}–{formatReviewDate(report.scope.early.source_created_to)}</small></div>}
        {report.scope.recent && <div><span>Recent cohort</span><strong>{report.scope.recent.review_count.toLocaleString()} reviews</strong><small>{formatReviewDate(report.scope.recent.source_created_from)}–{formatReviewDate(report.scope.recent.source_created_to)}</small></div>}
        <div><span>Provider</span><strong>{report.provenance.provider}</strong></div>
        <div><span>Model</span><strong>{report.provenance.model}</strong></div>
      </section>

      <details className="evidence-filters">
        <summary>Evidence filters{filterQuery ? " (active)" : ""}</summary>
        <form onSubmit={(event) => { event.preventDefault(); applyFilters(); }}>
          <label>Recommendation
            <select value={filterDraft.recommendation} onChange={(event) => setFilterDraft({ ...filterDraft, recommendation: event.target.value })}>
              <option value="all">All</option><option value="recommended">Recommended</option><option value="not_recommended">Not recommended</option>
            </select>
          </label>
          <BooleanFilter label="Steam purchase" value={filterDraft.steamPurchase} onChange={(value) => setFilterDraft({ ...filterDraft, steamPurchase: value })} />
          <BooleanFilter label="Received free" value={filterDraft.receivedForFree} onChange={(value) => setFilterDraft({ ...filterDraft, receivedForFree: value })} />
          <BooleanFilter label="Early Access" value={filterDraft.earlyAccess} onChange={(value) => setFilterDraft({ ...filterDraft, earlyAccess: value })} />
          <label>Playtime basis
            <select value={filterDraft.playtimeBasis} onChange={(event) => setFilterDraft({ ...filterDraft, playtimeBasis: event.target.value })}>
              <option value="at_review">At review</option><option value="current">Current total</option>
            </select>
          </label>
          <label>Minimum hours<input type="number" min="0" step="0.1" value={filterDraft.minimumHours} onChange={(event) => setFilterDraft({ ...filterDraft, minimumHours: event.target.value })} /></label>
          <label>Maximum hours<input type="number" min="0" step="0.1" value={filterDraft.maximumHours} onChange={(event) => setFilterDraft({ ...filterDraft, maximumHours: event.target.value })} /></label>
          <label>Reviewed from<input type="date" value={filterDraft.reviewCreatedFrom} onChange={(event) => setFilterDraft({ ...filterDraft, reviewCreatedFrom: event.target.value })} /></label>
          <label>Reviewed to<input type="date" value={filterDraft.reviewCreatedTo} onChange={(event) => setFilterDraft({ ...filterDraft, reviewCreatedTo: event.target.value })} /></label>
          <div className="filter-actions">
            <button type="submit">Apply filters</button>
            <button type="button" onClick={resetFilters}>Reset filters</button>
          </div>
        </form>
        {filterError && <p role="alert">{filterError}</p>}
        <p>Filters recalculate existing Themes only. They are not saved and do not run analysis.</p>
      </details>

      {!hasThemes && !filterQuery ? (
        <section className="empty-report" role="status">
          <h2>No recurring Themes met the evidence rule</h2>
          <p>
            {report.scope.non_neutral_opinion_point_count.toLocaleString()} positive or negative Opinion Point{report.scope.non_neutral_opinion_point_count === 1 ? " was" : "s were"} extracted from {report.scope.review_count.toLocaleString()} reviews.
          </p>
          <p>A Theme requires the same subject and polarity in at least two distinct reviews and a minimum percentage of the report scope. This empty result does not mean players expressed no opinions.</p>
        </section>
      ) : (
        <>
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
        </>
      )}

      <StorefrontOverview metadata={report.metadata} />

      <StorageControls
        appId={appId}
        reportId={report.report_version_id}
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
          {theme.below_threshold && <small className="threshold-note">Below original threshold</small>}
        </span>
        <span className="chevron" aria-hidden="true">⌄</span>
      </button>
      {expanded && (
        <div className="theme-detail" id={detailId}>
          <p>{theme.summary}</p>
          {theme.related_categories.length > 0 && (
            <p className="related-categories">Also relates to {theme.related_categories.join(", ")}</p>
          )}
          {theme.cohort_comparison && (
            <div className="cohort-comparison">
              <strong>{comparisonLabel(theme.cohort_comparison.direction)}</strong>
              <span>Early {formatPercent(theme.cohort_comparison.early.percentage)} ({theme.cohort_comparison.early.count}/{theme.cohort_comparison.early.denominator})</span>
              <span>Recent {formatPercent(theme.cohort_comparison.recent.percentage)} ({theme.cohort_comparison.recent.count}/{theme.cohort_comparison.recent.denominator})</span>
              <span>{formatSignedPercentagePoints(theme.cohort_comparison.percentage_point_change)}</span>
            </div>
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

function comparisonLabel(direction: ThemeCohortComparison["direction"]): string {
  return ({
    appears_improved: "Appears improved",
    mostly_unchanged: "Mostly unchanged",
    appears_worse: "Appears worse",
    new_in_recent_reviews: "New in recent reviews",
    no_longer_prominent: "No longer prominent",
  } as Record<string, string>)[direction] ?? direction;
}

function formatSignedPercentagePoints(value: number): string {
  const prefix: string = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)} percentage points`;
}

function formatReviewDate(timestamp: number): string {
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short" })
    .format(new Date(timestamp * 1000));
}

function formatHistoryDate(timestamp: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" })
    .format(new Date(`${timestamp.replace(" ", "T")}Z`));
}

function BooleanFilter({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }): JSX.Element {
  return (
    <label>{label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Any</option><option value="true">Yes</option><option value="false">No</option>
      </select>
    </label>
  );
}

function buildEvidenceFilterQuery(filter: EvidenceFilterDraft): string {
  const query = new URLSearchParams();
  if (filter.recommendation !== "all") query.set("recommendation", filter.recommendation);
  for (const [name, value] of [
    ["steam_purchase", filter.steamPurchase],
    ["received_for_free", filter.receivedForFree],
    ["written_during_early_access", filter.earlyAccess],
  ]) if (value) query.set(name, value);
  if (filter.playtimeBasis !== "at_review") query.set("playtime_basis", filter.playtimeBasis);
  if (filter.minimumHours) query.set("minimum_playtime_minutes", String(Math.round(Number(filter.minimumHours) * 60)));
  if (filter.maximumHours) query.set("maximum_playtime_minutes", String(Math.round(Number(filter.maximumHours) * 60)));
  if (filter.reviewCreatedFrom) query.set("review_created_from", String(Date.parse(`${filter.reviewCreatedFrom}T00:00:00Z`) / 1000));
  if (filter.reviewCreatedTo) query.set("review_created_to", String(Date.parse(`${filter.reviewCreatedTo}T00:00:00Z`) / 1000 + 86_399));
  return query.toString();
}

function formatPercent(value: number): string {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}%`;
}

function formatHours(minutes: number | null): string {
  if (minutes === null) return "Unknown";
  const hours: number = minutes / 60;
  return `${Number.isInteger(hours) ? hours : hours.toFixed(1)}h`;
}
