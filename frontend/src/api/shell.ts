export interface HealthResponse {
  status: "ok";
  service: "game-review-analyzer";
}

export interface PublicConfigResponse {
  environment: string;
  api_prefix: "/api";
  steam_country_code: string;
  keyed_catalog_available: boolean;
}

type ReleaseStatus = "released" | "coming_soon" | "unknown";
type MetadataSourceStatus = "complete" | "partial";
type MissingMetadataField =
  | "developers"
  | "capsule_image_url"
  | "release_date"
  | "release_status"
  | "review_count";

export interface SteamMetadata {
  app_id: number;
  title: string;
  developers: string[] | null;
  capsule_image_url: string | null;
  release_date: string | null;
  release_status: ReleaseStatus;
  review_count: number | null;
  source_status: MetadataSourceStatus;
  missing_fields: MissingMetadataField[];
  storefront: SteamStorefront;
  storefront_source_status: "complete" | "partial" | "unavailable";
  storefront_missing_fields: string[];
}

export interface ReviewLanguageCount {
  language: string;
  review_count: number;
}

export interface SteamPrice {
  country_code: string;
  currency: string;
  initial_minor: number;
  final_minor: number;
  discount_percent: number;
  initial_formatted: string;
  final_formatted: string;
}

export interface SteamFeature {
  name: string;
  group: "Play modes" | "Input" | "Steam features" | "Platforms and accessibility";
  state: "supported" | "partial" | "not_supported" | "unknown";
}

export interface SteamTrailer {
  name: string;
  thumbnail_url: string;
  video_url: string;
}

export interface SteamStorefront {
  publishers: string[] | null;
  genres: string[] | null;
  short_description: string | null;
  about_text: string | null;
  tags: string[] | null;
  price: SteamPrice | null;
  is_free: boolean | null;
  dlc_app_ids: number[] | null;
  dlc_names: string[] | null;
  demo_app_ids: number[] | null;
  package_names: string[] | null;
  platforms: string[] | null;
  supported_languages: string | null;
  age_rating: string | null;
  content_notes: string | null;
  features: SteamFeature[] | null;
  screenshot_urls: string[] | null;
  trailers: SteamTrailer[] | null;
}

export interface GameSearchResult {
  app_id: number;
  title: string;
  capsule_image_url: string | null;
  source: "catalog" | "fallback";
}

export type JobState = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface AnalysisJob {
  id: string;
  app_id: number;
  scope: "quick" | "full" | "refresh" | "reconciliation";
  state: JobState;
  target_count: number;
  imported_count: number;
  cursor: string;
  cancel_requested: boolean;
  error_code: string | null;
}

export interface CodexCliProviderStatus {
  installed: boolean;
  authenticated: boolean;
  version: string | null;
  model: string;
  reasoning_effort: string;
  processing_location: "external_cloud";
  cost_basis: "subscription_quota_unknown";
}

export interface AnalysisRun {
  id: string;
  app_id: number;
  provider: string;
  model: string;
  state: JobState;
  review_count: number;
  cancel_requested: boolean;
  error_code: string | null;
  report_version_id: string | null;
  input_tokens: number | null;
  cached_input_tokens: number | null;
  output_tokens: number | null;
  extracted_review_count: number;
  oversized_review_count: number;
  report_kind: "main" | "test" | null;
  refresh_imported_count: number | null;
  refresh_target_count: number | null;
  phase: "queued" | "refreshing" | "analyzing" | "extracting" | "consolidating" | "completed" | "failed" | "cancelled";
}

export interface GameWorkspace {
  full_history_ready: boolean;
  latest_analysis_run: AnalysisRun | null;
  test_report_available: boolean;
  main_report_available: boolean;
  available_reports: AvailableReport[];
}

export interface AvailableReport {
  kind: "main" | "test";
  review_count: number;
  created_at: string;
}

export interface AggregateReportSettings {
  minimum_support_percentage: number;
  maximum_headlines_per_polarity: number;
}

