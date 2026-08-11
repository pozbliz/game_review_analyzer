export interface HealthResponse {
  status: "ok";
  service: "game-review-analyzer";
}

export interface PublicConfigResponse {
  environment: string;
  api_prefix: "/api";
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

async function requestJson(path: string): Promise<unknown> {
  const response: Response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return response.json() as Promise<unknown>;
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
    payload.api_prefix !== "/api"
  ) {
    throw new Error("Invalid public configuration response");
  }
  return { environment: payload.environment, api_prefix: payload.api_prefix };
}

export async function getGamePreview(appId: string): Promise<SteamMetadata> {
  const payload: unknown = await requestJson(
    `/api/games/preview?appid=${encodeURIComponent(appId)}`,
  );
  if (
    !isRecord(payload) ||
    typeof payload.app_id !== "number" ||
    !Number.isInteger(payload.app_id) ||
    typeof payload.title !== "string" ||
    !(
      payload.developers === null ||
      (Array.isArray(payload.developers) &&
        payload.developers.every((developer) => typeof developer === "string"))
    ) ||
    !(payload.capsule_image_url === null || typeof payload.capsule_image_url === "string") ||
    !(payload.release_date === null || typeof payload.release_date === "string") ||
    !(
      payload.release_status === "released" ||
      payload.release_status === "coming_soon" ||
      payload.release_status === "unknown"
    ) ||
    !(
      payload.review_count === null ||
      (typeof payload.review_count === "number" && Number.isInteger(payload.review_count))
    ) ||
    !(payload.source_status === "complete" || payload.source_status === "partial") ||
    !Array.isArray(payload.missing_fields) ||
    !payload.missing_fields.every(isMissingMetadataField)
  ) {
    throw new Error("Invalid Steam metadata response");
  }
  return {
    app_id: payload.app_id,
    title: payload.title,
    developers: payload.developers,
    capsule_image_url: payload.capsule_image_url,
    release_date: payload.release_date,
    release_status: payload.release_status,
    review_count: payload.review_count,
    source_status: payload.source_status,
    missing_fields: payload.missing_fields,
  };
}
