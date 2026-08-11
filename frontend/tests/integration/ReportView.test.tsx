import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ReportView from "../../src/features/report/ReportView";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("report exploration", () => {
  it("shows ranked design and Technical Themes with one inline detail at a time", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json(reportPayload()));

    render(<ReportView reportId="report-1" />);

    expect(await screen.findByRole("heading", { name: "Hades II" })).toBeVisible();
    expect(screen.getByText("Provisional thresholds")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Positive themes" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Negative themes" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Technical themes" })).toBeVisible();
    expect(screen.getAllByText("2 reviews · 100% of 2")).toHaveLength(3);

    fireEvent.click(screen.getByRole("button", { name: /responsive combat/i }));
    expect(screen.getByText("Players praise immediate combat response.")).toBeVisible();
    expect(screen.getByText(/Combat is responsive/)).toBeVisible();
    expect(screen.getByText(/2 liked · 0 disliked · 0 mixed/i)).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /^View opposing: Sluggish combat$/i }));
    expect(screen.queryByText("Players praise immediate combat response.")).not.toBeInTheDocument();
    expect(screen.getByText("Players report delayed combat response.")).toBeVisible();
  });

  it("filters by category and drills from representative evidence into full reviews", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      return url.endsWith("/evidence") ? json(evidencePayload()) : json(reportPayload());
    });
    render(<ReportView reportId="report-1" />);
    await screen.findByRole("heading", { name: "Hades II" });

    fireEvent.change(screen.getByRole("combobox", { name: "Category" }), {
      target: { value: "Visuals and audio" },
    });
    expect(screen.queryByRole("button", { name: /responsive combat/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /audio stutter/i })).toBeVisible();

    fireEvent.change(screen.getByRole("combobox", { name: "Category" }), {
      target: { value: "All categories" },
    });
    fireEvent.click(screen.getByRole("button", { name: /responsive combat/i }));
    fireEvent.click(screen.getByRole("button", { name: /view all 2 evidence/i }));

    expect(await screen.findByText("Combat is responsive.")).toBeVisible();
    expect(screen.getByText("Recommended · 2h at review · 3 helpful votes")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/reports/report-1/themes/responsive-combat/evidence",
    );
  });
});

function json(payload: object): Response {
  return new Response(JSON.stringify(payload), { status: 200 });
}

function reportPayload(): object {
  const positive = theme(
    "responsive-combat",
    "Responsive combat",
    "Players praise immediate combat response.",
    "positive",
    "Gameplay and mechanics",
    "sluggish-combat",
    "Combat is responsive",
  );
  const negative = theme(
    "sluggish-combat",
    "Sluggish combat",
    "Players report delayed combat response.",
    "negative",
    "Gameplay and mechanics",
    "responsive-combat",
    "Inputs feel delayed",
  );
  const technical = theme(
    "audio-stutter",
    "Audio stutter",
    "Players report intermittent audio stutter.",
    "negative",
    "Visuals and audio",
    null,
    "Audio stutters",
  );
  return {
    report_version_id: "report-1",
    game: { app_id: 1145350, title: "Hades II" },
    scope: { review_count: 2, thresholds_calibrated: false },
    provenance: {
      provider: "manual-codex",
      model: "fixture-model",
      request_id: "request-1",
      scope_sha256: "a".repeat(64),
    },
    positive_themes: [positive],
    negative_themes: [negative],
    technical_themes: [technical],
    mixed_reception: [{
      positive_theme_id: "responsive-combat",
      negative_theme_id: "sluggish-combat",
      liked_count: 2,
      disliked_count: 0,
      mixed_count: 0,
      opinionated_review_count: 2,
      mentioned_review_count: 2,
      scope_review_count: 2,
      liked_percentage: 100,
      disliked_percentage: 0,
      mixed_percentage: 0,
      mentioned_percentage: 100,
    }],
  };
}

function theme(
  themeId: string,
  title: string,
  summary: string,
  polarity: string,
  primaryCategory: string,
  opposesThemeId: string | null,
  excerpt: string,
): object {
  return {
    theme_id: themeId,
    title,
    summary,
    polarity,
    primary_category: primaryCategory,
    related_categories: [],
    support: { count: 2, percentage: 100, denominator: 2 },
    evidence_count: 2,
    representative_evidence: [{
      opinion_point_id: `${themeId}-point-1`,
      review_revision_id: "review-1",
      excerpt,
      sentiment: polarity,
    }],
    opposes_theme_id: opposesThemeId,
  };
}

function evidencePayload(): object {
  return {
    theme_id: "responsive-combat",
    title: "Responsive combat",
    items: [{
      opinion_point_id: "responsive-combat-point-1",
      excerpt: "Combat is responsive",
      sentiment: "positive",
      subject: "combat response",
      review: {
        review_revision_id: "review-1",
        text: "Combat is responsive.",
        source_created_at: 100,
        source_updated_at: 100,
        recommended: true,
        votes_helpful: 3,
        steam_purchase: true,
        received_for_free: false,
        written_during_early_access: false,
        playtime_forever_minutes: 180,
        playtime_at_review_minutes: 120,
      },
    }],
  };
}
