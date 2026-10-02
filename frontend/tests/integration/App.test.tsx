import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App, { analysisFailureMessage } from "../../src/app/App";

afterEach(() => {
  cleanup();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
  vi.restoreAllMocks();
});

describe("application shell", () => {
  it.each([
    ["steam_unavailable", "Steam refresh failed"],
    ["reservation_conflict", "Another analysis owns this report slot"],
    ["no_unseen_reviews", "No unseen usable reviews remain"],
    ["provider_nonzero_exit", "The analysis provider failed"],
    ["checkpoint_invalid", "Saved progress was invalid"],
    ["cancelled", "Analysis was cancelled"],
    ["internal_analysis_error", "internal error"],
  ])("maps %s to actionable recovery text", (code, expected) => {
    expect(analysisFailureMessage(code)).toContain(expected);
  });

  it("opens with the current-report workspace prompt", async () => {
    mockShell();

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Select a game" })).toBeVisible();
    expect(screen.queryByText(/Ollama|gpt-5\.6-luna/i)).not.toBeInTheDocument();
  });

  it("previews a game and lists only its current report slots", async () => {
    mockShell({ workspace: workspace(true, null, true, true) });

    render(<App />);
    await previewGame();

    expect(screen.getByRole("link", { name: /Test Report.*50 reviews/i })).toHaveAttribute(
      "href", "/test-reports/1145350",
    );
    expect(screen.getByRole("link", { name: /Main Report.*1,000 reviews/i })).toHaveAttribute(
      "href", "/main-reports/1145350",
    );
    expect(screen.queryByLabelText("Analysis provider")).not.toBeInTheDocument();
  });

  it("starts a Test Report with the selected visibility settings", async () => {
    const fetchMock = mockShell({
      workspace: workspace(true),
      analysis: { ...analysisRun("completed"), report_kind: "test", review_count: 50 },
    });

    render(<App />);
    await previewGame();
    fireEvent.change(screen.getByLabelText("Minimum support percentage"), {
      target: { value: "7.5" },
    });
    fireEvent.change(screen.getByLabelText("Maximum Themes per list"), {
      target: { value: "4" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Report" }));

    expect(await screen.findByRole("heading", { name: "Report complete" })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/reports/test",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          minimum_support_percentage: 7.5,
          maximum_headlines_per_polarity: 4,
        }),
      },
    );
  });

  it("starts a Main Report without provider or model controls", async () => {
    const fetchMock = mockShell({
      workspace: workspace(true),
      analysis: { ...analysisRun("queued"), report_kind: "main", review_count: 1_000 },
    });

    render(<App />);
    await previewGame();
    fireEvent.change(screen.getByLabelText("Analysis scope"), { target: { value: "500" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Report" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/reports/main",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(screen.queryByText(/gpt-5\.6-luna|Codex analysis/i)).not.toBeInTheDocument();
  });

  it("shows measured Steam refresh percentage during report analysis", async () => {
    localStorage.setItem("active-analysis-run", "analysis-1");
    mockShell({
      analysis: {
        ...analysisRun("running"),
        phase: "refreshing",
        refresh_imported_count: 1_500,
        refresh_target_count: 5_000,
      },
    });

    render(<App />);

    expect(await screen.findByText(/Refreshing Steam reviews/)).toHaveTextContent("30%");
    expect(screen.getByRole("progressbar")).toHaveAttribute("value", "1500");
    expect(screen.getByRole("progressbar")).toHaveAttribute("max", "5000");
  });

  it("starts a Full import when the selected game has no completed dataset", async () => {
    const fetchMock = mockShell({ workspace: workspace(false), importJob: job("queued", 0) });

    render(<App />);
    await previewGame();
    fireEvent.click(screen.getByRole("button", { name: "Create Report" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/imports/full",
      expect.objectContaining({ method: "POST" }),
    ));
    expect(await screen.findByRole("heading", { name: "Downloading reviews" })).toBeVisible();
  });
});

interface MockOptions {
  workspace?: object;
  analysis?: object;
  importJob?: object;
}

function mockShell(options: MockOptions = {}): ReturnType<typeof vi.spyOn> {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (request, init) => {
    const url: string = request.toString();
    if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
    if (url === "/api/config") return json(publicConfig());
    if (url === "/api/providers/codex-cli") return json(codexProvider());
    if (url === "/api/games/preview?appid=1145350") return json(metadata());
    if (url === "/api/games/1145350/workspace") {
      return json(options.workspace ?? workspace(false));
    }
    if (url === "/api/games/1145350/imports/full" && init?.method === "POST") {
      return json(options.importJob ?? job("queued", 0));
    }
    if (url.startsWith("/api/jobs/")) return json(options.importJob ?? job("queued", 0));
    if (url.startsWith("/api/games/1145350/reports/") && init?.method === "POST") {
      return json(options.analysis ?? analysisRun("queued"));
    }
    if (url.startsWith("/api/analysis-runs/")) {
      return json(options.analysis ?? analysisRun("running"));
    }
    return new Response("{}", { status: 404 });
  });
}

async function previewGame(): Promise<void> {
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("connected"));
  fireEvent.change(screen.getByRole("textbox", { name: /steam appid/i }), {
    target: { value: "1145350" },
  });
  fireEvent.click(screen.getByRole("button", { name: /preview game/i }));
  await screen.findByRole("heading", { name: "Hades II" });
}

function json(payload: object): Response {
  return new Response(JSON.stringify(payload), { status: 200 });
}

function publicConfig(): object {
  return {
    environment: "test",
    api_prefix: "/api",
    steam_country_code: "US",
    keyed_catalog_available: false,
  };
}

function codexProvider(): object {
  return {
    installed: true,
    authenticated: true,
    version: "codex-cli test",
    model: "gpt-5.6-luna",
    reasoning_effort: "low",
    processing_location: "external_cloud",
    cost_basis: "subscription_quota_unknown",
  };
}

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
    storefront: Object.fromEntries(storefrontFields().map((field) => [field, null])),
    storefront_source_status: "unavailable",
    storefront_missing_fields: storefrontFields(),
  };
}

