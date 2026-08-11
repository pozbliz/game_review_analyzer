import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import StorageControls from "../../src/features/storage/StorageControls";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("shows local storage and requires exact destructive confirmations", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
    async (request) => request.toString().endsWith("/api/storage")
      ? json({
        database_path: "C:\\AppData\\game-review-analyzer\\app.sqlite3",
        database_bytes: 2048,
        game_dataset_count: 1,
        report_version_count: 2,
        review_revision_count: 5000,
        incomplete_job_count: 0,
      })
      : new Response(null, { status: 204 }),
  );
  render(<StorageControls appId={1145350} reportId="report-1" />);

  fireEvent.click(screen.getByRole("button", { name: "Load storage details" }));
  expect(await screen.findByText("2 KB")).toBeVisible();
  expect(screen.getByText(/data-directory relocation is not available/i)).toBeVisible();

  const reportConfirmation = screen.getByLabelText("Type report-1 to delete this report");
  const deleteReport = screen.getByRole("button", { name: "Delete this report" });
  fireEvent.change(reportConfirmation, { target: { value: "wrong" } });
  expect(deleteReport).toBeDisabled();
  fireEvent.change(reportConfirmation, { target: { value: "report-1" } });
  fireEvent.click(deleteReport);

  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/reports/report-1/delete",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: "report-1" }),
    },
  ));
  expect(await screen.findByText(/report deleted/i)).toBeVisible();
});

function json(payload: object): Response {
  return new Response(JSON.stringify(payload), { status: 200 });
}
