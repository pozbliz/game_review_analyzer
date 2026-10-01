import { FormEvent, useEffect, useRef, useState } from "react";
import {
  AnalysisJob,
  AnalysisRun,
  analysisFailureMessage,
  AggregateReportSettings,
  AvailableReport,
  cancelJob,
  cancelAnalysisRun,
  CodexCliProviderStatus,
  getCodexCliProviderStatus,
  getOllamaProviderStatus,
  getGamePreview,
  getGameWorkspace,
  getHealth,
  getJob,
  getAnalysisRun,
  getPublicConfig,
  GameSearchResult,
  OllamaProviderStatus,
  retryJob,
  retryAnalysisRun,
  searchGames,
  startFullImport,
  startOllamaAnalysis,
  startMainReport,
  startTestReport,
  SteamMetadata,
} from "../api/shell";
import ReportView from "../features/report/ReportView";
import AggregateReportView from "../features/report/AggregateReportView";
import { getRecentReports, getReportHistory, ReportHistoryEntry } from "../api/reports";
import { deleteIncompleteJob } from "../api/storage";
import StorefrontOverview from "../features/game/StorefrontOverview";

type HealthState = "loading" | "ready" | "unavailable";

export { analysisFailureMessage } from "../api/shell";

export default function App(): JSX.Element {
  const testReportMatch: RegExpMatchArray | null = window.location.pathname.match(
    /^\/test-reports\/(\d+)$/,
  );
  const mainReportMatch: RegExpMatchArray | null = window.location.pathname.match(
    /^\/main-reports\/(\d+)$/,
  );
  const reportMatch: RegExpMatchArray | null = window.location.pathname.match(/^\/reports\/([^/]+)$/);
  return mainReportMatch
    ? <AggregateReportView appId={Number(mainReportMatch[1])} kind="main" />
    : testReportMatch
    ? <AggregateReportView appId={Number(testReportMatch[1])} />
    : reportMatch
    ? <ReportView reportId={decodeURIComponent(reportMatch[1])} />
    : <CatalogApp />;
}