export function analysisFailureMessage(code: string): string {
  if (["steam_unavailable", "invalid_steam_response", "cursor_repeated", "internal_import_error"].includes(code)) {
    return "Steam refresh failed. Retry to resume from the saved refresh checkpoint.";
  }
  if (["reservation_conflict", "main_report_analysis_active", "test_report_analysis_active"].includes(code)) {
    return "Another analysis owns this report slot. Wait for it to finish or cancel it.";
  }
  if (code === "no_unseen_reviews") {
    return "No unseen usable reviews remain. The current report already covers every eligible review.";
  }
  if (code.startsWith("provider_") || code === "codex_cli_not_ready") {
    return "The analysis provider failed. Check provider access, then retry this run.";
  }
  if (code.includes("checkpoint") || code === "invalid_refresh_scope") {
    return "Saved progress was invalid. Retry to rebuild only the affected stage.";
  }
  if (code === "cancelled") {
    return "Analysis was cancelled. Resume to continue from saved progress.";
  }
  return "Analysis stopped because of an internal error. Retry once, then inspect the error code if it repeats.";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isMissingMetadataField(value: unknown): value is MissingMetadataField {
  return typeof value === "string" && [
    "developers",
    "capsule_image_url",
    "release_date",
    "release_status",
    "review_count",
  ].includes(value);
}

async function requestJson(path: string, options?: RequestInit): Promise<unknown> {
  const response: Response = options ? await fetch(path, options) : await fetch(path);
  if (!response.ok) {
    let code: string = "request_failed";
    try {
      const payload: unknown = await response.json();
      if (isRecord(payload) && isRecord(payload.detail) && typeof payload.detail.code === "string") {
        code = payload.detail.code;
      }
    } catch {
      // The stable fallback keeps non-JSON proxy failures actionable.
    }
    throw new Error(code);
  }
  return response.json() as Promise<unknown>;
}

function parseJob(payload: unknown): AnalysisJob {
  if (
    !isRecord(payload) ||
    typeof payload.id !== "string" ||
    typeof payload.app_id !== "number" ||
    !["quick", "full", "refresh", "reconciliation"].includes(String(payload.scope)) ||
    !["queued", "running", "completed", "failed", "cancelled"].includes(
      String(payload.state),
    ) ||
    typeof payload.target_count !== "number" ||
    typeof payload.imported_count !== "number" ||
    typeof payload.cursor !== "string" ||
    typeof payload.cancel_requested !== "boolean" ||
    !(payload.error_code === null || typeof payload.error_code === "string")
  ) {
    throw new Error("Invalid analysis job response");
  }
  return payload as unknown as AnalysisJob;
}

function parseAnalysisRun(payload: unknown): AnalysisRun {
  if (!isRecord(payload) || typeof payload.id !== "string" ||
      typeof payload.app_id !== "number" || typeof payload.provider !== "string" ||
      typeof payload.model !== "string" ||
      !["queued", "running", "completed", "failed", "cancelled"].includes(String(payload.state)) ||
      typeof payload.review_count !== "number" || typeof payload.cancel_requested !== "boolean" ||
      typeof payload.extracted_review_count !== "number" ||
      typeof payload.oversized_review_count !== "number" ||
      !(payload.report_kind === null || payload.report_kind === "main" || payload.report_kind === "test") ||
      !["queued", "refreshing", "analyzing", "extracting", "consolidating", "completed", "failed", "cancelled"].includes(String(payload.phase)) ||
      !(payload.error_code === null || typeof payload.error_code === "string") ||
      !(payload.report_version_id === null || typeof payload.report_version_id === "string")) {
    throw new Error("Invalid analysis run response");
  }
  return {
    ...payload,
    refresh_imported_count: typeof payload.refresh_imported_count === "number"
      ? payload.refresh_imported_count : null,
    refresh_target_count: typeof payload.refresh_target_count === "number"
      ? payload.refresh_target_count : null,
  } as unknown as AnalysisRun;
}

export async function startTestReport(
  appId: number,
  settings: AggregateReportSettings,
): Promise<AnalysisRun> {
  return parseAnalysisRun(await requestJson(`/api/games/${appId}/reports/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  }));
}

export async function startMainReport(
  appId: number,
  settings: AggregateReportSettings,
): Promise<AnalysisRun> {
  return parseAnalysisRun(await requestJson(`/api/games/${appId}/reports/main`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  }));
}

export async function extendMainReport(appId: number): Promise<AnalysisRun> {
  return parseAnalysisRun(await requestJson(`/api/games/${appId}/reports/main/extend`, {
    method: "POST",
  }));
}

export async function getGameWorkspace(appId: number): Promise<GameWorkspace> {
  const payload: unknown = await requestJson(`/api/games/${appId}/workspace`);
  if (!isRecord(payload) || typeof payload.full_history_ready !== "boolean" ||
      typeof payload.test_report_available !== "boolean" ||
      typeof payload.main_report_available !== "boolean" ||
      !(payload.latest_analysis_run === null || isRecord(payload.latest_analysis_run)) ||
      !(payload.available_reports === undefined || Array.isArray(payload.available_reports))) {
    throw new Error("Invalid game workspace response");
  }
  return {
    full_history_ready: payload.full_history_ready,
    test_report_available: payload.test_report_available,
    main_report_available: payload.main_report_available,
    available_reports: (payload.available_reports ?? []).map((report) => {
      if (!isRecord(report) || !["main", "test"].includes(String(report.kind)) ||
          typeof report.review_count !== "number" || typeof report.created_at !== "string") {
        throw new Error("Invalid available report response");
      }
      return report as unknown as AvailableReport;
    }),
    latest_analysis_run: payload.latest_analysis_run === null
      ? null
      : parseAnalysisRun(payload.latest_analysis_run),
  };
}

export async function getAnalysisRun(runId: string): Promise<AnalysisRun> {
  return parseAnalysisRun(await requestJson(`/api/analysis-runs/${runId}`));
}

export async function cancelAnalysisRun(runId: string): Promise<AnalysisRun> {
  return parseAnalysisRun(await requestJson(
    `/api/analysis-runs/${runId}/cancel`, { method: "POST" },
  ));
}

export async function retryAnalysisRun(runId: string): Promise<AnalysisRun> {
  return parseAnalysisRun(await requestJson(
    `/api/analysis-runs/${encodeURIComponent(runId)}/retry`, { method: "POST" },
  ));
}

export async function startQuickImport(appId: number, targetCount: number): Promise<AnalysisJob> {
  return parseJob(await requestJson(`/api/games/${appId}/imports/quick`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_count: targetCount }),
  }));
}

export async function startRefresh(appId: number, targetCount: number): Promise<AnalysisJob> {
  return parseJob(await requestJson(`/api/games/${appId}/refreshes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_count: targetCount }),
  }));
}

