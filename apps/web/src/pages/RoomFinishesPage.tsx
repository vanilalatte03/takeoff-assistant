import { FormEvent, useMemo, useState } from "react";

import {
  createRoomFinishForDrawingFile,
  extractRoomFinishes,
  listRoomFinishes,
  rejectRoomFinish,
  updateRoomFinish,
} from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import type { ReviewStatus, RoomFinish, RoomFinishCreate } from "../types/api";

const statuses: ReviewStatus[] = ["DRAFT", "NEEDS_REVIEW", "CONFIRMED", "REJECTED"];
const statusFilters: Array<ReviewStatus | ""> = ["", ...statuses];

function parseDrawingFileId(value: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error("Drawing File ID must be a positive integer.");
  }
  return parsed;
}

function textValue(value: string | null) {
  return value ?? "";
}

function emptyDraft(): RoomFinishCreate {
  return {
    room_no: "",
    room_name: "",
    floor_finish: "",
    base_finish: "",
    wall_finish: "",
    ceiling_finish: "",
    height: "",
    source_sheet_no: "",
    remarks: "",
  };
}

function normalizeDraft(draft: RoomFinishCreate): RoomFinishCreate {
  return Object.fromEntries(
    Object.entries(draft).map(([key, value]) => [key, typeof value === "string" && !value.trim() ? null : value]),
  ) as RoomFinishCreate;
}

