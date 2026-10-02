import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
      created_at: "2026-09-30 04:06:47",
      kind: "test",
      game: { app_id: 1145350, title: "Hades II" },
      metadata: metadata(),
      scope: {
        review_count: 50,
        oldest_review_count: 25,
        newest_review_count: 25,
        oversized_review_count: 0,
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
    expect(screen.queryByText("gpt-5.6-luna")).not.toBeInTheDocument();
    expect(screen.queryByText("codex-cli")).not.toBeInTheDocument();
    expect(screen.queryByText("Provider")).not.toBeInTheDocument();
    expect(screen.queryByText("Model")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Responsive combat" })).toBeVisible();
    expect(screen.getByText("4 reviews · 8% total")).toBeVisible();
    expect(screen.getByText("Oldest 4% · Newest 12% · +8 percentage points")).toBeVisible();
    const toggle = screen.getByRole("button", { name: "Show review evidence for Responsive combat" });
    expect(toggle.querySelector(".aggregate-theme-chevron")).toBeVisible();
    fireEvent.click(toggle);

    const evidenceList = await screen.findByRole("region", { name: "Review evidence for Responsive combat" });
    const reviews = within(evidenceList).getAllByRole("article");
    expect(reviews[0]).toHaveTextContent("Most helpful review");
    expect(reviews[0]).toHaveTextContent("20 helpful votes");
    expect(reviews[1]).toHaveTextContent("Less helpful review");
    const firstReviewDetails: HTMLDetailsElement | null = reviews[0].querySelector("details");
    const firstReviewSummary: HTMLElement | null = reviews[0].querySelector("summary");
    expect(firstReviewDetails).toHaveAttribute("open");
    expect(firstReviewSummary).not.toBeNull();
    fireEvent.click(firstReviewSummary as HTMLElement);
    expect(firstReviewDetails).not.toHaveAttribute("open");
    expect(reviews[1].querySelector("details")).toHaveAttribute("open");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/reports/test/themes/responsive-combat/evidence",
    );

    fireEvent.click(screen.getByRole("button", { name: "Hide review evidence for Responsive combat" }));
    expect(screen.queryByRole("region", { name: "Review evidence for Responsive combat" })).not.toBeInTheDocument();
  });

  it("starts a 1,000-review Main Report extension beside the review count", async () => {
    const navigationMock = vi.spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function navigate(this: HTMLAnchorElement): void {
        expect(this.getAttribute("href")).toBe("/?appid=1145350");
      });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request, options) => {
      const url: string = request.toString();
      if (options?.method === "POST") {
        return new Response(JSON.stringify({
          id: "extension-1", app_id: 1145350, provider: "codex-cli",
          model: "gpt-5.6-luna", state: "queued", review_count: 1_000,
          cancel_requested: false, error_code: null, report_version_id: null,
          input_tokens: null, cached_input_tokens: null, output_tokens: null,
          extracted_review_count: 0, oversized_review_count: 0,
          report_kind: "main", phase: "queued",
        }), { status: 202 });
      }
      return new Response(JSON.stringify({
        schema_version: "3.0", report_id: "main-report",
        created_at: "2026-09-30 04:06:47", kind: "main",
        game: { app_id: 1145350, title: "Hades II" }, metadata: metadata(),
        scope: { review_count: 1_000, oldest_review_count: 500, newest_review_count: 500, oversized_review_count: 0 },
        provider: "codex-cli", model: "gpt-5.6-luna",
        positive_themes: [], negative_themes: [],
      }), { status: 200 });
    });

    render(<AggregateReportView appId={1145350} kind="main" />);
    const extendButton: HTMLElement = await screen.findByRole("button", { name: "Extend Report" });
    expect(extendButton.closest(".report-review-value")).toHaveTextContent("1000");
    fireEvent.click(extendButton);

    await waitFor(() => expect(navigationMock).toHaveBeenCalledOnce());
    expect(localStorage.getItem("active-analysis-run")).toBe("extension-1");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/reports/main/extend",
      { method: "POST" },
    );
  });

  it("shows the reservation code returned when extension conflicts", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request, options) => {
      if (options?.method === "POST") {
        return new Response(JSON.stringify({
          detail: { code: "main_report_analysis_active" },
        }), { status: 409 });
      }
      return new Response(JSON.stringify({
        schema_version: "3.0", report_id: "main-report",
        created_at: "2026-09-30 04:06:47", kind: "main",
        game: { app_id: 1145350, title: "Hades II" }, metadata: metadata(),
        scope: { review_count: 1_000, oldest_review_count: 500, newest_review_count: 500, oversized_review_count: 0 },
        provider: "codex-cli", model: "gpt-5.6-luna",
        positive_themes: [], negative_themes: [],
      }), { status: 200 });
    });

    render(<AggregateReportView appId={1145350} kind="main" />);
    fireEvent.click(await screen.findByRole("button", { name: "Extend Report" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Another analysis owns this report slot",
    );
  });

  it("deletes a report immediately from the bottom button", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request, options) => {
      if (options?.method === "POST") return new Response(null, { status: 204 });
      return new Response(JSON.stringify({
        schema_version: "3.0", report_id: "main-report",
        created_at: "2026-09-30 04:06:47", kind: "main",
        game: { app_id: 1145350, title: "Hades II" }, metadata: metadata(),
        scope: { review_count: 1_000, oldest_review_count: 500, newest_review_count: 500, oversized_review_count: 0 },
        provider: "codex-cli", model: "gpt-5.6-luna",
        positive_themes: [], negative_themes: [],
      }), { status: 200 });
    });
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValue(true);
    const navigationMock = vi.spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function navigate(this: HTMLAnchorElement): void {
        expect(this.getAttribute("href")).toBe("/?appid=1145350");
      });

    render(<AggregateReportView appId={1145350} kind="main" />);
    const deleteButton: HTMLElement = await screen.findByRole("button", { name: "Delete Report" });
    expect(deleteButton.closest(".report-delete")).toBe(document.querySelector("main")?.lastElementChild);
    fireEvent.click(deleteButton);

    await waitFor(() => expect(navigationMock).toHaveBeenCalledOnce());
    expect(confirmMock).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/reports/main-report/delete",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: "main-report" }),
      },
    );
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
