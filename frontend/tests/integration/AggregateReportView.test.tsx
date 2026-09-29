import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AggregateReportView from "../../src/features/report/AggregateReportView";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("aggregate Test Report", () => {
  it("expands helpful-first review evidence and closes it again", async () => {
    const report = {
      schema_version: "3.0",
      report_id: "test-report",
      kind: "test",
      game: { app_id: 1145350, title: "Hades II" },
      metadata: metadata(),
      scope: {
        review_count: 50,
        oldest_review_count: 25,
        newest_review_count: 25,
      },
      provider: "codex-cli",
      model: "gpt-5.6-luna",
      positive_themes: [{
        theme_id: "responsive-combat",
        title: "Responsive combat",
        summary: "Players praise responsive combat.",
        polarity: "positive",
        support_count: 4,
        total_support_percentage: 8,
        oldest_support_percentage: 4,
        newest_support_percentage: 12,
        percentage_point_difference: 8,
      }],
      negative_themes: [],
    };
    const evidence = {
      theme_id: "responsive-combat",
      title: "Responsive combat",
      reviews: [
        { review_revision_id: 2, text: "Most helpful review", recommended: true, votes_helpful: 20 },
        { review_revision_id: 1, text: "Less helpful review", recommended: true, votes_helpful: 3 },
      ],
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      const payload: object = url.endsWith("/themes/responsive-combat/evidence")
        ? evidence
        : report;
      return new Response(JSON.stringify(payload), { status: 200 });
    });

    render(<AggregateReportView appId={1145350} />);

    expect(await screen.findByRole("heading", { name: "Hades II" })).toBeVisible();
    expect(screen.getByText("Test Report")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Responsive combat" })).toBeVisible();
    expect(screen.getByText("4 reviews · 8% total")).toBeVisible();
    expect(screen.getByText("Oldest 4% · Newest 12% · +8 percentage points")).toBeVisible();
    const toggle = screen.getByRole("button", { name: "Show review evidence for Responsive combat" });
    fireEvent.click(toggle);

    const evidenceList = await screen.findByRole("region", { name: "Review evidence for Responsive combat" });
    const reviews = within(evidenceList).getAllByRole("article");
    expect(reviews[0]).toHaveTextContent("Most helpful review");
    expect(reviews[0]).toHaveTextContent("20 helpful votes");
    expect(reviews[1]).toHaveTextContent("Less helpful review");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/reports/test/themes/responsive-combat/evidence",
    );

    fireEvent.click(screen.getByRole("button", { name: "Hide review evidence for Responsive combat" }));
    expect(screen.queryByRole("region", { name: "Review evidence for Responsive combat" })).not.toBeInTheDocument();
  });
});

function metadata(): object {
  return {
    app_id: 1145350,
    title: "Hades II",
    developers: ["Supergiant Games"],
    capsule_image_url: null,
    release_date: null,
    release_status: "unknown",
    review_count: 100,
    source_status: "complete",
    missing_fields: [],
    storefront: {
      publishers: null,
      genres: null,
      tags: null,
      dlc_names: null,
      package_names: null,
      platforms: null,
      short_description: null,
      about_text: null,
      supported_languages: null,
      age_rating: null,
      content_notes: null,
      is_free: null,
      dlc_app_ids: null,
      demo_app_ids: null,
      price: null,
      screenshot_urls: null,
      features: null,
      trailers: null,
    },
    storefront_source_status: "unavailable",
    storefront_missing_fields: [],
  };
}
