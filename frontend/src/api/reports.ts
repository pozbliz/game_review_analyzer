import { parseSteamMetadata, SteamMetadata } from "./shell";

export type ThemePolarity = "positive" | "negative";

export interface AggregateTheme {
  theme_id: string;
  title: string;
  summary: string;
  polarity: ThemePolarity;
  support_count: number;
  total_support_percentage: number;
  oldest_support_percentage: number;
  newest_support_percentage: number;
  percentage_point_difference: number;
}

export interface AggregateReport {
  schema_version: "3.0";
  report_id: string;
  created_at: string;
  kind: "main" | "test";
  game: { app_id: number; title: string };
  metadata: SteamMetadata;
  scope: {
    review_count: number;
    oldest_review_count: number;
    newest_review_count: number;
    oversized_review_count: number;
  };
  unseen_review_count: number | null;
  positive_themes: AggregateTheme[];
  negative_themes: AggregateTheme[];
}

export interface AggregateEvidenceReview {
  review_revision_id: number;
  text: string;
  recommended: boolean;
  votes_helpful: number;
}

export interface AggregateThemeEvidence {
  theme_id: string;
  title: string;
  reviews: AggregateEvidenceReview[];
}

export async function getTestReport(appId: number): Promise<AggregateReport> {
  return getAggregateReport(`/api/games/${appId}/reports/test`);
}

export async function getMainReport(appId: number): Promise<AggregateReport> {
  return getAggregateReport(`/api/games/${appId}/reports/main`);
}

export async function getAggregateThemeEvidence(
  appId: number,
  themeId: string,
  kind: "main" | "test",
): Promise<AggregateThemeEvidence> {
  const path: string = `/api/games/${appId}/reports/${kind}/themes/` +
    `${encodeURIComponent(themeId)}/evidence`;
  const response: Response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return parseAggregateThemeEvidence(await response.json());
}

async function getAggregateReport(path: string): Promise<AggregateReport> {
  const response: Response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return parseAggregateReport(await response.json());
}

function parseAggregateReport(payload: unknown): AggregateReport {
  if (!isRecord(payload) || payload.schema_version !== "3.0" ||
      !["main", "test"].includes(String(payload.kind)) ||
      typeof payload.report_id !== "string" || typeof payload.created_at !== "string" ||
      !isRecord(payload.game) ||
      typeof payload.game.app_id !== "number" || typeof payload.game.title !== "string" ||
      !isRecord(payload.metadata) || !isRecord(payload.scope) ||
      !numbers(payload.scope, [
        "review_count", "oldest_review_count", "newest_review_count",
        "oversized_review_count",
      ]) ||
      !(payload.unseen_review_count === null ||
        typeof payload.unseen_review_count === "number") ||
      !Array.isArray(payload.positive_themes) || !Array.isArray(payload.negative_themes)) {
    throw new Error("Invalid aggregate report response");
  }
  return {
    schema_version: "3.0",
    report_id: payload.report_id,
    created_at: payload.created_at,
    kind: payload.kind as AggregateReport["kind"],
    game: { app_id: payload.game.app_id, title: payload.game.title },
    metadata: parseSteamMetadata(payload.metadata),
    scope: payload.scope as AggregateReport["scope"],
    unseen_review_count: payload.unseen_review_count as number | null,
    positive_themes: payload.positive_themes.map(parseAggregateTheme),
    negative_themes: payload.negative_themes.map(parseAggregateTheme),
  };
}

function parseAggregateTheme(value: unknown): AggregateTheme {
  if (!isRecord(value) ||
      !strings(value, ["theme_id", "title", "summary", "polarity"]) ||
      !["positive", "negative"].includes(String(value.polarity)) ||
      !numbers(value, [
        "support_count",
        "total_support_percentage",
        "oldest_support_percentage",
        "newest_support_percentage",
        "percentage_point_difference",
      ])) {
    throw new Error("Invalid aggregate Theme response");
  }
  return value as unknown as AggregateTheme;
}

function parseAggregateThemeEvidence(payload: unknown): AggregateThemeEvidence {
  if (!isRecord(payload) || !strings(payload, ["theme_id", "title"]) ||
      !Array.isArray(payload.reviews) || !payload.reviews.every((review: unknown) =>
        isRecord(review) && typeof review.review_revision_id === "number" &&
        typeof review.text === "string" && typeof review.recommended === "boolean" &&
        typeof review.votes_helpful === "number")) {
    throw new Error("Invalid aggregate Theme evidence response");
  }
  return payload as unknown as AggregateThemeEvidence;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function strings(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every((field) => typeof value[field] === "string");
}

function numbers(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every((field) => {
    const item: unknown = value[field];
    return typeof item === "number" && Number.isFinite(item);
  });
}
