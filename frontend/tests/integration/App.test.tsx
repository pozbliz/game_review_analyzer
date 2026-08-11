import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../../src/app/App";

afterEach(() => vi.restoreAllMocks());

describe("application shell", () => {
  it("reports backend health when the API is available", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );

    render(<App />);

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("connected"));
    expect(screen.getByRole("heading", { name: /evidence-backed review research/i })).toBeVisible();
  });
});
