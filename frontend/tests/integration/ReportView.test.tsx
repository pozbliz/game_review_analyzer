import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ReportView from "../../src/features/report/ReportView";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("report exploration", () => {
  it("shows ranked design and Technical Themes with one inline detail at a time", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(reportFetch);

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
      if (url.endsWith("/evidence")) return json(evidencePayload());
      return reportFetch(request);
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

  it("starts refresh and exposes immutable report history with failure recovery", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (request, options) => {
        const url: string = request.toString();
        if (url.endsWith("/refreshes")) return json(jobPayload("failed"));
        if (url.endsWith("/retry")) return json(jobPayload("queued"));
        if (url.endsWith("/api/jobs/refresh-job")) return json(jobPayload("completed"));
        return reportFetch(request, options);
      },
    );
    render(<ReportView reportId="report-1" />);

    expect(await screen.findByRole("heading", { name: "Hades II" })).toBeVisible();
    expect(await screen.findByText("Report history (2)")).toBeVisible();
    expect(screen.getByRole("link", { name: /report-2/i })).toHaveAttribute(
      "href",
      "/reports/report-2",
    );

    fireEvent.click(screen.getByRole("button", { name: "Refresh reviews" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry refresh" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/refresh-job/retry",
      { method: "POST" },
    ));
  });

  it("cancels a running refresh without changing the displayed report", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (request) => {
        const url: string = request.toString();
        if (url.endsWith("/refreshes")) return json(jobPayload("running"));
        if (url.endsWith("/cancel")) return json(jobPayload("cancelled"));
        if (url.endsWith("/api/jobs/refresh-job")) return json(jobPayload("running"));
        return reportFetch(request);
      },
    );
    render(<ReportView reportId="report-1" />);
    await screen.findByRole("heading", { name: "Hades II" });

    fireEvent.click(screen.getByRole("button", { name: "Refresh reviews" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancel refresh" }));

    expect(await screen.findByText("Refresh cancelled. Existing reports are unchanged.")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/refresh-job/cancel",
      { method: "POST" },
    );
  });

  it("starts explicit Full import and reconciliation maintenance jobs", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (request) => {
        const url: string = request.toString();
        if (url.endsWith("/imports/full")) return json(jobPayload("completed", "full"));
        if (url.endsWith("/reconciliations")) {
          return json(jobPayload("completed", "reconciliation"));
        }
        return reportFetch(request);
      },
    );
    render(<ReportView reportId="report-1" />);
    await screen.findByRole("heading", { name: "Hades II" });

    fireEvent.click(screen.getByText("Dataset maintenance"));
    fireEvent.click(screen.getByRole("button", { name: "Start Full import" }));
    expect(await screen.findByText(/Full import complete/i)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Reconcile deleted reviews" }));
    expect(await screen.findByText(/Reconciliation complete/i)).toBeVisible();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/imports/full",
      { method: "POST" },
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/reconciliations",
      { method: "POST" },
    );
  });
});

function json(payload: object): Response {
  return new Response(JSON.stringify(payload), { status: 200 });
}

async function reportFetch(request: RequestInfo | URL, _options?: RequestInit): Promise<Response> {
  const url: string = request.toString();
  return url.endsWith("/games/1145350/reports")
    ? json(historyPayload())
    : json(reportPayload());
}

function historyPayload(): object[] {
  return ["report-2", "report-1"].map((reportId) => ({
    report_version_id: reportId,
    app_id: 1145350,
    game_title: "Hades II",
    review_count: 2,
    provider: "manual-codex",
    model: "fixture-model",
    thresholds_calibrated: false,
    created_at: "2026-08-11 12:00:00",
  }));
}

function jobPayload(
  state: "queued" | "running" | "completed" | "failed" | "cancelled",
  scope: "refresh" | "full" | "reconciliation" = "refresh",
): object {
  return {
    id: "refresh-job",
    app_id: 1145350,
    scope,
    state,
    target_count: 5000,
    imported_count: 0,
    cursor: "*",
    cancel_requested: false,
    error_code: state === "failed" ? "steam_unavailable" : null,
  };
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
