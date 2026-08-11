import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../../src/app/App";

afterEach(() => {
  cleanup();
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
        JSON.stringify({ environment: "test", api_prefix: "/api" }),
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
          JSON.stringify({ environment: "test", api_prefix: "/api" }),
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
});