function storefrontFields(): string[] {
  return [
    "publishers", "genres", "short_description", "about_text", "tags", "price",
    "is_free", "dlc_app_ids", "dlc_names", "demo_app_ids", "package_names", "platforms",
    "supported_languages", "age_rating", "content_notes", "features",
    "screenshot_urls", "trailers",
  ];
}

function job(state: string, importedCount: number): object {
  return {
    id: "job-1",
    app_id: 1145350,
    scope: "full",
    state,
    target_count: 5_000,
    imported_count: importedCount,
    cursor: "*",
    cancel_requested: false,
    error_code: null,
  };
}

function analysisRun(state: string): object {
  return {
    id: "analysis-1",
    app_id: 1145350,
    provider: "codex-cli",
    model: "gpt-5.6-luna",
    state,
    review_revision_ids: [1],
    review_count: 1,
    metric_policy: {
      minimum_support_count: 2,
      minimum_support_percentage: 5,
      technical_minimum_support_count: 2,
      technical_minimum_support_percentage: 5,
      maximum_headlines_per_polarity: 10,
    },
    cancel_requested: false,
    error_code: null,
    report_version_id: state === "completed" ? "report-1" : null,
    input_tokens: state === "completed" ? 120 : null,
    cached_input_tokens: state === "completed" ? 20 : null,
    output_tokens: state === "completed" ? 30 : null,
    extracted_review_count: state === "completed" ? 1 : 0,
    oversized_review_count: 0,
    report_kind: null,
    phase: state === "running" ? "extracting" : state,
    refresh_imported_count: null,
    refresh_target_count: null,
  };
}

function workspace(
  fullHistoryReady: boolean,
  latestAnalysisRun: object | null = null,
  testReportAvailable: boolean = false,
  mainReportAvailable: boolean = false,
): object {
  const availableReports: object[] = [];
  if (testReportAvailable) {
    availableReports.push({ kind: "test", review_count: 50, created_at: "2026-10-01 00:00:00" });
  }
  if (mainReportAvailable) {
    availableReports.push({ kind: "main", review_count: 1_000, created_at: "2026-10-02 00:00:00" });
  }
  return {
    full_history_ready: fullHistoryReady,
    latest_analysis_run: latestAnalysisRun,
    test_report_available: testReportAvailable,
    main_report_available: mainReportAvailable,
    available_reports: availableReports,
  };
}
