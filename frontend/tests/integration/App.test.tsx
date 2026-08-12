import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../../src/app/App";

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("application shell", () => {
  it("reports backend health after validating the shell API contracts", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") {
        return new Response(
          JSON.stringify({ status: "ok", service: "game-review-analyzer" }),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify(publicConfig()),
        { status: 200 },
      );
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("connected"));
    expect(fetchMock).toHaveBeenCalledWith("/api/health");
    expect(fetchMock).toHaveBeenCalledWith("/api/config");
    expect(screen.getByRole("heading", { name: /select the game to analyze/i })).toBeVisible();
  });

  it("rejects an invalid public configuration payload", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      return url === "/api/health"
        ? new Response(
            JSON.stringify({ status: "ok", service: "game-review-analyzer" }),
            { status: 200 },
          )
        : new Response(JSON.stringify({ environment: "test" }), { status: 200 });
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("unavailable"));
  });

  it("previews a partial game and labels unavailable identity fields", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") {
        return new Response(
          JSON.stringify({ status: "ok", service: "game-review-analyzer" }),
          { status: 200 },
        );
      }
      if (url === "/api/config") {
        return new Response(
          JSON.stringify(publicConfig()),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify({
          app_id: 1145350,
          title: "Hades II",
          developers: ["Supergiant Games"],
          capsule_image_url: null,
          release_date: null,
          release_status: "unknown",
          review_count: null,
          source_status: "partial",
          missing_fields: [
            "capsule_image_url",
            "release_date",
            "release_status",
            "review_count",
          ],
          storefront: emptyStorefront(),
          storefront_source_status: "unavailable",
          storefront_missing_fields: storefrontFields(),
        }),
        { status: 200 },
      );
    });

    render(<App />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("connected"));

    fireEvent.change(screen.getByRole("textbox", { name: /steam appid/i }), {
      target: { value: "1145350" },
    });
    fireEvent.click(screen.getByRole("button", { name: /preview game/i }));

    expect(await screen.findByRole("heading", { name: "Hades II" })).toBeVisible();
    expect(screen.getByText("Supergiant Games")).toBeVisible();
    expect(screen.getAllByText("Unknown / unavailable")).toHaveLength(3);
    expect(screen.getByRole("button", { name: "Create report" })).toBeEnabled();
  });

  it("searches by game name and previews the selected Steam result", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json({ environment: "test", api_prefix: "/api", steam_country_code: "JP", keyed_catalog_available: true });
      if (url === "/api/games/search?q=Hades%202") return json([{
        app_id: 1145350,
        title: "Hades II",
        capsule_image_url: null,
        source: "catalog",
      }]);
      return json(metadata());
    });

    render(<App />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("connected"));
    fireEvent.change(screen.getByRole("textbox", { name: "Game name" }), {
      target: { value: "Hades 2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search games" }));
    fireEvent.click(await screen.findByRole("button", { name: /Hades II.*AppID 1145350/i }));

    expect(await screen.findByRole("heading", { name: "Hades II" })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("/api/games/preview?appid=1145350");
  });

  it("starts a Quick import and exposes durable progress and cancellation", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request, options) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url.startsWith("/api/games/preview")) return json(metadata());
      if (url === "/api/games/1145350/imports/quick") {
        expect(options).toMatchObject({ method: "POST", body: JSON.stringify({ target_count: 5000 }) });
        return json(job("queued", 0));
      }
      if (url === "/api/jobs/job-1/cancel") return json(job("cancelled", 200));
      if (url === "/api/jobs/job-1/delete") return new Response(null, { status: 204 });
      return json(job("running", 200));
    });

    render(<App />);
    await previewGame();
    fireEvent.click(screen.getByRole("button", { name: "Create report" }));

    expect(await screen.findByText("200 of 5,000 reviews")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Cancel import" }));
    expect(await screen.findByText("Import cancelled")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Type job-1 to delete this incomplete job"), {
      target: { value: "job-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Delete incomplete job" }));
    expect(await screen.findByText("Incomplete job deleted")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-1/delete",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: "job-1" }),
      },
    );
  });

  it("discloses Codex CLI cloud processing and unknown subscription quota", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json({
        installed: true,
        authenticated: true,
        version: "codex-cli 0.147.0",
        model: "gpt-5.6-luna",
        reasoning_effort: "medium",
        processing_location: "external_cloud",
        cost_basis: "subscription_quota_unknown",
      });
      return json(metadata());
    });

    render(<App />);
    await previewGame();

    expect(screen.getByText("Codex CLI ready")).toBeVisible();
    expect(screen.getByText("GPT-5.6 Luna · medium reasoning")).toBeVisible();
    expect(screen.getByText(/review text is sent to openai/i)).toBeVisible();
    expect(screen.getByText(/remaining subscription quota and dollar cost are unavailable/i)).toBeVisible();
  });

  it("starts Codex analysis after import and links the completed report", async () => {
    let analysisPolls = 0;
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url.startsWith("/api/games/preview")) return json(metadata());
      if (url === "/api/games/1145350/imports/quick") return json(job("completed", 5000));
      if (url === "/api/games/1145350/analyses/codex-cli") return json(analysisRun("queued"));
      analysisPolls += 1;
      return json(analysisRun(analysisPolls > 1 ? "completed" : "running"));
    });

    render(<App />);
    await previewGame();
    fireEvent.click(screen.getByRole("button", { name: "Create report" }));
    fireEvent.click(await screen.findByRole("button", { name: "Analyze with Codex CLI" }));

    const link = await screen.findByRole("link", { name: "View report" });
    expect(link).toHaveAttribute("href", "/reports/report-1");
    expect(screen.getByText(/120 input and 30 output tokens/i)).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/analyses/codex-cli",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("retries a failed Quick import", async () => {
    let progressRequests = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url.startsWith("/api/games/preview")) return json(metadata());
      if (url === "/api/games/1145350/imports/quick") return json(job("queued", 0));
      if (url === "/api/jobs/job-1/retry") return json(job("queued", 0));
      progressRequests += 1;
      return json(progressRequests === 1 ? job("failed", 0) : job("completed", 5000));
    });

    render(<App />);
    await previewGame();
    fireEvent.click(screen.getByRole("button", { name: "Create report" }));
    fireEvent.click(await screen.findByRole("button", { name: "Retry import" }));

    expect(await screen.findByText("Import complete")).toBeVisible();
  });

  it("reattaches to durable import progress after a browser refresh", async () => {
    localStorage.setItem("active-import-job", "job-1");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      return json(job("running", 200));
    });

    render(<App />);

    expect(await screen.findByText("Downloading reviews")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/job-1");
  });
});

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
    version: "codex-cli 0.147.0",
    model: "gpt-5.6-luna",
    reasoning_effort: "medium",
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
    review_count: null,
    source_status: "partial",
    missing_fields: ["capsule_image_url", "release_date", "release_status", "review_count"],
    storefront: emptyStorefront(),
    storefront_source_status: "unavailable",
    storefront_missing_fields: storefrontFields(),
  };
}

function emptyStorefront(): object {
  return Object.fromEntries(storefrontFields().map((field) => [field, null]));
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
    scope: "quick",
    state,
    target_count: 5000,
    imported_count: importedCount,
    cursor: "*",
    cancel_requested: false,
    error_code: state === "failed" ? "steam_unavailable" : null,
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
      minimum_support_percentage: 1,
      technical_minimum_support_count: 2,
      technical_minimum_support_percentage: 1,
      maximum_headlines_per_polarity: 10,
    },
    cancel_requested: false,
    error_code: null,
    report_version_id: state === "completed" ? "report-1" : null,
    input_tokens: state === "completed" ? 120 : null,
    cached_input_tokens: state === "completed" ? 20 : null,
    output_tokens: state === "completed" ? 30 : null,
  };
}
