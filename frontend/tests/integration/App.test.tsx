import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../../src/app/App";
import { SteamMetadata } from "../../src/api/shell";
import StorefrontOverview from "../../src/features/game/StorefrontOverview";

afterEach(() => {
  cleanup();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
  vi.restoreAllMocks();
});

describe("application shell", () => {
  it("shows recent saved reports beside game search", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/reports/recent") {
        return json([{ ...historyEntry("recent-report", 1145350), game_title: "Hades II" }]);
      }
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      return json(ollamaProvider());
    });

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Recent reports" })).toBeVisible();
    expect(screen.getByRole("link", { name: /Hades II/i })).toHaveAttribute(
      "href",
      "/reports/recent-report",
    );
    expect(screen.getByRole("heading", { name: /select the game to analyze/i })).toBeVisible();
  });

  it("keeps terminal background work out of the initial catalog", async () => {
    localStorage.setItem("active-import-job", "job-1");
    localStorage.setItem("active-analysis-run", "analysis-1");
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/reports/recent") return json([]);
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/jobs/job-1") return json(job("cancelled", 10));
      return json(analysisRun("cancelled"));
    });

    render(<App />);

    await waitFor(() => {
      expect(localStorage.getItem("active-import-job")).toBeNull();
      expect(localStorage.getItem("active-analysis-run")).toBeNull();
    });
    expect(screen.getByRole("heading", { name: "Recent reports" })).toBeVisible();
    expect(screen.queryByText("Import cancelled")).not.toBeInTheDocument();
  });

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
      if (url === "/api/games/1145350/reports") return json([]);
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

  it("surfaces dated saved reports before new report controls", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/1145350/reports") return json([
        {
          report_version_id: "report-latest",
          app_id: 1145350,
          game_title: "Hades II",
          review_count: 50,
          provider: "ollama",
          model: "qwen3.5:4b",
          thresholds_calibrated: false,
          created_at: "2026-08-14 12:00:00",
        },
        {
          report_version_id: "report-older",
          app_id: 1145350,
          game_title: "Hades II",
          review_count: 5000,
          provider: "codex-cli",
          model: "gpt-5.6-luna",
          thresholds_calibrated: false,
          created_at: "2026-08-12 12:00:00",
        },
      ]);
      return json(metadata());
    });

    render(<App />);
    await previewGame();

    expect(await screen.findByRole("link", { name: "Open latest report" })).toHaveAttribute(
      "href",
      "/reports/report-latest",
    );
    expect(screen.getByText(/Aug 12, 2026.*Codex CLI.*gpt-5.6-luna/i)).toBeVisible();
    expect(screen.getByRole("button", { name: "Create new report" })).toBeEnabled();
    expect(fetchMock).toHaveBeenCalledWith("/api/games/1145350/reports");
  });

  it("does not start a Full import when saved report discovery fails", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/1145350/reports") {
        return new Response("{}", { status: 503 });
      }
      return json(metadata());
    });

    render(<App />);
    await previewGame();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unable to load saved reports",
    );
    expect(screen.getByRole("button", { name: "Create report" })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/games/1145350/imports/full",
      expect.anything(),
    );
  });

  it("waits for saved report discovery before enabling report creation", async () => {
    let resolveHistory: (response: Response) => void = () => undefined;
    const historyResponse = new Promise<Response>((resolve) => { resolveHistory = resolve; });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/1145350/reports") return historyResponse;
      return json(metadata());
    });

    render(<App />);
    await previewGame();

    expect(screen.getByRole("button", { name: "Create report" })).toBeDisabled();
    resolveHistory(json([]));
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Create report" })).toBeEnabled();
    });
  });

  it("ignores saved report history from an earlier game selection", async () => {
    let resolveFirstHistory: (response: Response) => void = () => undefined;
    const firstHistory = new Promise<Response>((resolve) => { resolveFirstHistory = resolve; });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/111/reports") return firstHistory;
      if (url === "/api/games/222/reports") return json([historyEntry("report-222", 222)]);
      if (url === "/api/games/preview?appid=111") {
        return json({ ...metadata(), app_id: 111, title: "First game" });
      }
      return json({ ...metadata(), app_id: 222, title: "Second game" });
    });

    render(<App />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("connected"));
    await selectAppId("111");
    expect(await screen.findByRole("heading", { name: "First game" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Game search" }));
    await selectAppId("222");
    expect(await screen.findByRole("link", { name: "Open latest report" })).toHaveAttribute(
      "href",
      "/reports/report-222",
    );

    await act(async () => {
      resolveFirstHistory(json([historyEntry("report-111", 111)]));
    });
    expect(screen.getByRole("link", { name: "Open latest report" })).toHaveAttribute(
      "href",
      "/reports/report-222",
    );
  });

  it("creates another report from retained reviews without a Full import", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/1145350/reports") return json([{
        report_version_id: "report-latest",
        app_id: 1145350,
        game_title: "Hades II",
        review_count: 5000,
        provider: "codex-cli",
        model: "gpt-5.6-luna",
        thresholds_calibrated: false,
        created_at: "2026-08-14 12:00:00",
      }]);
      if (url === "/api/games/1145350/analyses/codex-cli") {
        return json(analysisRun("completed"));
      }
      if (url === "/api/games/1145350/imports/full") return json(job("completed", 5000, "full"));
      return json(metadata());
    });

    render(<App />);
    await previewGame();
    fireEvent.click(await screen.findByRole("button", { name: "Create new report" }));

    expect(await screen.findByRole("heading", { name: "Report complete" })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/analyses/codex-cli",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/games/1145350/imports/full",
      expect.anything(),
    );
  });

  it("creates the first report from a completed Game Dataset without another import", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/1145350/reports") return json([]);
      if (url === "/api/games/1145350/workspace") return json(workspace(true));
      if (url === "/api/games/1145350/analyses/codex-cli") {
        return json(analysisRun("completed"));
      }
      return json(metadata());
    });

    render(<App />);
    await previewGame();
    fireEvent.click(await screen.findByRole("button", { name: "Create report" }));

    expect(await screen.findByRole("heading", { name: "Report complete" })).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/games/1145350/imports/full",
      expect.anything(),
    );
  });

  it("restores the latest resumable analysis when its game is selected", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/1145350/reports") return json([]);
      if (url === "/api/games/1145350/workspace") {
        return json(workspace(true, analysisRun("cancelled")));
      }
      return json(metadata());
    });

    render(<App />);
    await previewGame();

    expect(await screen.findByRole("heading", { name: "Analysis cancelled" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Resume analysis" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Choose different provider" }));
    expect(screen.getByLabelText("Analysis provider")).toBeVisible();
  });

  it("moves from game search to full-width details and back", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      return json(metadata());
    });

    render(<App />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("connected"));

    const selectionPanel = screen.getByRole("region", { name: /select the game to analyze/i });
    fireEvent.change(screen.getByRole("textbox", { name: /steam appid/i }), {
      target: { value: "1145350" },
    });
    fireEvent.click(screen.getByRole("button", { name: /preview game/i }));

    expect(await screen.findByRole("heading", { name: "Hades II" })).toBeVisible();
    expect(screen.queryByText("CONFIRM IDENTITY")).not.toBeInTheDocument();
    expect(selectionPanel).not.toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Game search" }));
    expect(selectionPanel).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Hades II" })).not.toBeInTheDocument();
  });

  it("opens a selected game from a new-report catalog link", async () => {
    window.history.replaceState({}, "", "/?appid=1145350");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url: string = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url === "/api/games/1145350/reports") return json([]);
      return json(metadata());
    });

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Hades II" })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith("/api/games/preview?appid=1145350");
  });

  it("presents storefront tags and feature support as scan-friendly lists", () => {
    const richMetadata: SteamMetadata = {
      ...metadata(),
      storefront: {
        ...emptyStorefront(),
        tags: ["Action", "Roguelike"],
        supported_languages: "English *, French, Spanish - Spain, Ukrainian * languages with full audio support",
        screenshot_urls: ["https://example.com/one.jpg", "https://example.com/two.jpg"],
        features: [
          { name: "Windows", group: "Platforms and accessibility", state: "supported" },
          { name: "Linux", group: "Platforms and accessibility", state: "not_supported" },
        ],
      },
    } as SteamMetadata;

    render(<StorefrontOverview metadata={richMetadata} />);

    expect(screen.queryByText("STEAM SNAPSHOT")).not.toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Tags" })).getByText("Action")).toBeVisible();
    const featureList = screen.getByRole("list", { name: "Features" });
    expect(within(featureList).getByText("Windows")).toBeVisible();
    expect(within(featureList).getByText("Supported")).toBeVisible();
    expect(within(featureList).getByText("Not supported")).toBeVisible();
    const fullAudio = screen.getByRole("list", { name: "Full audio" });
    expect(within(fullAudio).getByText("English")).toBeVisible();
    expect(within(fullAudio).getByText("Ukrainian")).toBeVisible();
    const interfaceLanguages = screen.getByRole("list", { name: "Interface and subtitles" });
    expect(within(interfaceLanguages).getByText("French")).toBeVisible();
    expect(within(interfaceLanguages).getByText("Spanish (Spain)")).toBeVisible();
    expect(screen.queryByText(/languages with full audio support/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Enlarge Hades II Steam screenshot 1" }));
    const firstDialog = screen.getByRole("dialog", { name: "Hades II screenshot 1 of 2" });
    expect(firstDialog).toBeVisible();
    expect(within(firstDialog).getByRole("img", { name: "Hades II Steam screenshot 1" }))
      .toHaveAttribute("src", "https://example.com/one.jpg");
    fireEvent.click(screen.getByRole("button", { name: "Next screenshot" }));
    expect(screen.getByRole("dialog", { name: "Hades II screenshot 2 of 2" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Close screenshot" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("starts a Full import and exposes durable progress and cancellation", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request, options) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json({ ...ollamaProvider(), available: false, models: [] });
      if (url.startsWith("/api/games/preview")) return json(metadata());
      if (url === "/api/games/1145350/reports") return json([]);
      if (url === "/api/games/1145350/imports/full") {
        expect(options).toMatchObject({ method: "POST" });
        return json(job("queued", 0, "full"));
      }
      if (url === "/api/jobs/job-1/cancel") return json(job("cancelled", 200));
      if (url === "/api/jobs/job-1/delete") return new Response(null, { status: 204 });
      return json(job("running", 200));
    });

    render(<App />);
    await previewGame();
    fireEvent.click(screen.getByRole("button", { name: "Create report" }));

    expect(await screen.findByText("200 reviews scanned")).toBeVisible();
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
      if (url === "/api/games/1145350/reports") return json([]);
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
      if (url === "/api/games/1145350/reports") return json([]);
      if (url === "/api/games/1145350/imports/full") return json(job("completed", 5000, "full"));
      if (url === "/api/games/1145350/analyses/codex-cli") return json(analysisRun("queued"));
      analysisPolls += 1;
      return json(analysisRun(analysisPolls > 1 ? "completed" : "running"));
    });

    render(<App />);
    await previewGame();
    fireEvent.click(screen.getByRole("button", { name: "Create report" }));
    fireEvent.click(await screen.findByRole("button", { name: "Run Codex pilot" }));

    const link = await screen.findByRole("link", { name: "View report" });
    expect(link).toHaveAttribute("href", "/reports/report-1");
    expect(screen.getByText(/120 input and 30 output tokens/i)).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/analyses/codex-cli",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"cohort_size":25'),
      }),
    );
  });

  it("selects an installed Ollama model and starts local analysis explicitly", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request, options) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url.startsWith("/api/games/preview")) return json(metadata());
      if (url === "/api/games/1145350/reports") return json([]);
      if (url === "/api/games/1145350/imports/full") return json(job("completed", 5000, "full"));
      if (url === "/api/games/1145350/analyses/ollama") {
        expect(options).toMatchObject({
          method: "POST",
          body: expect.stringContaining('"model":"qwen3.5:4b"'),
        });
        expect(options?.body).toContain('"cohort_size":25');
        return json({ ...analysisRun("queued"), provider: "ollama", model: "qwen3.5:4b" });
      }
      return json({ ...analysisRun("completed"), provider: "ollama", model: "qwen3.5:4b" });
    });

    render(<App />);
    await previewGame();
    fireEvent.change(screen.getByLabelText("Analysis provider"), {
      target: { value: "ollama::qwen3.5:4b" },
    });
    expect(screen.getByText(/local processing: review text stays on this device/i)).toBeVisible();
    expect(screen.getByText(/analyzes 25 oldest and 25 newest reviews/i)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Create report" }));
    fireEvent.click(await screen.findByRole("button", { name: "Run Ollama pilot" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/games/1145350/analyses/ollama",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("cancels a running analysis from the progress view", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      if (url.startsWith("/api/games/preview")) return json(metadata());
      if (url === "/api/games/1145350/reports") return json([]);
      if (url === "/api/games/1145350/imports/full") return json(job("completed", 5000, "full"));
      if (url === "/api/games/1145350/analyses/ollama") {
        return json({ ...analysisRun("running"), provider: "ollama", model: "qwen3.5:4b" });
      }
      if (url === "/api/analysis-runs/analysis-1/cancel") {
        return json({ ...analysisRun("cancelled"), provider: "ollama", model: "qwen3.5:4b" });
      }
      return json({ ...analysisRun("running"), provider: "ollama", model: "qwen3.5:4b" });
    });

    render(<App />);
    await previewGame();
    fireEvent.change(screen.getByLabelText("Analysis provider"), {
      target: { value: "ollama::qwen3.5:4b" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create report" }));
    fireEvent.click(await screen.findByRole("button", { name: "Run Ollama pilot" }));
    fireEvent.click(await screen.findByRole("button", { name: "Cancel analysis" }));

    expect(await screen.findByRole("heading", { name: "Analysis cancelled" })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/analysis-runs/analysis-1/cancel",
      { method: "POST" },
    );
  });

  it("shows external-only model commands when Ollama has no installed models", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") {
        return json({ ...ollamaProvider(), available: false, models: [] });
      }
      if (url === "/api/games/1145350/reports") return json([]);
      return json(metadata());
    });

    render(<App />);
    await previewGame();

    expect(screen.getByText("ollama pull qwen3.5:4b")).toBeVisible();
    expect(screen.getByText("ollama pull qwen3.5:9b")).toBeVisible();
    expect(screen.getByText(/copy and run one command outside this application/i)).toBeVisible();
  });

  it("retries a failed Quick import", async () => {
    let progressRequests = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json({ ...ollamaProvider(), available: false, models: [] });
      if (url.startsWith("/api/games/preview")) return json(metadata());
      if (url === "/api/reports/recent") return json([]);
      if (url === "/api/games/1145350/reports") return json([]);
      if (url === "/api/games/1145350/workspace") return json(workspace(false));
      if (url === "/api/games/1145350/imports/full") return json(job("queued", 0, "full"));
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

  it("preserves the selected Ollama provider across an import-page reload", async () => {
    localStorage.setItem("active-import-job", "job-1");
    localStorage.setItem("analysis-provider", "ollama::qwen3.5:4b");
    let jobRequests: number = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (request) => {
      const url = request.toString();
      if (url === "/api/health") return json({ status: "ok", service: "game-review-analyzer" });
      if (url === "/api/config") return json(publicConfig());
      if (url === "/api/reports/recent") return json([]);
      if (url === "/api/providers/codex-cli") return json(codexProvider());
      if (url === "/api/providers/ollama") return json(ollamaProvider());
      jobRequests += 1;
      return json(job(jobRequests === 1 ? "running" : "completed", 100));
    });

    render(<App />);

    expect(await screen.findByRole("button", { name: "Run Ollama pilot" })).toBeEnabled();
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

async function selectAppId(appId: string): Promise<void> {
  fireEvent.change(screen.getByRole("textbox", { name: /steam appid/i }), {
    target: { value: appId },
  });
  fireEvent.click(screen.getByRole("button", { name: /preview game/i }));
}

function historyEntry(reportId: string, appId: number): object {
  return {
    report_version_id: reportId,
    app_id: appId,
    game_title: "Game",
    review_count: 50,
    provider: "ollama",
    model: "qwen3.5:4b",
    thresholds_calibrated: false,
    created_at: "2026-08-14 12:00:00",
  };
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

function ollamaProvider(): object {
  return {
    available: true,
    version: "0.12.6",
    processing_location: "local_device",
    models: [{
      name: "qwen3.5:4b",
      size: 3_400_000_000,
      parameter_size: "4B",
      quantization_level: "Q4_K_M",
    }],
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

function job(state: string, importedCount: number, scope: string = "full"): object {
  return {
    id: "job-1",
    app_id: 1145350,
    scope,
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
    extracted_review_count: state === "completed" ? 1 : 0,
    phase: state === "running" ? "extracting" : state,
  };
}

function workspace(fullHistoryReady: boolean, latestAnalysisRun: object | null = null): object {
  return {
    full_history_ready: fullHistoryReady,
    latest_analysis_run: latestAnalysisRun,
  };
}
