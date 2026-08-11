import { FormEvent, useEffect, useState } from "react";
import {
  AnalysisJob,
  cancelJob,
  getGamePreview,
  getHealth,
  getJob,
  getPublicConfig,
  GameSearchResult,
  retryJob,
  searchGames,
  startQuickImport,
  SteamMetadata,
} from "../api/shell";
import ReportView from "../features/report/ReportView";
import { deleteIncompleteJob } from "../api/storage";
import StorefrontOverview from "../features/game/StorefrontOverview";

type HealthState = "loading" | "ready" | "unavailable";

export default function App(): JSX.Element {
  const reportMatch: RegExpMatchArray | null = window.location.pathname.match(/^\/reports\/([^/]+)$/);
  return reportMatch
    ? <ReportView reportId={decodeURIComponent(reportMatch[1])} />
    : <CatalogApp />;
}

function CatalogApp(): JSX.Element {
  const [health, setHealth] = useState<HealthState>("loading");
  const [appId, setAppId] = useState<string>("");
  const [gameQuery, setGameQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<GameSearchResult[]>([]);
  const [searchError, setSearchError] = useState<string>("");
  const [preview, setPreview] = useState<SteamMetadata | null>(null);
  const [previewError, setPreviewError] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [targetCount, setTargetCount] = useState<number>(5000);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [jobError, setJobError] = useState<string>("");
  const [jobDeleteConfirmation, setJobDeleteConfirmation] = useState<string>("");
  const [jobDeleted, setJobDeleted] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    Promise.all([getHealth(), getPublicConfig()])
      .then(() => {
        if (active) setHealth("ready");
      })
      .catch(() => {
        if (active) setHealth("unavailable");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const jobId: string | null = window.localStorage.getItem("active-import-job");
    if (!jobId) return;
    getJob(jobId)
      .then(setJob)
      .catch(() => window.localStorage.removeItem("active-import-job"));
  }, []);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.state)) return;
    let active = true;
    const refresh = (): void => {
      getJob(job.id)
        .then((nextJob) => {
          if (active) setJob(nextJob);
        })
        .catch(() => {
          if (active) setJobError("Unable to refresh import progress.");
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [job?.id, job?.state]);

  function submitPreview(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    loadPreview(appId);
  }

  function loadPreview(selectedAppId: string): void {
    setPreviewLoading(true);
    setPreviewError("");
    setJob(null);
    window.localStorage.removeItem("active-import-job");
    getGamePreview(selectedAppId)
      .then((metadata) => setPreview(metadata))
      .catch(() => {
        setPreview(null);
        setPreviewError("Unable to preview that AppID. Check it and try again.");
      })
      .finally(() => setPreviewLoading(false));
  }

  function submitSearch(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setSearchError("");
    searchGames(gameQuery)
      .then(setSearchResults)
      .catch(() => setSearchError("Unable to search Steam games."));
  }

  function selectSearchResult(result: GameSearchResult): void {
    const selectedAppId: string = String(result.app_id);
    setAppId(selectedAppId);
    loadPreview(selectedAppId);
  }

  function beginImport(): void {
    if (!preview) return;
    setJobError("");
    setJobDeleted(false);
    setJobDeleteConfirmation("");
    startQuickImport(preview.app_id, targetCount)
      .then((startedJob) => {
        window.localStorage.setItem("active-import-job", startedJob.id);
        setJob(startedJob);
      })
      .catch(() => setJobError("Unable to start the Quick import."));
  }

  function cancelImport(): void {
    if (!job) return;
    cancelJob(job.id).then(setJob).catch(() => setJobError("Unable to cancel the import."));
  }

  function retryImport(): void {
    if (!job) return;
    setJobError("");
    retryJob(job.id).then(setJob).catch(() => setJobError("Unable to retry the import."));
  }

  function removeIncompleteJob(): void {
    if (!job) return;
    setJobError("");
    deleteIncompleteJob(job.id, jobDeleteConfirmation)
      .then(() => {
        window.localStorage.removeItem("active-import-job");
        setJobDeleted(true);
      })
      .catch(() => setJobError("Unable to delete the incomplete job."));
  }

  const unknown = "Unknown / unavailable";

  return (
    <main className="shell">
      <header className="app-header">
        <div className="brand"><span aria-hidden="true">G</span> Game Review Analyzer</div>
        <p className={`health health-${health}`} role="status">
          Backend {health === "loading" ? "checking…" : health === "ready" ? "connected" : "unavailable"}
        </p>
      </header>

      <div className="catalog">
        <section className="catalog-search" aria-labelledby="catalog-title">
          <p className="eyebrow">GAME CATALOG</p>
          <h1 id="catalog-title">Select the game to analyze</h1>
          <p className="intro">Search by name or enter an exact Steam AppID, then confirm the game before reviews are downloaded.</p>
          <form className="game-search-form" onSubmit={submitSearch}>
            <label htmlFor="game-name">Game name</label>
            <div className="appid-row">
              <input id="game-name" minLength={2} required value={gameQuery} onChange={(event) => setGameQuery(event.target.value)} />
              <button type="submit" disabled={health !== "ready"}>Search games</button>
            </div>
          </form>
          {searchError && <p className="error" role="alert">{searchError}</p>}
          {searchResults.length > 0 && (
            <ul className="game-results">
              {searchResults.map((result) => (
                <li key={result.app_id}>
                  <button type="button" onClick={() => selectSearchResult(result)}>
                    <strong>{result.title}</strong>
                    <span>AppID {result.app_id} · {result.source === "catalog" ? "Steam catalog" : "Store fallback"}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <form className="appid-form" onSubmit={submitPreview}>
            <label htmlFor="steam-appid">Steam AppID</label>
            <div className="appid-row">
              <input
                id="steam-appid"
                inputMode="numeric"
                pattern="[1-9][0-9]*"
                required
                value={appId}
                onChange={(event) => setAppId(event.target.value)}
                placeholder="1145350"
              />
              <button type="submit" disabled={health !== "ready" || previewLoading}>
                {previewLoading ? "Checking…" : "Preview game"}
              </button>
            </div>
          </form>
          {previewError && <p className="error" role="alert">{previewError}</p>}
        </section>

        <aside className="catalog-preview" aria-live="polite">
          {job ? (
            <section className="import-progress" aria-labelledby="import-title">
              <p className="eyebrow">QUICK IMPORT</p>
              <h2 id="import-title">{
                job.state === "completed" ? "Import complete" :
                job.state === "failed" ? "Import failed" :
                job.state === "cancelled" ? "Import cancelled" : "Downloading reviews"
              }</h2>
              <p>{job.imported_count.toLocaleString()} of {job.target_count.toLocaleString()} reviews</p>
              <progress value={job.imported_count} max={job.target_count} />
              {job.state === "failed" && <button type="button" onClick={retryImport}>Retry import</button>}
              {["queued", "running"].includes(job.state) && (
                <button type="button" onClick={cancelImport}>Cancel import</button>
              )}
              {["failed", "cancelled"].includes(job.state) && !jobDeleted && (
                <div className="job-deletion">
                  <p>This removes only the incomplete job. Imported reviews and existing reports remain available.</p>
                  <label>
                    Type {job.id} to delete this incomplete job
                    <input
                      value={jobDeleteConfirmation}
                      onChange={(event) => setJobDeleteConfirmation(event.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={jobDeleteConfirmation !== job.id}
                    onClick={removeIncompleteJob}
                  >
                    Delete incomplete job
                  </button>
                </div>
              )}
              {jobDeleted && <p role="status">Incomplete job deleted</p>}
            </section>
          ) : !preview ? (
            <div className="preview-empty">
              <p className="eyebrow">CONFIRM IDENTITY</p>
              <h2>Game details appear here</h2>
              <p>Nothing is downloaded beyond the metadata needed for this preview.</p>
            </div>
          ) : (
            <>
              {preview.capsule_image_url ? (
                <img src={preview.capsule_image_url} alt={`${preview.title} Steam capsule`} />
              ) : (
                <div className="capsule-placeholder" aria-hidden="true">{preview.title}</div>
              )}
              <p className="eyebrow">CONFIRM IDENTITY</p>
              <h2>{preview.title}</h2>
              <p className="developer">{preview.developers?.join(", ") ?? unknown}</p>
              <dl className="identity-grid">
                <div><dt>AppID</dt><dd>{preview.app_id}</dd></div>
                <div><dt>Release date</dt><dd>{preview.release_date ?? unknown}</dd></div>
                <div><dt>Release status</dt><dd>{preview.release_status === "unknown" ? unknown : preview.release_status === "coming_soon" ? "Coming soon" : "Released"}</dd></div>
                <div><dt>Review availability</dt><dd>{preview.review_count === null ? unknown : `${preview.review_count.toLocaleString()} reviews`}</dd></div>
              </dl>
              {preview.source_status === "partial" && (
                <p className="source-note">Some optional Steam metadata is unavailable. You can still continue.</p>
              )}
              {preview.storefront_source_status !== "unavailable" && (
                <StorefrontOverview metadata={preview} />
              )}
              <div className="analysis-setup">
                <p><strong>Quick analysis</strong><br />Latest eligible English reviews</p>
                <label htmlFor="review-limit">Review limit</label>
                <input
                  id="review-limit"
                  type="number"
                  min="1"
                  required
                  value={targetCount}
                  onChange={(event) => setTargetCount(event.target.valueAsNumber)}
                />
                <button className="create-report" type="button" onClick={beginImport}>
                  Create report
                </button>
              </div>
            </>
          )}
          {jobError && <p className="error" role="alert">{jobError}</p>}
        </aside>
      </div>
    </main>
  );
}