export function RoomFinishesPage() {
  const [drawingFileId, setDrawingFileId] = useState("");
  const [rows, setRows] = useState<RoomFinish[]>([]);
  const [persistedStatuses, setPersistedStatuses] = useState<Record<number, ReviewStatus>>({});
  const [warnings, setWarnings] = useState<string[]>([]);
  const [draft, setDraft] = useState<RoomFinishCreate>(emptyDraft);
  const [pendingRowId, setPendingRowId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [roomFilter, setRoomFilter] = useState("");
  const [finishFilter, setFinishFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | "">("");

  const filteredRows = useMemo(
    () =>
      rows.filter((row) => {
        const roomText = `${row.room_no ?? ""} ${row.room_name ?? ""}`.toUpperCase();
        const finishText = [
          row.floor_finish,
          row.base_finish,
          row.wall_finish,
          row.ceiling_finish,
          row.remarks,
          row.source_sheet_no,
        ]
          .filter(Boolean)
          .join(" ")
          .toUpperCase();
        return (
          (!roomFilter.trim() || roomText.includes(roomFilter.trim().toUpperCase())) &&
          (!finishFilter.trim() || finishText.includes(finishFilter.trim().toUpperCase())) &&
          (!statusFilter || row.status === statusFilter)
        );
      }),
    [finishFilter, roomFilter, rows, statusFilter],
  );

  async function loadRows(id: number) {
    const loaded = await listRoomFinishes(id);
    setRows(loaded);
    setPersistedStatuses(Object.fromEntries(loaded.map((row) => [row.id, row.status])));
    return loaded;
  }

  async function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const loaded = await loadRows(parseDrawingFileId(drawingFileId));
      setMessage(`Loaded ${loaded.length} room finishes.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleExtract() {
    setIsLoading(true);
    setError(null);
    setMessage(null);
    setWarnings([]);
    try {
      const id = parseDrawingFileId(drawingFileId);
      const result = await extractRoomFinishes(id);
      const loaded = await loadRows(id);
      setWarnings(result.warnings ?? []);
      setMessage(`Extracted ${result.room_finishes.length} room finishes. Total loaded: ${loaded.length}.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsLoading(false);
    }
  }

  function updateLocalRow(rowId: number, patch: Partial<RoomFinish>) {
    setRows((current) => current.map((row) => (row.id === rowId ? { ...row, ...patch } : row)));
  }

  function isReadOnly(row: RoomFinish) {
    return persistedStatuses[row.id] === "CONFIRMED" || persistedStatuses[row.id] === "REJECTED";
  }

  function applySavedRow(saved: RoomFinish) {
    updateLocalRow(saved.id, saved);
    setPersistedStatuses((current) => ({ ...current, [saved.id]: saved.status }));
  }

  async function startReview(row: RoomFinish) {
    setPendingRowId(row.id);
    setError(null);
    setMessage(null);
    try {
      applySavedRow(await updateRoomFinish(row.id, { status: "DRAFT" }));
      setMessage(`Room ${row.room_no ?? row.id} 재검토 시작`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingRowId(null);
    }
  }

  function updateDraft(patch: Partial<RoomFinishCreate>) {
    setDraft((current) => ({ ...current, ...patch }));
    setMessage(null);
    setError(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsCreating(true);
    setError(null);
    setMessage(null);
    try {
      const id = parseDrawingFileId(drawingFileId);
      const saved = await createRoomFinishForDrawingFile(id, normalizeDraft(draft));
      setRows((current) => [...current, saved]);
      setPersistedStatuses((current) => ({ ...current, [saved.id]: saved.status }));
      setDraft(emptyDraft());
      setMessage(`Room ${saved.room_no ?? saved.id} created.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSave(row: RoomFinish) {
    if (isReadOnly(row)) return;
    setPendingRowId(row.id);
    setError(null);
    setMessage(null);
    try {
      const saved = await updateRoomFinish(row.id, {
        room_no: row.room_no,
        room_name: row.room_name,
        floor_finish: row.floor_finish,
        base_finish: row.base_finish,
        wall_finish: row.wall_finish,
        ceiling_finish: row.ceiling_finish,
        height: row.height,
        remarks: row.remarks,
        status: row.status,
      });
      applySavedRow(saved);
      setMessage(`Room ${saved.room_no ?? saved.id} saved.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingRowId(null);
    }
  }

  async function handleReject(row: RoomFinish) {
    setPendingRowId(row.id);
    setError(null);
    setMessage(null);
    try {
      const rejected = await rejectRoomFinish(row.id);
      applySavedRow(rejected);
      setMessage(`Room ${rejected.room_no ?? rejected.id} rejected.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingRowId(null);
    }
  }

  return (
    <>
      <PageHeader title="Room Finish Review" description="Extract, filter, edit, confirm, or reject room finish rows." />

      <section className="panel">
        <form className="toolbar-form compact" onSubmit={handleLoad}>
          <label>
            <span>Drawing File ID</span>
            <input value={drawingFileId} inputMode="numeric" onChange={(event) => setDrawingFileId(event.target.value)} />
          </label>
          <button type="submit" disabled={isLoading}>
            Load
          </button>
          <button type="button" className="button-secondary" disabled={isLoading} onClick={handleExtract}>
            Extract
          </button>
        </form>
        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
        {warnings.length ? (
          <div className="message message-warning">
            <strong>Extraction warnings</strong>
            <ul className="message-list">
              {warnings.map((warning, index) => (
                <li key={`${warning}-${index}`}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Add Room Finish</h2>
          <span className="count-label">Manual row</span>
        </div>
        <form className="room-finish-create-grid" onSubmit={handleCreate}>
          <label>
            <span>Room No</span>
            <input value={draft.room_no ?? ""} onChange={(event) => updateDraft({ room_no: event.target.value })} />
          </label>
          <label>
            <span>Room Name</span>
            <input value={draft.room_name ?? ""} onChange={(event) => updateDraft({ room_name: event.target.value })} />
          </label>
          <label>
            <span>Floor</span>
            <input value={draft.floor_finish ?? ""} onChange={(event) => updateDraft({ floor_finish: event.target.value })} />
          </label>
          <label>
            <span>Base</span>
            <input value={draft.base_finish ?? ""} onChange={(event) => updateDraft({ base_finish: event.target.value })} />
          </label>
          <label>
            <span>Wall</span>
            <input value={draft.wall_finish ?? ""} onChange={(event) => updateDraft({ wall_finish: event.target.value })} />
          </label>
          <label>
            <span>Ceiling</span>
            <input value={draft.ceiling_finish ?? ""} onChange={(event) => updateDraft({ ceiling_finish: event.target.value })} />
          </label>
          <label>
            <span>Height</span>
            <input value={draft.height ?? ""} onChange={(event) => updateDraft({ height: event.target.value })} />
          </label>
          <label>
            <span>Source Sheet</span>
            <input value={draft.source_sheet_no ?? ""} placeholder="AE601" onChange={(event) => updateDraft({ source_sheet_no: event.target.value })} />
          </label>
          <label className="wide-field">
            <span>Remarks</span>
            <input value={draft.remarks ?? ""} onChange={(event) => updateDraft({ remarks: event.target.value })} />
          </label>
          <button type="submit" disabled={isCreating || isLoading}>
            {isCreating ? "Creating..." : "Create"}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Room Finish</h2>
          <span className="count-label">
            {filteredRows.length} / {rows.length} rows
          </span>
        </div>
        <div className="measurement-filter-grid">
          <label>
            <span>Room</span>
            <input value={roomFilter} placeholder="119 or lobby" onChange={(event) => setRoomFilter(event.target.value)} />
          </label>
          <label>
            <span>Finish</span>
            <input value={finishFilter} placeholder="tile, paint, GWB" onChange={(event) => setFinishFilter(event.target.value)} />
          </label>
          <label>
            <span>Status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as ReviewStatus | "")}>
              {statusFilters.map((status) => (
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
                  <th>Room No</th>
                  <th>Room Name</th>
                  <th>Floor</th>
                  <th>Base</th>
                  <th>Wall</th>
                  <th>Ceiling</th>
                  <th>Height</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <input disabled={isReadOnly(row)} value={textValue(row.room_no)} onChange={(event) => updateLocalRow(row.id, { room_no: event.target.value })} />
                    </td>
                    <td>
                      <input disabled={isReadOnly(row)} value={textValue(row.room_name)} onChange={(event) => updateLocalRow(row.id, { room_name: event.target.value })} />
                    </td>
                    <td>
                      <input disabled={isReadOnly(row)} value={textValue(row.floor_finish)} onChange={(event) => updateLocalRow(row.id, { floor_finish: event.target.value })} />
                    </td>
                    <td>
                      <input disabled={isReadOnly(row)} value={textValue(row.base_finish)} onChange={(event) => updateLocalRow(row.id, { base_finish: event.target.value })} />
                    </td>
                    <td>
                      <input disabled={isReadOnly(row)} value={textValue(row.wall_finish)} onChange={(event) => updateLocalRow(row.id, { wall_finish: event.target.value })} />
                    </td>
                    <td>
                      <input
                        disabled={isReadOnly(row)}
                        value={textValue(row.ceiling_finish)}
                        onChange={(event) => updateLocalRow(row.id, { ceiling_finish: event.target.value })}
                      />
                    </td>
                    <td>
                      <input disabled={isReadOnly(row)} value={textValue(row.height)} onChange={(event) => updateLocalRow(row.id, { height: event.target.value })} />
                    </td>
                    <td>
                      <select disabled={isReadOnly(row)} value={row.status} onChange={(event) => updateLocalRow(row.id, { status: event.target.value as ReviewStatus })}>
                        {statuses.map((status) => (
                          <option key={status} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                      <StatusBadge status={row.status} />
                    </td>
                    <td>{row.source_sheet_no ?? "-"}</td>
                    <td>
                      <div className="table-actions">
                        {persistedStatuses[row.id] === "CONFIRMED" ? <button type="button" disabled={pendingRowId === row.id} onClick={() => startReview(row)}>재검토 시작</button> : null}
                        <button type="button" className="button-secondary compact-button" disabled={pendingRowId === row.id || isReadOnly(row)} onClick={() => handleSave(row)}>
                          Save
                        </button>
                        <button
                          type="button"
                          className="button-secondary compact-button danger-button"
                          disabled={pendingRowId === row.id || isReadOnly(row)}
                          onClick={() => handleReject(row)}
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>{rows.length ? "No room finishes match the filters." : "No room finishes loaded."}</EmptyState>
        )}
      </section>
    </>
  );
}
