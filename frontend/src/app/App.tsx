import { FormEvent, useEffect, useState } from "react";
import {
  AnalysisJob,
  AnalysisRun,
  cancelJob,
  cancelAnalysisRun,
  CodexCliProviderStatus,
  getCodexCliProviderStatus,
  getOllamaProviderStatus,
  getGamePreview,
  getHealth,
  getJob,
  getAnalysisRun,
  getPublicConfig,
  GameSearchResult,
  OllamaProviderStatus,
  retryJob,
  searchGames,
  startQuickImport,
  startCodexAnalysis,
  startOllamaAnalysis,
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
  const [catalogExpanded, setCatalogExpanded] = useState<boolean>(true);
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
  const [codexStatus, setCodexStatus] = useState<CodexCliProviderStatus | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaProviderStatus | null>(null);
  const [providerSelection, setProviderSelection] = useState<string>("codex-cli");
  const [analysisRun, setAnalysisRun] = useState<AnalysisRun | null>(null);
  const [analysisError, setAnalysisError] = useState<string>("");

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
    let active: boolean = true;
    getOllamaProviderStatus()
      .then((status) => { if (active) setOllamaStatus(status); })
      .catch(() => { if (active) setOllamaStatus(null); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const runId = window.localStorage.getItem("active-analysis-run");
    if (!runId) return;
    getAnalysisRun(runId)
      .then(setAnalysisRun)
      .catch(() => window.localStorage.removeItem("active-analysis-run"));
  }, []);

  useEffect(() => {
    let active: boolean = true;
    getCodexCliProviderStatus()
      .then((status) => {
        if (active) setCodexStatus(status);
      })
      .catch(() => {
        if (active) setCodexStatus(null);
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

  useEffect(() => {
    if (!analysisRun || !["queued", "running"].includes(analysisRun.state)) return;
    let active = true;
    const refresh = (): void => {
      getAnalysisRun(analysisRun.id)
        .then((nextRun) => { if (active) setAnalysisRun(nextRun); })
        .catch(() => { if (active) setAnalysisError("Unable to refresh analysis progress."); });
    };
    refresh();
    const timer = window.setInterval(refresh, 500);
    return () => { active = false; window.clearInterval(timer); };
  }, [analysisRun?.id, analysisRun?.state]);

  function submitPreview(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    loadPreview(appId);
  }

  function loadPreview(selectedAppId: string): void {
    setPreviewLoading(true);
    setPreviewError("");
    setJob(null);
    setAnalysisRun(null);
    window.localStorage.removeItem("active-import-job");
    window.localStorage.removeItem("active-analysis-run");
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

  function beginAnalysis(): void {
    const selectedAppId = preview?.app_id ?? job?.app_id;
    if (!selectedAppId) return;
    setAnalysisError("");
    const selectedModel = providerSelection.startsWith("ollama::")
      ? providerSelection.slice("ollama::".length)
      : null;
    const start = selectedModel
      ? startOllamaAnalysis(selectedAppId, selectedModel)
      : startCodexAnalysis(selectedAppId);
    start
      .then((run) => {
        window.localStorage.setItem("active-analysis-run", run.id);
        setAnalysisRun(run);
      })
      .catch(() => setAnalysisError("Unable to start the selected analysis provider."));
  }

  function cancelAnalysis(): void {
    if (!analysisRun) return;
    cancelAnalysisRun(analysisRun.id)
      .then(setAnalysisRun)
      .catch(() => setAnalysisError("Unable to cancel analysis."));
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

      <div className={`catalog${catalogExpanded ? "" : " catalog-collapsed"}`}>
        <section
          id="catalog-selection"
          className="catalog-search"
          aria-labelledby="catalog-title"
          hidden={!catalogExpanded}
        >
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

        <button
          className="catalog-toggle"
          type="button"
          aria-controls="catalog-selection"
          aria-expanded={catalogExpanded}
          aria-label={`${catalogExpanded ? "Collapse" : "Expand"} game selection`}
          onClick={() => setCatalogExpanded(!catalogExpanded)}
        >
          <span aria-hidden="true">{catalogExpanded ? "‹" : "›"}</span>
        </button>

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
              {job.state === "completed" && !analysisRun && (
                <>
                  <p>Provisional report thresholds: at least 2 reviews and 1% support.</p>
                  <button
                    type="button"
                    onClick={beginAnalysis}
                    disabled={
                      providerSelection === "codex-cli"
                        ? !codexStatus?.installed || !codexStatus.authenticated
                        : !ollamaStatus?.models.some(
                            (model) => providerSelection === `ollama::${model.name}`,
                          )
                    }
                  >
                    {providerSelection === "codex-cli"
                      ? "Analyze with Codex CLI"
                      : "Analyze with Ollama"}
                  </button>
                </>
              )}
              {analysisRun && (
                <div className="analysis-progress">
                  <p className="eyebrow">{analysisRun.provider === "ollama" ? "OLLAMA ANALYSIS" : "CODEX ANALYSIS"}</p>
                  <h3>{
                    analysisRun.state === "completed" ? "Report complete" :
                    analysisRun.state === "failed" ? "Analysis failed" :
                    analysisRun.state === "cancelled" ? "Analysis cancelled" : "Analyzing reviews"
                  }</h3>
                  <p>{analysisRun.review_count.toLocaleString()} reviews · {analysisRun.model}</p>
                  {["queued", "running"].includes(analysisRun.state) && (
                    <button type="button" onClick={cancelAnalysis}>Cancel analysis</button>
                  )}
                  {analysisRun.report_version_id && (
                    <>
                      {analysisRun.input_tokens !== null && analysisRun.output_tokens !== null && (
                        <p>
                          Measured usage: {analysisRun.input_tokens.toLocaleString()} input and {analysisRun.output_tokens.toLocaleString()} output tokens.{analysisRun.provider === "codex-cli" ? " Remaining subscription quota is unavailable." : " Processing stayed on this device."}
                        </p>
                      )}
                      <a href={`/reports/${encodeURIComponent(analysisRun.report_version_id)}`}>View report</a>
                    </>
                  )}
                </div>
              )}
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
                <label htmlFor="analysis-provider">Analysis provider</label>
                <select
                  id="analysis-provider"
                  value={providerSelection}
                  onChange={(event) => setProviderSelection(event.target.value)}
                >
                  <option value="codex-cli">Codex CLI · GPT-5.6 Luna</option>
                  {ollamaStatus?.models.map((model) => (
                    <option key={model.name} value={`ollama::${model.name}`}>
                      Ollama · {model.name}
                    </option>
                  ))}
                </select>
                {providerSelection === "codex-cli" && codexStatus && (
                  <div className="provider-disclosure">
                    <strong>{
                      codexStatus.installed && codexStatus.authenticated
                        ? "Codex CLI ready"
                        : "Codex CLI unavailable"
                    }</strong>
                    <span>GPT-5.6 Luna · {codexStatus.reasoning_effort} reasoning</span>
                    <p>External cloud processing: review text is sent to OpenAI only when you start analysis.</p>
                    <p>Remaining subscription quota and dollar cost are unavailable to this application.</p>
                  </div>
                )}
                {providerSelection.startsWith("ollama::") && (
                  <div className="provider-disclosure">
                    <strong>Ollama local model ready</strong>
                    <span>{providerSelection.slice("ollama::".length)}</span>
                    <p>Local processing: review text stays on this device.</p>
                    <p>The application only uses models already installed in Ollama and never downloads one.</p>
                  </div>
                )}
                {ollamaStatus && ollamaStatus.models.length === 0 && (
                  <div className="provider-disclosure">
                    <strong>Ollama has no installed models</strong>
                    <p>After installing Ollama, copy and run one command outside this application:</p>
                    <code>ollama pull qwen3.5:4b</code>
                    <code>ollama pull qwen3.5:9b</code>
                    <p>Restart the app after the model download completes.</p>
                  </div>
                )}
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
          {analysisError && <p className="error" role="alert">{analysisError}</p>}
        </aside>
      </div>
    </main>
  );
}
