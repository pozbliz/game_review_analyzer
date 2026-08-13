import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    expect(screen.getByText("Early cohort")).toBeVisible();
    expect(screen.getByText("Recent cohort")).toBeVisible();
    expect(screen.getAllByText("2 reviews · 100% of 2")).toHaveLength(3);

    fireEvent.click(screen.getByRole("button", { name: /responsive combat/i }));
    expect(screen.getByText("Appears improved")).toBeVisible();
    expect(screen.getByText("-30.0 percentage points")).toBeVisible();
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
    expect(screen.getByText("Not recommended · Unknown at review · 0 helpful votes")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/reports/report-1/themes/responsive-combat/evidence",
    );
  });

  it("applies and resets temporary Evidence Filters", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => (
      request.toString().includes("/evidence") ? json(evidencePayload()) : reportFetch(request)
    ));
    render(<ReportView reportId="report-1" />);
    await screen.findByRole("heading", { name: "Hades II" });

    fireEvent.click(screen.getByText("Evidence filters"));
    fireEvent.change(screen.getByRole("combobox", { name: "Recommendation" }), {
      target: { value: "recommended" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Minimum hours" }), {
      target: { value: "2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/reports/report-1?recommendation=recommended&minimum_playtime_minutes=120",
    ));

    fireEvent.click(screen.getByRole("button", { name: /responsive combat/i }));
    fireEvent.click(screen.getByRole("button", { name: /view all 2 evidence/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/reports/report-1/themes/responsive-combat/evidence?recommendation=recommended&minimum_playtime_minutes=120",
    ));

    fetchMock.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Reset filters" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/reports/report-1"));
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

  it("shows grouped regional storefront details and explicit Steam-hosted media links", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(reportFetch);
    render(<ReportView reportId="report-1" />);

    expect(await screen.findByRole("heading", { name: "Storefront overview" })).toBeVisible();
    expect(screen.getByText("¥ 3,600 · JPY · JP")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Features" })).toBeVisible();
    const featureList = screen.getByRole("list", { name: "Features" });
    expect(within(featureList).getByText("Single-player")).toBeVisible();
    expect(within(featureList).getByText("Supported")).toBeVisible();
    const trailer = screen.getByRole("link", { name: "Play Early Access Showcase on Steam" });
    expect(trailer).toHaveAttribute("target", "_blank");
    expect(trailer).toHaveAttribute("rel", "noreferrer");
    expect(screen.queryByRole("video")).not.toBeInTheDocument();
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
    metadata: richMetadata(),
    scope: {
      review_count: 2,
      thresholds_calibrated: false,
      early: { review_count: 1, source_created_from: 1_600_000_000, source_created_to: 1_600_000_000 },
      recent: { review_count: 1, source_created_from: 1_700_000_000, source_created_to: 1_700_000_000 },
    },
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

function richMetadata(): object {
  return {
    ...metadataIdentity(),
    storefront: {
      publishers: ["Supergiant Games"], genres: ["Action", "Indie"],
      short_description: "Battle beyond the Underworld.", about_text: "Master dark sorcery.",
      tags: null,
      price: { country_code: "JP", currency: "JPY", initial_minor: 450000, final_minor: 360000, discount_percent: 20, initial_formatted: "¥ 4,500", final_formatted: "¥ 3,600" },
      is_free: false, dlc_app_ids: [2000001], dlc_names: ["Hades II Soundtrack"], demo_app_ids: [2000002],
      package_names: ["Hades II - ¥ 3,600"], platforms: ["Windows"],
      supported_languages: "English, Japanese", age_rating: "18", content_notes: "Fantasy violence",
      features: [{ name: "Single-player", group: "Play modes", state: "supported" }],
      screenshot_urls: ["https://shared.akamai.steamstatic.com/steam/apps/1145350/ss_1.jpg"],
      trailers: [{ name: "Early Access Showcase", thumbnail_url: "https://shared.akamai.steamstatic.com/steam/apps/1145350/movie.jpg", video_url: "https://video.akamai.steamstatic.com/store_trailers/1145350/movie.mp4" }],
    },
    storefront_source_status: "partial",
    storefront_missing_fields: ["tags"],
  };
}

function metadataIdentity(): object {
  return {
    app_id: 1145350, title: "Hades II", developers: ["Supergiant Games"],
    capsule_image_url: null, release_date: "6 May, 2024", release_status: "released",
    review_count: 48239, source_status: "partial", missing_fields: ["capsule_image_url"],
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
    below_threshold: false,
    evidence_count: 2,
    representative_evidence: [{
      opinion_point_id: `${themeId}-point-1`,
      review_revision_id: "review-1",
      excerpt,
      sentiment: polarity,
    }],
    opposes_theme_id: opposesThemeId,
    cohort_comparison: {
      early: { count: 1, percentage: 80, denominator: 1 },
      recent: { count: 1, percentage: 50, denominator: 1 },
      percentage_point_change: -30,
      direction: "appears_improved",
    },
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
    }, {
      opinion_point_id: "responsive-combat-point-2",
      excerpt: "Still responsive",
      sentiment: "positive",
      subject: "combat response",
      review: {
        review_revision_id: "review-2",
        text: "Still responsive.",
        source_created_at: 101,
        source_updated_at: 101,
        recommended: false,
        votes_helpful: 0,
        steam_purchase: true,
        received_for_free: false,
        written_during_early_access: false,
        playtime_forever_minutes: 60,
        playtime_at_review_minutes: null,
      },
    }],
  };
}
