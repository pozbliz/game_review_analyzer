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
  provider: string;
  model: string;
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

export interface RepresentativeEvidence {
  opinion_point_id: string;
  review_revision_id: string;
  excerpt: string;
  sentiment: "positive" | "negative" | "neutral";
}

export interface ReportTheme {
  theme_id: string;
  title: string;
  summary: string;
  polarity: ThemePolarity;
  primary_category: string;
  related_categories: string[];
  support: { count: number; percentage: number; denominator: number };
  below_threshold: boolean;
  evidence_count: number;
  representative_evidence: RepresentativeEvidence[];
  opposes_theme_id: string | null;
  cohort_comparison?: ThemeCohortComparison;
}

export interface ThemeCohortComparison {
  early: { count: number; percentage: number; denominator: number };
  recent: { count: number; percentage: number; denominator: number };
  percentage_point_change: number;
  direction: "appears_improved" | "mostly_unchanged" | "appears_worse" |
    "new_in_recent_reviews" | "no_longer_prominent";
}

export interface CohortScope {
  review_count: number;
  source_created_from: number;
  source_created_to: number;
}

export interface MixedReception {
  positive_theme_id: string;
  negative_theme_id: string;
  liked_count: number;
  disliked_count: number;
  mixed_count: number;
  opinionated_review_count: number;
  mentioned_review_count: number;
  scope_review_count: number;
  liked_percentage: number;
  disliked_percentage: number;
  mixed_percentage: number;
  mentioned_percentage: number;
}

export interface ReportSummary {
  report_version_id: string;
  game: { app_id: number; title: string };
  metadata: SteamMetadata;
  scope: {
    review_count: number;
    opinion_point_count: number;
    non_neutral_opinion_point_count: number;
    thresholds_calibrated: boolean;
    early?: CohortScope;
    recent?: CohortScope;
  };
  provenance: { provider: string; model: string; request_id: string; scope_sha256: string };
  positive_themes: ReportTheme[];
  negative_themes: ReportTheme[];
  technical_themes: ReportTheme[];
  mixed_reception: MixedReception[];
}

export interface EvidenceReview {
  review_revision_id: string;
  text: string;
  source_created_at: number;
  source_updated_at: number;
  recommended: boolean;
  votes_helpful: number;
  steam_purchase: boolean;
  received_for_free: boolean;
  written_during_early_access: boolean;
  playtime_forever_minutes: number;
  playtime_at_review_minutes: number | null;
}

export interface ThemeEvidenceItem {
  opinion_point_id: string;
  excerpt: string;
  sentiment: "positive" | "negative" | "neutral";
  subject: string;
  review: EvidenceReview;
}

export interface ThemeEvidence {
  theme_id: string;
  title: string;
  items: ThemeEvidenceItem[];
}

export interface ReportHistoryEntry {
  report_version_id: string;
  app_id: number;
  game_title: string;
  review_count: number;
  provider: string;
  model: string;
  thresholds_calibrated: boolean;
  created_at: string;
}

export async function getReport(reportId: string, query: string = ""): Promise<ReportSummary> {
  return parseReport(await requestJson(reportPath(reportId, query)));
}

export async function getTestReport(appId: number): Promise<AggregateReport> {
  return parseAggregateReport(await requestJson(`/api/games/${appId}/reports/test`));
}

export async function getMainReport(appId: number): Promise<AggregateReport> {
  return parseAggregateReport(await requestJson(`/api/games/${appId}/reports/main`));
}

export async function getAggregateThemeEvidence(
  appId: number,
  themeId: string,
  kind: "main" | "test" = "test",
): Promise<AggregateThemeEvidence> {
  return parseAggregateThemeEvidence(await requestJson(
    `/api/games/${appId}/reports/${kind}/themes/${encodeURIComponent(themeId)}/evidence`,
  ));
}

export async function getThemeEvidence(
  reportId: string,
  themeId: string,
  query: string = "",
): Promise<ThemeEvidence> {
  return parseThemeEvidence(await requestJson(
    `${reportPath(reportId, "")}/themes/${encodeURIComponent(themeId)}/evidence${query ? `?${query}` : ""}`,
  ));
}

function reportPath(reportId: string, query: string): string {
  const path: string = `/api/reports/${encodeURIComponent(reportId)}`;
  return query ? `${path}?${query}` : path;
}