function CatalogApp(): JSX.Element {
  const previewRequestId = useRef<number>(0);
  const requestedAppId: string = new URLSearchParams(window.location.search).get("appid") ?? "";
  const [health, setHealth] = useState<HealthState>("loading");
  const [showGameSearch, setShowGameSearch] = useState<boolean>(true);
  const [appId, setAppId] = useState<string>(requestedAppId);
  const [gameQuery, setGameQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<GameSearchResult[]>([]);
  const [searchError, setSearchError] = useState<string>("");
  const [preview, setPreview] = useState<SteamMetadata | null>(null);
  const [previewError, setPreviewError] = useState<string>("");
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [reportHistory, setReportHistory] = useState<ReportHistoryEntry[]>([]);
  const [recentReports, setRecentReports] = useState<ReportHistoryEntry[]>([]);
  const [reportHistoryLoading, setReportHistoryLoading] = useState<boolean>(false);
  const [reportHistoryError, setReportHistoryError] = useState<string>("");
  const [fullHistoryReady, setFullHistoryReady] = useState<boolean>(false);
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [jobError, setJobError] = useState<string>("");
  const [jobDeleteConfirmation, setJobDeleteConfirmation] = useState<string>("");
  const [jobDeleted, setJobDeleted] = useState<boolean>(false);
  const [codexStatus, setCodexStatus] = useState<CodexCliProviderStatus | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaProviderStatus | null>(null);
  const [providerSelection, setProviderSelection] = useState<string>(
    () => window.localStorage.getItem("analysis-provider") ?? "codex-cli",
  );
  const [codexCohortSize, setCodexCohortSize] = useState<number>(25);
  const [minimumSupportPercentage, setMinimumSupportPercentage] = useState<number>(5);
  const [maximumThemesPerPolarity, setMaximumThemesPerPolarity] = useState<number>(10);
  const [analysisRun, setAnalysisRun] = useState<AnalysisRun | null>(null);
  const [availableReports, setAvailableReports] = useState<AvailableReport[]>([]);
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
    getRecentReports()
      .then((reports) => { if (active) setRecentReports(reports); })
      .catch(() => { if (active) setRecentReports([]); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (/^[1-9][0-9]*$/.test(requestedAppId)) loadPreview(requestedAppId);
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
      .then((restoredRun) => {
        if (["queued", "running"].includes(restoredRun.state)) {
          setAnalysisRun(restoredRun);
          setShowGameSearch(false);
        } else {
          window.localStorage.removeItem("active-analysis-run");
        }
      })
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
      .then((restoredJob) => {
        if (["queued", "running"].includes(restoredJob.state)) {
          setJob(restoredJob);
          setShowGameSearch(false);
        } else {
          window.localStorage.removeItem("active-import-job");
        }
      })
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
    const requestId: number = ++previewRequestId.current;
    setPreviewLoading(true);
    setPreviewError("");
    setReportHistory([]);
    setReportHistoryLoading(true);
    setReportHistoryError("");
    setFullHistoryReady(false);
    setAvailableReports([]);
    setJob(null);
    setAnalysisRun(null);
    window.localStorage.removeItem("active-import-job");
    window.localStorage.removeItem("active-analysis-run");
    getGamePreview(selectedAppId)
      .then((metadata) => {
        if (requestId !== previewRequestId.current) return;
        setPreview(metadata);
        setShowGameSearch(false);
        const historyRequest: Promise<void> = getReportHistory(metadata.app_id)
          .then((items) => {
            if (requestId === previewRequestId.current) setReportHistory(items);
          })
          .catch(() => {
            if (requestId === previewRequestId.current) {
              setReportHistoryError(
                "Unable to load saved reports. Select this game again to retry.",
              );
            }
          });
        const workspaceRequest: Promise<void> = getGameWorkspace(metadata.app_id)
          .then((workspace) => {
            if (requestId !== previewRequestId.current) return;
            setFullHistoryReady(workspace.full_history_ready);
            setAvailableReports(workspace.available_reports);
            if (workspace.latest_analysis_run?.state !== "completed") {
              const latestRun: AnalysisRun | null = workspace.latest_analysis_run;
              if (latestRun) {
                window.localStorage.setItem("active-analysis-run", latestRun.id);
                setAnalysisRun(latestRun);
              }
            }
          });
        void Promise.allSettled([historyRequest, workspaceRequest]).then(() => {
          if (requestId === previewRequestId.current) setReportHistoryLoading(false);
        });
      })
      .catch(() => {
        if (requestId !== previewRequestId.current) return;
        setPreview(null);
        setPreviewError("Unable to preview that AppID. Check it and try again.");
      })
      .finally(() => {
        if (requestId === previewRequestId.current) setPreviewLoading(false);
      });
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
    startFullImport(preview.app_id)
      .then((startedJob) => {
        window.localStorage.setItem("active-import-job", startedJob.id);
        setJob(startedJob);
      })
      .catch(() => setJobError("Unable to start the full-history import."));
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
    const reportSettings: AggregateReportSettings = {
      minimum_support_percentage: minimumSupportPercentage,
      maximum_headlines_per_polarity: maximumThemesPerPolarity,
    };
    const start = selectedModel
      ? startOllamaAnalysis(selectedAppId, selectedModel)
      : codexCohortSize === 500
      ? startMainReport(selectedAppId, reportSettings)
      : startTestReport(selectedAppId, reportSettings);
    start
      .then((run) => {
        window.localStorage.setItem("active-analysis-run", run.id);
        setAnalysisRun(run);
      })
      .catch((error: unknown) => setAnalysisError(
        error instanceof Error
          ? analysisFailureMessage(error.message)
          : "Unable to start the selected analysis provider.",
      ));
  }

  function cancelAnalysis(): void {
    if (!analysisRun) return;
    cancelAnalysisRun(analysisRun.id)
      .then(setAnalysisRun)
      .catch(() => setAnalysisError("Unable to cancel analysis."));
  }

  function retryAnalysis(): void {
    if (!analysisRun) return;
    setAnalysisError("");
    retryAnalysisRun(analysisRun.id)
      .then(setAnalysisRun)
      .catch(() => setAnalysisError("Unable to retry analysis."));
  }

  function chooseDifferentProvider(): void {
    window.localStorage.removeItem("active-analysis-run");
    setAnalysisRun(null);
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
  const reportSettingsValid: boolean = (
    minimumSupportPercentage >= 0
    && minimumSupportPercentage <= 100
    && Number.isInteger(maximumThemesPerPolarity)
    && maximumThemesPerPolarity >= 1
  );

  return (
    <main className="shell">
      <header className="app-header">
        <div className="brand"><span aria-hidden="true">G</span> Game Review Analyzer</div>
        <p className={`health health-${health}`} role="status">
          Backend {health === "loading" ? "checking…" : health === "ready" ? "connected" : "unavailable"}
        </p>
      </header>

      <div className={`catalog${showGameSearch ? " catalog-searching" : ""}`}>
        <section
          id="catalog-selection"
          className="catalog-search"
          aria-labelledby="catalog-title"
          hidden={!showGameSearch}
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

        <aside className="catalog-preview" aria-live="polite">
          {showGameSearch ? (
            <section className="recent-reports" aria-labelledby="recent-reports-title">
              <p className="eyebrow">CONTINUE YOUR RESEARCH</p>
              <h2 id="recent-reports-title">Recent reports</h2>
              {recentReports.length > 0 ? (
                <ul>
                  {recentReports.map((entry) => (
                    <li key={entry.report_version_id}>
                      <a href={`/reports/${encodeURIComponent(entry.report_version_id)}`}>
                        <strong>{entry.game_title}</strong>
                        <span>{entry.review_count.toLocaleString()} reviews</span>
                        <small>{formatReportHistoryEntry(entry)}</small>
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No saved reports yet. Select a game to create the first one.</p>
              )}
            </section>
          ) : (
            <>
          <button className="game-search-back" type="button" onClick={() => setShowGameSearch(true)}>
            <span aria-hidden="true">←</span> Game search
          </button>
          {job || analysisRun ? (
            <section className="import-progress" aria-labelledby={job ? "import-title" : "analysis-title"}>
              {job && (
                <>
                  <p className="eyebrow">FULL HISTORY IMPORT</p>
                  <h2 id="import-title">{
                    job.state === "completed" ? "Import complete" :
                    job.state === "failed" ? "Import failed" :
                    job.state === "cancelled" ? "Import cancelled" : "Downloading reviews"
                  }</h2>
                  <p>{job.imported_count.toLocaleString()} reviews scanned</p>
                  {job.state === "failed" && job.error_code && (
                    <p className="error">Error code: <code>{job.error_code}</code></p>
                  )}
                  {job.state !== "completed" && <progress />}
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
                            ? !codexStatus?.installed
                              || !codexStatus.authenticated
                              || !reportSettingsValid
                            : !ollamaStatus?.models.some(
                                (model) => providerSelection === `ollama::${model.name}`,
                              )
                        }
                      >
                        {providerSelection.startsWith("ollama::") ? "Run Ollama pilot" : "Create Report"}
                      </button>
                    </>
                  )}
                </>
              )}
              {analysisRun && (
                <div className="analysis-progress">
                  <p className="eyebrow">{analysisRun.provider === "ollama" ? "OLLAMA ANALYSIS" : "CODEX ANALYSIS"}</p>
                  <h3 id="analysis-title">{
                    analysisRun.state === "completed" ? "Report complete" :
                    analysisRun.state === "failed" ? "Analysis failed" :
                    analysisRun.state === "cancelled" ? "Analysis cancelled" : "Analyzing reviews"
                  }</h3>
                  <p>{analysisRun.review_count.toLocaleString()} reviews · {analysisRun.model}</p>
                  {analysisRun.state === "failed" && analysisRun.error_code && (
                    <p className="error">
                      {analysisFailureMessage(analysisRun.error_code)} Error code: <code>{analysisRun.error_code}</code>
                    </p>
                  )}
                  {analysisRun.state === "running" && analysisRun.phase === "refreshing" && (
                    <p>Refreshing Steam reviews before selecting the report scope</p>
                  )}
                  {analysisRun.state === "running" && analysisRun.phase === "extracting" && (
                    <p>{analysisRun.extracted_review_count.toLocaleString()} of {analysisRun.review_count.toLocaleString()} reviews {analysisRun.report_kind === "main" ? "analyzed and checkpointed" : "extracted and cached"}</p>
                  )}
                  {analysisRun.state === "running" && analysisRun.phase === "consolidating" && (
                    <p>{analysisRun.report_kind === "main" ? "Merging Theme candidates and calculating metrics" : "Consolidating shared themes and cohort comparisons"}</p>
                  )}
                  {analysisRun.state === "running" && analysisRun.phase === "analyzing" && (
                    <p>Finding aggregate Themes</p>
                  )}
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
                      <a href={
                        analysisRun.report_kind === "test"
                          ? `/test-reports/${analysisRun.app_id}`
                          : analysisRun.report_kind === "main"
                          ? `/main-reports/${analysisRun.app_id}`
                          : `/reports/${encodeURIComponent(analysisRun.report_version_id)}`
                      }>
                        {analysisRun.report_kind === "test"
                          ? "View Test Report"
                          : analysisRun.report_kind === "main"
                          ? "View Main Report"
                          : "View report"}
                      </a>
                    </>
                  )}
                  {["failed", "cancelled"].includes(analysisRun.state)
                    && analysisRun.error_code !== "no_unseen_reviews" && (
                    <>
                      <button type="button" onClick={retryAnalysis}>Resume analysis</button>
                      <button type="button" onClick={chooseDifferentProvider}>
                        {analysisRun.state === "cancelled" ? "Back" : "Choose different provider"}
                      </button>
                    </>
                  )}
                </div>
              )}
            </section>
          ) : !preview ? (
            <div className="preview-empty">
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
              {reportHistory.length > 0 && (
                <section className="saved-reports" aria-labelledby="saved-reports-title">
                  <h3 id="saved-reports-title">Saved reports</h3>
                  <a
                    className="open-latest-report"
                    href={`/reports/${encodeURIComponent(reportHistory[0].report_version_id)}`}
                  >
                    Open latest report
                  </a>
                  <p>{formatReportHistoryEntry(reportHistory[0])}</p>
                  {reportHistory.length > 1 && (
                    <ul>
                      {reportHistory.slice(1).map((entry) => (
                        <li key={entry.report_version_id}>
                          <a href={`/reports/${encodeURIComponent(entry.report_version_id)}`}>
                            {formatReportHistoryEntry(entry)}
                          </a>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}
              <div className="analysis-setup">
                <p><strong>{providerSelection.startsWith("ollama::") || codexCohortSize === 25 ? "Oldest versus newest pilot" : "Oldest versus newest"}</strong><br />{
                  providerSelection.startsWith("ollama::") || codexCohortSize === 25
                    ? "Scans the complete available English review history, then analyzes 25 oldest and 25 newest reviews. Pilot results are less complete than a full report."
                    : "Scans the complete available English review history, then analyzes up to the 500 oldest and 500 newest reviews."
                }</p>
                <label htmlFor="analysis-provider">Analysis provider</label>
                <select
                  id="analysis-provider"
                  value={providerSelection}
                  onChange={(event) => {
                    window.localStorage.setItem("analysis-provider", event.target.value);
                    setProviderSelection(event.target.value);
                  }}
                >
                  <option value="codex-cli">Codex CLI · GPT-5.6 Luna</option>
                  {ollamaStatus?.models.map((model) => (
                    <option key={model.name} value={`ollama::${model.name}`}>
                      Ollama · {model.name}
                    </option>
                  ))}
                </select>
                {providerSelection === "codex-cli" && (
                  <>
                    <label htmlFor="analysis-scope">Analysis scope</label>
                    <select
                      id="analysis-scope"
                      value={codexCohortSize}
                      onChange={(event) => setCodexCohortSize(Number(event.target.value))}
                    >
                      <option value={25}>Test · 50 reviews</option>
                      <option value={500}>Main · 1,000 reviews</option>
                    </select>
                    <fieldset className="report-settings">
                      <legend>Theme visibility</legend>
                      <div>
                        <label htmlFor="minimum-support-percentage">Minimum support percentage</label>
                        <input
                          id="minimum-support-percentage"
                          type="number"
                          min={0}
                          max={100}
                          step={0.1}
                          value={minimumSupportPercentage}
                          onChange={(event) => setMinimumSupportPercentage(Number(event.target.value))}
                        />
                        <small>A Theme appears when it reaches this percentage in either cohort.</small>
                      </div>
                      <div>
                        <label htmlFor="maximum-themes-per-polarity">Maximum Themes per list</label>
                        <input
                          id="maximum-themes-per-polarity"
                          type="number"
                          min={1}
                          step={1}
                          value={maximumThemesPerPolarity}
                          onChange={(event) => setMaximumThemesPerPolarity(Number(event.target.value))}
                        />
                        <small>Positive and negative lists use this cap independently.</small>
                      </div>
                    </fieldset>
                  </>
                )}
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
                {availableReports.length > 0 && (
                  <section className="available-reports" aria-labelledby="available-reports-title">
                    <h3 id="available-reports-title">Available Reports</h3>
                    {availableReports.map((report) => (
                      <a
                        key={report.kind}
                        href={`/${report.kind}-reports/${preview.app_id}`}
                      >
                        <strong>{report.kind === "main" ? "Main Report" : "Test Report"}</strong>
                        <span>{report.review_count.toLocaleString()} reviews{" \u00b7 "}{formatReportDate(report.created_at)}</span>
                      </a>
                    ))}
                  </section>
                )}
                <button
                  className={`create-report${reportHistory.length > 0 ? " create-report-secondary" : ""}`}
                  type="button"
                  disabled={
                    reportHistoryLoading
                    || Boolean(reportHistoryError)
                    || (
                      (reportHistory.length > 0 || fullHistoryReady)
                      && providerSelection === "codex-cli"
                      && (!codexStatus?.installed || !codexStatus.authenticated)
                    )
                    || (providerSelection === "codex-cli" && !reportSettingsValid)
                  }
                  onClick={reportHistory.length > 0 || fullHistoryReady ? beginAnalysis : beginImport}
                >
                  Create Report
                </button>
              </div>
            </>
          )}
          {reportHistoryError && <p className="error" role="alert">{reportHistoryError}</p>}
          {jobError && <p className="error" role="alert">{jobError}</p>}
          {analysisError && <p className="error" role="alert">{analysisError}</p>}
            </>
          )}
        </aside>
      </div>
    </main>
  );
}

function formatReportHistoryEntry(entry: ReportHistoryEntry): string {
  const date: Date = new Date(`${entry.created_at.replace(" ", "T")}Z`);
  const provider: string = ({
    "codex-cli": "Codex CLI",
    "manual-codex": "Manual Codex",
    ollama: "Ollama",
  } as Record<string, string>)[entry.provider] ?? entry.provider;
  return `${new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date)} · ${provider} · ${entry.model}`;
}

function formatReportDate(createdAt: string): string {
  const date: Date = new Date(`${createdAt.replace(" ", "T")}Z`);
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}
