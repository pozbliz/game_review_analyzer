import { useState } from "react";
import {
  deleteGameDataset,
  deleteIncompleteJob,
  deleteReport,
  getStorageDiagnostics,
  StorageDiagnostics,
} from "../../api/storage";

interface StorageControlsProps {
  appId: number;
  reportId: string;
  incompleteJobId?: string;
}

export default function StorageControls({
  appId,
  reportId,
  incompleteJobId,
}: StorageControlsProps): JSX.Element {
  const [diagnostics, setDiagnostics] = useState<StorageDiagnostics | null>(null);
  const [reportConfirmation, setReportConfirmation] = useState<string>("");
  const [gameConfirmation, setGameConfirmation] = useState<string>("");
  const [jobConfirmation, setJobConfirmation] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");

  function loadStorage(): void {
    setError("");
    getStorageDiagnostics()
      .then(setDiagnostics)
      .catch(() => setError("Unable to load storage details."));
  }

  function removeReport(): void {
    setError("");
    deleteReport(reportId, reportConfirmation)
      .then(() => setMessage("Report deleted. Return to the catalog to continue."))
      .catch(() => setError("Report deletion was rejected."));
  }

  function removeGame(): void {
    setError("");
    deleteGameDataset(appId, gameConfirmation)
      .then(() => setMessage("Game Dataset deleted. Reports and local evidence cannot be recovered."))
      .catch(() => setError("Game Dataset deletion was rejected."));
  }

  function removeJob(): void {
    if (!incompleteJobId) return;
    setError("");
    deleteIncompleteJob(incompleteJobId, jobConfirmation)
      .then(() => setMessage("Incomplete job deleted. Existing reports are unchanged."))
      .catch(() => setError("Job deletion was rejected."));
  }

  return (
    <section className="storage-controls" aria-labelledby="storage-title">
      <h2 id="storage-title">Local data</h2>
      <p>Inspect retained data before deleting anything. Deletions cannot be undone.</p>
      <button type="button" onClick={loadStorage}>Load storage details</button>
      {diagnostics && (
        <dl className="storage-facts">
          <div><dt>Storage used</dt><dd>{formatBytes(diagnostics.database_bytes)}</dd></div>
          <div><dt>Database</dt><dd><code>{diagnostics.database_path}</code></dd></div>
          <div><dt>Retained</dt><dd>{diagnostics.game_dataset_count} games · {diagnostics.report_version_count} reports · {diagnostics.review_revision_count.toLocaleString()} revisions</dd></div>
        </dl>
      )}
      <p className="storage-guidance">Data-directory relocation is not available yet. Export important reports before deletion; default exports are not complete evidence backups.</p>

      <details className="danger-zone">
        <summary>Destructive controls</summary>
        <div>
          <label>
            Type {reportId} to delete this report
            <input value={reportConfirmation} onChange={(event) => setReportConfirmation(event.target.value)} />
          </label>
          <button type="button" disabled={reportConfirmation !== reportId} onClick={removeReport}>Delete this report</button>
        </div>
        {incompleteJobId && (
          <div>
            <label>
              Type {incompleteJobId} to delete the incomplete job
              <input value={jobConfirmation} onChange={(event) => setJobConfirmation(event.target.value)} />
            </label>
            <button type="button" disabled={jobConfirmation !== incompleteJobId} onClick={removeJob}>Delete incomplete job</button>
          </div>
        )}
        <div>
          <p>Deleting the Game Dataset also deletes every owned report, job, and local Review Revision.</p>
          <label>
            Type DELETE {appId} to delete the complete Game Dataset
            <input value={gameConfirmation} onChange={(event) => setGameConfirmation(event.target.value)} />
          </label>
          <button type="button" disabled={gameConfirmation !== `DELETE ${appId}`} onClick={removeGame}>Delete Game Dataset</button>
        </div>
      </details>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