export async function getReportHistory(appId: number): Promise<ReportHistoryEntry[]> {
  const payload: unknown = await requestJson(`/api/games/${appId}/reports`);
  if (!Array.isArray(payload)) throw new Error("Invalid report history response");
  return payload.map(parseHistoryEntry);
}

export async function getRecentReports(): Promise<ReportHistoryEntry[]> {
  const payload: unknown = await requestJson("/api/reports/recent");
  if (!Array.isArray(payload)) throw new Error("Invalid recent reports response");
  return payload.map(parseHistoryEntry);
}

async function requestJson(path: string): Promise<unknown> {
  const response: Response = await fetch(path);
  if (!response.ok) throw new Error(`Request failed: ${path}`);
  return response.json() as Promise<unknown>;
}

function parseReport(payload: unknown): ReportSummary {
  if (!isRecord(payload) || !isRecord(payload.game) || !isRecord(payload.scope) ||
      !isRecord(payload.provenance) || typeof payload.report_version_id !== "string" ||
      !isRecord(payload.metadata) ||
      typeof payload.game.app_id !== "number" || typeof payload.game.title !== "string" ||
      typeof payload.scope.review_count !== "number" ||
      typeof payload.scope.opinion_point_count !== "number" ||
      typeof payload.scope.non_neutral_opinion_point_count !== "number" ||
      typeof payload.scope.thresholds_calibrated !== "boolean" ||
      !strings(payload.provenance, ["provider", "model", "request_id", "scope_sha256"]) ||
      !Array.isArray(payload.positive_themes) || !Array.isArray(payload.negative_themes) ||
      !Array.isArray(payload.technical_themes) || !Array.isArray(payload.mixed_reception)) {
    throw new Error("Invalid report response");
  }
  return {
    report_version_id: payload.report_version_id,
    game: { app_id: payload.game.app_id, title: payload.game.title },
    metadata: parseSteamMetadata(payload.metadata),
    scope: {
      review_count: payload.scope.review_count,
      opinion_point_count: payload.scope.opinion_point_count,
      non_neutral_opinion_point_count: payload.scope.non_neutral_opinion_point_count,
      thresholds_calibrated: payload.scope.thresholds_calibrated,
      early: parseCohortScope(payload.scope.early),
      recent: parseCohortScope(payload.scope.recent),
    },
    provenance: payload.provenance as ReportSummary["provenance"],
    positive_themes: payload.positive_themes.map(parseTheme),
    negative_themes: payload.negative_themes.map(parseTheme),
    technical_themes: payload.technical_themes.map(parseTheme),
    mixed_reception: payload.mixed_reception.map(parseMixedReception),
  };
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
      !strings(payload, ["provider", "model"]) ||
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
    provider: payload.provider as string,
    model: payload.model as string,
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
      !Array.isArray(payload.reviews) || !payload.reviews.every((review) =>
        isRecord(review) && typeof review.review_revision_id === "number" &&
        typeof review.text === "string" && typeof review.recommended === "boolean" &&
        typeof review.votes_helpful === "number")) {
    throw new Error("Invalid aggregate Theme evidence response");
  }
  return payload as unknown as AggregateThemeEvidence;
}

function parseTheme(value: unknown): ReportTheme {
  if (!isRecord(value) || !isRecord(value.support) ||
      !strings(value, ["theme_id", "title", "summary", "primary_category"]) ||
      !(value.polarity === "positive" || value.polarity === "negative") ||
      !Array.isArray(value.related_categories) ||
      !value.related_categories.every((item) => typeof item === "string") ||
      !numbers(value.support, ["count", "percentage", "denominator"]) ||
      typeof value.below_threshold !== "boolean" ||
      typeof value.evidence_count !== "number" ||
      !Array.isArray(value.representative_evidence) ||
      !(value.opposes_theme_id === null || typeof value.opposes_theme_id === "string")) {
    throw new Error("Invalid report Theme response");
  }
  return {
    theme_id: value.theme_id as string,
    title: value.title as string,
    summary: value.summary as string,
    polarity: value.polarity,
    primary_category: value.primary_category as string,
    related_categories: value.related_categories as string[],
    support: value.support as ReportTheme["support"],
    below_threshold: value.below_threshold,
    evidence_count: value.evidence_count,
    representative_evidence: value.representative_evidence.map(parseRepresentativeEvidence),
    opposes_theme_id: value.opposes_theme_id,
    cohort_comparison: parseCohortComparison(value.cohort_comparison),
  };
}

