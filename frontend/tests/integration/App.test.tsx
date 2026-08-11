import { cleanup, render, screen, waitFor } from "@testing-library/react";
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
    expect(screen.getByRole("heading", { name: /evidence-backed review research/i })).toBeVisible();
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
});
