import { FormEvent, useMemo, useState } from "react";

import {
  downloadMeasurementsExcel,
  generateMeasurements,
  getDrawingFileRoomStatus,
  listMeasurements,
  mergeMeasurements,
  rejectMeasurement,
} from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { MeasurementCalculationForm } from "../components/MeasurementCalculationForm";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import type { DrawingFileRoomStatus, Measurement, MeasurementType, ReviewStatus } from "../types/api";

const measurementTypeOptions: Array<MeasurementType | ""> = [
  "",
  "FLOOR_AREA",
  "CEILING_AREA",
  "PERIMETER_LENGTH",
  "WALL_AREA",
  "PARTITION_AREA",
  "COUNT",
];
const statusOptions: Array<ReviewStatus | ""> = ["", "DRAFT", "NEEDS_REVIEW", "CONFIRMED", "REJECTED"];

function parseDrawingFileId(value: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error("Drawing File ID must be a positive integer.");
  }
  return parsed;
}

function triggerDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export function MeasurementsPage() {
  const [drawingFileId, setDrawingFileId] = useState("");
  const [rows, setRows] = useState<Measurement[]>([]);
  const [roomStatus, setRoomStatus] = useState<DrawingFileRoomStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [pendingRowId, setPendingRowId] = useState<number | null>(null);
  const [isMerging, setIsMerging] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [selectedMeasurementId, setSelectedMeasurementId] = useState<number | null>(null);
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [mergeSourceIds, setMergeSourceIds] = useState<number[]>([]);
  const [roomNoFilter, setRoomNoFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [codeFilter, setCodeFilter] = useState("");
  const [measurementTypeFilter, setMeasurementTypeFilter] = useState<MeasurementType | "">("");
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | "">("");

  const selectedMeasurement = useMemo(
    () => rows.find((row) => row.id === selectedMeasurementId) ?? null,
    [rows, selectedMeasurementId],
  );
  const mergeableRows = useMemo(
    () => rows.filter((row) => row.status !== "CONFIRMED" && row.status !== "REJECTED"),
    [rows],
  );
  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        const roomNoMatches = !roomNoFilter.trim() || (row.room_no ?? "").toUpperCase().includes(roomNoFilter.trim().toUpperCase());
        const categoryMatches = !categoryFilter.trim() || row.category.toUpperCase().includes(categoryFilter.trim().toUpperCase());
        const codeMatches = !codeFilter.trim() || row.finish_code.toUpperCase().includes(codeFilter.trim().toUpperCase());
        const typeMatches = !measurementTypeFilter || row.measurement_type === measurementTypeFilter;
        const statusMatches = !statusFilter || row.status === statusFilter;
        return roomNoMatches && categoryMatches && codeMatches && typeMatches && statusMatches;
      }),
    [categoryFilter, codeFilter, measurementTypeFilter, roomNoFilter, rows, statusFilter],
  );

  async function loadRoomStatus(id: number) {
    const loadedStatus = await getDrawingFileRoomStatus(id);
    setRoomStatus(loadedStatus);
    return loadedStatus;
  }

  async function loadRows(id: number) {
    const [loaded] = await Promise.all([listMeasurements(id), loadRoomStatus(id)]);
    setRows(loaded);
    setSelectedMeasurementId((current) => {
      if (current && loaded.some((row) => row.id === current)) {
        return current;
      }
      return loaded[0]?.id ?? null;
    });
    setMergeTargetId((current) => {
      if (current && loaded.some((row) => String(row.id) === current && row.status !== "CONFIRMED" && row.status !== "REJECTED")) {
        return current;
      }
      const firstMergeable = loaded.find((row) => row.status !== "CONFIRMED" && row.status !== "REJECTED");
      return firstMergeable ? String(firstMergeable.id) : "";
    });
    setMergeSourceIds((current) => current.filter((idValue) => loaded.some((row) => row.id === idValue)));
    return loaded;
  }

  async function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const loaded = await loadRows(parseDrawingFileId(drawingFileId));
      setMessage(`Loaded ${loaded.length} measurements.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGenerate() {
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const id = parseDrawingFileId(drawingFileId);
      const result = await generateMeasurements(id);
      const loaded = await loadRows(id);
      setMessage(`Generated ${result.measurements.length} candidates. Total loaded: ${loaded.length}.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDownload() {
    setIsDownloading(true);
    setError(null);
    setMessage(null);
    try {
      const id = parseDrawingFileId(drawingFileId);
      const exportFile = await downloadMeasurementsExcel(id);
      triggerDownload(exportFile.blob, exportFile.filename);
      setMessage(`Downloaded ${exportFile.filename}.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsDownloading(false);
    }
  }

  function handleMeasurementSaved(saved: Measurement) {
    setRows((current) => current.map((row) => (row.id === saved.id ? saved : row)));
    setSelectedMeasurementId(saved.id);
    setMergeTargetId((current) => {
      if (String(saved.id) === current && (saved.status === "CONFIRMED" || saved.status === "REJECTED")) {
        const nextTarget = rows.find((row) => row.id !== saved.id && row.status !== "CONFIRMED" && row.status !== "REJECTED");
        return nextTarget ? String(nextTarget.id) : "";
      }
      return current;
    });
    setMergeSourceIds((current) => current.filter((idValue) => idValue !== saved.id || (saved.status !== "CONFIRMED" && saved.status !== "REJECTED")));
    if (drawingFileId.trim()) {
      try {
        void loadRoomStatus(parseDrawingFileId(drawingFileId)).catch(setError);
      } catch {
        // The load form owns validation feedback for invalid drawing file IDs.
      }
    }
  }

  async function handleReject(row: Measurement) {
    setPendingRowId(row.id);
    setError(null);
    setMessage(null);
    try {
      const rejected = await rejectMeasurement(row.id);
      handleMeasurementSaved(rejected);
      setMessage(`Measurement ${rejected.id} rejected.`);
      if (drawingFileId) {
        await loadRoomStatus(parseDrawingFileId(drawingFileId));
      }
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingRowId(null);
    }
  }

  async function handleMerge() {
    setIsMerging(true);
    setError(null);
    setMessage(null);
    try {
      const targetId = parseDrawingFileId(mergeTargetId);
      const sourceIds = mergeSourceIds.filter((idValue) => idValue !== targetId);
      if (!sourceIds.length) {
        throw new Error("Choose at least one source measurement to merge.");
      }
      const merged = await mergeMeasurements({ target_id: targetId, source_ids: sourceIds });
      const id = parseDrawingFileId(drawingFileId);
      const loaded = await loadRows(id);
      setSelectedMeasurementId(merged.id);
      setMergeSourceIds([]);
      setMessage(`Merged ${sourceIds.length} measurements into #${merged.id}. Total loaded: ${loaded.length}.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsMerging(false);
    }
  }

  function toggleMergeSource(rowId: number, checked: boolean) {
    setMergeSourceIds((current) => (checked ? [...new Set([...current, rowId])] : current.filter((idValue) => idValue !== rowId)));
  }

  return (
    <>
      <PageHeader
        title="Measurement Review"
        description="Generate, calculate, merge, reject, and export takeoff measurements."
        actions={
          <button type="button" className="button-secondary" disabled={isDownloading} onClick={handleDownload}>
            {isDownloading ? "Exporting..." : "Export Excel"}
          </button>
        }
      />

      <section className="panel">
        <form className="toolbar-form compact" onSubmit={handleLoad}>
          <label>
            <span>Drawing File ID</span>
            <input value={drawingFileId} inputMode="numeric" onChange={(event) => setDrawingFileId(event.target.value)} />
          </label>
          <button type="submit" disabled={isLoading}>
            Load
          </button>
          <button type="button" className="button-secondary" disabled={isLoading} onClick={handleGenerate}>
            Generate
          </button>
        </form>
        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Room Status</h2>
          <span className="count-label">{roomStatus?.rooms.length ?? 0} rooms</span>
        </div>
        {roomStatus?.rooms.length ? (
          <div className="room-status-grid">
            {roomStatus.rooms.map((room) => (
              <button
                key={`${room.room_no ?? "room"}-${room.room_name ?? ""}`}
                type="button"
                className="room-status-card"
                onClick={() => setRoomNoFilter(room.room_no ?? "")}
              >
                <strong>{room.room_no ?? "-"}</strong>
                <span>{room.room_name ?? "Unnamed room"}</span>
                <dl>
                  <div>
                    <dt>Total</dt>
                    <dd>{room.total_count}</dd>
                  </div>
                  <div>
                    <dt>Qty</dt>
                    <dd>{room.quantity_count}</dd>
                  </div>
                  <div>
                    <dt>Confirmed</dt>
                    <dd>{room.confirmed_count}</dd>
                  </div>
                  <div>
                    <dt>Review</dt>
                    <dd>{room.needs_review_count}</dd>
                  </div>
                  <div>
                    <dt>Missing</dt>
                    <dd>{room.missing_quantity_count}</dd>
                  </div>
                </dl>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState>Load a drawing file to see room measurement status.</EmptyState>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Merge Measurements</h2>
          <span className="count-label">{mergeSourceIds.length} sources selected</span>
        </div>
        <div className="merge-grid">
          <label>
            <span>Target</span>
            <select value={mergeTargetId} onChange={(event) => setMergeTargetId(event.target.value)} disabled={!mergeableRows.length}>
              {mergeableRows.map((row) => (
                <option key={row.id} value={row.id}>
                  #{row.id} {row.room_no ?? "-"} {row.category} {row.finish_code}
                </option>
              ))}
            </select>
          </label>
          <button type="button" disabled={isMerging || !mergeTargetId || !mergeSourceIds.length} onClick={handleMerge}>
            {isMerging ? "Merging..." : "Merge selected"}
          </button>
        </div>
      </section>

      <MeasurementCalculationForm measurement={selectedMeasurement} onSaved={handleMeasurementSaved} />

      <section className="panel">
        <div className="section-heading">
          <h2>Measurements</h2>
          <span className="count-label">
            {filteredRows.length} / {rows.length} rows
          </span>
        </div>
        <div className="measurement-filter-grid">
          <label>
            <span>Room No</span>
            <input value={roomNoFilter} placeholder="119" onChange={(event) => setRoomNoFilter(event.target.value)} />
          </label>
          <label>
            <span>Category</span>
            <input value={categoryFilter} placeholder="PARTITION" onChange={(event) => setCategoryFilter(event.target.value)} />
          </label>
          <label>
            <span>Code</span>
            <input value={codeFilter} placeholder="GWB or 5A" onChange={(event) => setCodeFilter(event.target.value)} />
          </label>
          <label>
            <span>Type</span>
            <select value={measurementTypeFilter} onChange={(event) => setMeasurementTypeFilter(event.target.value as MeasurementType | "")}>
              {measurementTypeOptions.map((type) => (
                <option key={type || "ALL"} value={type}>
                  {type || "All"}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as ReviewStatus | "")}>
              {statusOptions.map((status) => (
                <option key={status || "ALL"} value={status}>
                  {status || "All"}
                </option>
              ))}
            </select>
          </label>
        </div>
        {filteredRows.length ? (
          <div className="table-wrap wide">
            <table>
              <thead>
                <tr>
                  <th>Select</th>
                  <th>Merge</th>
                  <th>Room</th>
                  <th>Category</th>
                  <th>Finish Code</th>
                  <th>Type</th>
                  <th>Formula</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>Source Sheets</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => (
                  <tr
                    key={row.id}
                    className={selectedMeasurementId === row.id ? "selected-row" : undefined}
                    onClick={() => setSelectedMeasurementId(row.id)}
                  >
                    <td>
                      <button
                        type="button"
                        className="button-secondary compact-button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedMeasurementId(row.id);
                        }}
                      >
                        Select
                      </button>
                    </td>
                    <td onClick={(event) => event.stopPropagation()}>
                      <label className="checkbox-label table-checkbox">
                        <input
                          type="checkbox"
                          checked={mergeSourceIds.includes(row.id)}
                          disabled={String(row.id) === mergeTargetId || row.status === "CONFIRMED" || row.status === "REJECTED"}
                          onChange={(event) => toggleMergeSource(row.id, event.target.checked)}
                        />
                        <span>Source</span>
                      </label>
                    </td>
                    <td>
                      <strong>{row.room_no ?? "-"}</strong>
                      <span className="muted-cell">{row.room_name ?? ""}</span>
                    </td>
                    <td>{row.category}</td>
                    <td>{row.finish_code}</td>
                    <td>{row.measurement_type}</td>
                    <td>{row.formula ?? "-"}</td>
                    <td>{row.quantity ?? "-"}</td>
                    <td>{row.unit ?? "-"}</td>
                    <td>{row.source_sheets || "-"}</td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>
                    <td onClick={(event) => event.stopPropagation()}>
                      <button
                        type="button"
                        className="button-secondary compact-button danger-button"
                        disabled={pendingRowId === row.id || row.status === "CONFIRMED" || row.status === "REJECTED"}
                        onClick={() => handleReject(row)}
                      >
                        Reject
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>{rows.length ? "No measurements match the filters." : "No measurements loaded."}</EmptyState>
        )}
      </section>
    </>
  );
}
