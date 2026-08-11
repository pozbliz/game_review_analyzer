export interface StorageDiagnostics {
  database_path: string;
  database_bytes: number;
  game_dataset_count: number;
  report_version_count: number;
  review_revision_count: number;
  incomplete_job_count: number;
}

export async function getStorageDiagnostics(): Promise<StorageDiagnostics> {
  const response: Response = await fetch("/api/storage");
  if (!response.ok) throw new Error("Unable to load storage diagnostics");
  const payload: unknown = await response.json();
  if (!isRecord(payload) || typeof payload.database_path !== "string" ||
      !numbers(payload, [
        "database_bytes", "game_dataset_count", "report_version_count",
        "review_revision_count", "incomplete_job_count",
      ])) {
    throw new Error("Invalid storage diagnostics response");
  }
  return payload as unknown as StorageDiagnostics;
}

export async function deleteReport(reportId: string, confirmation: string): Promise<void> {
  await confirmedRequest(`/api/reports/${encodeURIComponent(reportId)}/delete`, confirmation);
}

export async function deleteGameDataset(appId: number, confirmation: string): Promise<void> {
  await confirmedRequest(`/api/games/${appId}/delete`, confirmation);
}

export async function deleteIncompleteJob(jobId: string, confirmation: string): Promise<void> {
  await confirmedRequest(`/api/jobs/${encodeURIComponent(jobId)}/delete`, confirmation);
}

async function confirmedRequest(path: string, confirmation: string): Promise<void> {
  const response: Response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmation }),
  });
  if (!response.ok) throw new Error("Deletion rejected");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function numbers(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every((field) => {
    const item: unknown = value[field];
    return typeof item === "number" && Number.isFinite(item);
  });
}