function parseCohortScope(value: unknown): CohortScope | undefined {
  if (value === undefined || value === null) return undefined;
  if (!isRecord(value) || !numbers(value, [
    "review_count", "source_created_from", "source_created_to",
  ])) throw new Error("Invalid cohort scope response");
  return value as unknown as CohortScope;
}

function parseCohortComparison(value: unknown): ThemeCohortComparison | undefined {
  if (value === undefined || value === null) return undefined;
  const directions: string[] = [
    "appears_improved", "mostly_unchanged", "appears_worse",
    "new_in_recent_reviews", "no_longer_prominent",
  ];
  if (!isRecord(value) || !isRecord(value.early) || !isRecord(value.recent) ||
      !numbers(value.early, ["count", "percentage", "denominator"]) ||
      !numbers(value.recent, ["count", "percentage", "denominator"]) ||
      typeof value.percentage_point_change !== "number" ||
      !directions.includes(String(value.direction))) {
    throw new Error("Invalid cohort comparison response");
  }
  return value as unknown as ThemeCohortComparison;
}

function parseRepresentativeEvidence(value: unknown): RepresentativeEvidence {
  if (!isRecord(value) ||
      !strings(value, ["opinion_point_id", "review_revision_id", "excerpt"]) ||
      !["positive", "negative", "neutral"].includes(String(value.sentiment))) {
    throw new Error("Invalid representative evidence response");
  }
  return value as unknown as RepresentativeEvidence;
}

function parseMixedReception(value: unknown): MixedReception {
  const numericFields: string[] = [
    "liked_count", "disliked_count", "mixed_count", "opinionated_review_count",
    "mentioned_review_count", "scope_review_count", "liked_percentage",
    "disliked_percentage", "mixed_percentage", "mentioned_percentage",
  ];
  if (!isRecord(value) || !strings(value, ["positive_theme_id", "negative_theme_id"]) ||
      !numbers(value, numericFields)) {
    throw new Error("Invalid mixed reception response");
  }
  return value as unknown as MixedReception;
}

function parseThemeEvidence(payload: unknown): ThemeEvidence {
  if (!isRecord(payload) || !strings(payload, ["theme_id", "title"]) ||
      !Array.isArray(payload.items)) {
    throw new Error("Invalid Theme evidence response");
  }
  return {
    theme_id: payload.theme_id as string,
    title: payload.title as string,
    items: payload.items.map(parseEvidenceItem),
  };
}

function parseEvidenceItem(value: unknown): ThemeEvidenceItem {
  if (!isRecord(value) || !isRecord(value.review) ||
      !strings(value, ["opinion_point_id", "excerpt", "subject"]) ||
      !["positive", "negative", "neutral"].includes(String(value.sentiment)) ||
      !strings(value.review, ["review_revision_id", "text"]) ||
      !numbers(value.review, [
        "source_created_at", "source_updated_at", "votes_helpful",
        "playtime_forever_minutes",
      ]) || !(value.review.playtime_at_review_minutes === null ||
        typeof value.review.playtime_at_review_minutes === "number") || !booleans(value.review, [
        "recommended", "steam_purchase", "received_for_free", "written_during_early_access",
      ])) {
    throw new Error("Invalid complete evidence response");
  }
  return value as unknown as ThemeEvidenceItem;
}

function parseHistoryEntry(value: unknown): ReportHistoryEntry {
  if (!isRecord(value) ||
      !strings(value, ["report_version_id", "game_title", "provider", "model", "created_at"]) ||
      !numbers(value, ["app_id", "review_count"]) ||
      typeof value.thresholds_calibrated !== "boolean") {
    throw new Error("Invalid report history response");
  }
  return value as unknown as ReportHistoryEntry;
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

function booleans(value: Record<string, unknown>, fields: string[]): boolean {
  return fields.every((field) => typeof value[field] === "boolean");
}
import { parseSteamMetadata, SteamMetadata } from "./shell";
