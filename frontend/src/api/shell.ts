export interface HealthResponse {
  status: "ok";
  service: "game-review-analyzer";
}

export interface PublicConfigResponse {
  environment: string;
  api_prefix: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
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
    typeof payload.api_prefix !== "string"
  ) {
    throw new Error("Invalid public configuration response");
  }
  return { environment: payload.environment, api_prefix: payload.api_prefix };
}