export async function startFullImport(appId: number): Promise<AnalysisJob> {
  return parseJob(await requestJson(`/api/games/${appId}/imports/full`, { method: "POST" }));
}

export async function startReconciliation(appId: number): Promise<AnalysisJob> {
  return parseJob(await requestJson(`/api/games/${appId}/reconciliations`, { method: "POST" }));
}

export async function getJob(jobId: string): Promise<AnalysisJob> {
  return parseJob(await requestJson(`/api/jobs/${jobId}`));
}

export async function cancelJob(jobId: string): Promise<AnalysisJob> {
  return parseJob(await requestJson(`/api/jobs/${jobId}/cancel`, { method: "POST" }));
}

export async function retryJob(jobId: string): Promise<AnalysisJob> {
  return parseJob(await requestJson(`/api/jobs/${jobId}/retry`, { method: "POST" }));
}

export async function getHealth(): Promise<HealthResponse> {
  const payload: unknown = await requestJson("/api/health");
  if (
    !isRecord(payload) ||
    payload.status !== "ok" ||
    payload.service !== "game-review-analyzer"
  ) {
    throw new Error("Invalid health response");
  }
  return { status: payload.status, service: payload.service };
}

export async function getPublicConfig(): Promise<PublicConfigResponse> {
  const payload: unknown = await requestJson("/api/config");
  if (
    !isRecord(payload) ||
    typeof payload.environment !== "string" ||
    payload.api_prefix !== "/api" ||
    typeof payload.steam_country_code !== "string" ||
    typeof payload.keyed_catalog_available !== "boolean"
  ) {
    throw new Error("Invalid public configuration response");
  }
  return {
    environment: payload.environment,
    api_prefix: payload.api_prefix,
    steam_country_code: payload.steam_country_code,
    keyed_catalog_available: payload.keyed_catalog_available,
  };
}

export async function getCodexCliProviderStatus(): Promise<CodexCliProviderStatus> {
  const payload: unknown = await requestJson("/api/providers/codex-cli");
  if (
    !isRecord(payload) ||
    typeof payload.installed !== "boolean" ||
    typeof payload.authenticated !== "boolean" ||
    !(payload.version === null || typeof payload.version === "string") ||
    typeof payload.model !== "string" ||
    typeof payload.reasoning_effort !== "string" ||
    payload.processing_location !== "external_cloud" ||
    payload.cost_basis !== "subscription_quota_unknown"
  ) {
    throw new Error("Invalid Codex CLI provider response");
  }
  return payload as unknown as CodexCliProviderStatus;
}

export async function searchGames(query: string): Promise<GameSearchResult[]> {
  const payload: unknown = await requestJson(`/api/games/search?q=${encodeURIComponent(query)}`);
  if (!Array.isArray(payload)) throw new Error("Invalid game search response");
  return payload.map((item) => {
    if (!isRecord(item) || typeof item.app_id !== "number" || typeof item.title !== "string" ||
        !(item.capsule_image_url === null || typeof item.capsule_image_url === "string") ||
        !(item.source === "catalog" || item.source === "fallback")) {
      throw new Error("Invalid game search response");
    }
    return item as unknown as GameSearchResult;
  });
}

export async function getGamePreview(appId: string): Promise<SteamMetadata> {
  return parseSteamMetadata(await requestJson(
    `/api/games/preview?appid=${encodeURIComponent(appId)}`,
  ));
}

