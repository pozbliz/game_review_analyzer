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
  if (!response.ok) throw new Error(`Request failed: ${path}`);
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