export async function getReviewLanguageCounts(
  appId: number,
): Promise<ReviewLanguageCount[]> {
  const payload: unknown = await requestJson(`/api/games/${appId}/review-languages`);
  if (!Array.isArray(payload) || !payload.every((item) => (
    isRecord(item)
    && typeof item.language === "string"
    && typeof item.review_count === "number"
    && Number.isInteger(item.review_count)
    && item.review_count >= 0
  ))) {
    throw new Error("Invalid review language response");
  }
  return payload as ReviewLanguageCount[];
}

export function parseSteamMetadata(payload: unknown): SteamMetadata {
  if (!isRecord(payload)) throw new Error("Invalid Steam metadata response");
  return parseMetadataRecord(payload);
}

function parseMetadataRecord(payload: Record<string, unknown>): SteamMetadata {
  if (
    typeof payload.app_id !== "number" || !Number.isInteger(payload.app_id) ||
    typeof payload.title !== "string" ||
    !(payload.developers === null || stringArray(payload.developers)) ||
    !(payload.capsule_image_url === null || typeof payload.capsule_image_url === "string") ||
    !(payload.release_date === null || typeof payload.release_date === "string") ||
    !["released", "coming_soon", "unknown"].includes(String(payload.release_status)) ||
    !(payload.review_count === null || (typeof payload.review_count === "number" && Number.isInteger(payload.review_count))) ||
    !(payload.source_status === "complete" || payload.source_status === "partial") ||
    !Array.isArray(payload.missing_fields) || !payload.missing_fields.every(isMissingMetadataField) ||
    !isRecord(payload.storefront) ||
    !["complete", "partial", "unavailable"].includes(String(payload.storefront_source_status)) ||
    !stringArray(payload.storefront_missing_fields)
  ) throw new Error("Invalid Steam metadata response");
  return {
    app_id: payload.app_id,
    title: payload.title,
    developers: payload.developers as string[] | null,
    capsule_image_url: payload.capsule_image_url as string | null,
    release_date: payload.release_date as string | null,
    release_status: payload.release_status as ReleaseStatus,
    review_count: payload.review_count as number | null,
    source_status: payload.source_status,
    missing_fields: payload.missing_fields as MissingMetadataField[],
    storefront: parseStorefront(payload.storefront),
    storefront_source_status: payload.storefront_source_status as SteamMetadata["storefront_source_status"],
    storefront_missing_fields: payload.storefront_missing_fields,
  };
}

function parseStorefront(value: Record<string, unknown>): SteamStorefront {
  const nullableStringArrays: string[] = ["publishers", "genres", "tags", "dlc_names", "package_names", "platforms"];
  const nullableStrings: string[] = ["short_description", "about_text", "supported_languages", "age_rating", "content_notes"];
  if (!nullableStringArrays.every((field) => value[field] === null || stringArray(value[field])) ||
      !nullableStrings.every((field) => value[field] === null || typeof value[field] === "string") ||
      !(value.is_free === null || typeof value.is_free === "boolean") ||
      !["dlc_app_ids", "demo_app_ids"].every((field) => value[field] === null || numberArray(value[field])) ||
      !(value.price === null || isPrice(value.price)) ||
      !(value.screenshot_urls === null || steamUrlArray(value.screenshot_urls)) ||
      !(value.features === null || (Array.isArray(value.features) && value.features.every(isFeature))) ||
      !(value.trailers === null || (Array.isArray(value.trailers) && value.trailers.every(isTrailer)))) {
    throw new Error("Invalid Steam storefront response");
  }
  return value as unknown as SteamStorefront;
}

function stringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function numberArray(value: unknown): value is number[] {
  return Array.isArray(value) && value.every((item) => typeof item === "number" && Number.isInteger(item));
}

function isPrice(value: unknown): boolean {
  return isRecord(value) && ["country_code", "currency", "initial_formatted", "final_formatted"].every((field) => typeof value[field] === "string") &&
    ["initial_minor", "final_minor", "discount_percent"].every((field) => typeof value[field] === "number");
}

function isFeature(value: unknown): boolean {
  return isRecord(value) && typeof value.name === "string" &&
    ["Play modes", "Input", "Steam features", "Platforms and accessibility"].includes(String(value.group)) &&
    ["supported", "partial", "not_supported", "unknown"].includes(String(value.state));
}

function isTrailer(value: unknown): boolean {
  return isRecord(value) && typeof value.name === "string" &&
    isSafeSteamUrl(value.thumbnail_url) && isSafeSteamUrl(value.video_url);
}

function steamUrlArray(value: unknown): boolean {
  return Array.isArray(value) && value.every(isSafeSteamUrl);
}

function isSafeSteamUrl(value: unknown): boolean {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "https:" &&
      (url.hostname === "steamstatic.com" || url.hostname.endsWith(".steamstatic.com"));
  } catch {
    return false;
  }
}
