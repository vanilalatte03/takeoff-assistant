import { FormEvent, useState } from "react";

import { createRoomFinishForDrawingFile, extractRoomFinishes, listRoomFinishes, updateRoomFinish } from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import type { ReviewStatus, RoomFinish, RoomFinishCreate } from "../types/api";

const statuses: ReviewStatus[] = ["DRAFT", "NEEDS_REVIEW", "CONFIRMED", "REJECTED"];

function parseDrawingFileId(value: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error("Drawing File ID는 1 이상의 정수여야 합니다.");
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
  const [draft, setDraft] = useState<RoomFinishCreate>(emptyDraft);
  const [pendingRowId, setPendingRowId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  async function loadRows(id: number) {
    const loaded = await listRoomFinishes(id);
    setRows(loaded);
    return loaded;
  }

  async function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const loaded = await loadRows(parseDrawingFileId(drawingFileId));
      setMessage(`Room Finish ${loaded.length}건`);
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
    try {
      const id = parseDrawingFileId(drawingFileId);
      const result = await extractRoomFinishes(id);
      const loaded = await loadRows(id);
      setMessage(`후보 ${result.room_finishes.length}건 추출, 전체 ${loaded.length}건`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsLoading(false);
    }
  }

  function updateLocalRow(rowId: number, patch: Partial<RoomFinish>) {
    setRows((current) => current.map((row) => (row.id === rowId ? { ...row, ...patch } : row)));
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
      setDraft(emptyDraft());
      setMessage(`Room ${saved.room_no ?? saved.id} 수동 추가 완료`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSave(row: RoomFinish) {
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
      updateLocalRow(row.id, saved);
      setMessage(`Room ${saved.room_no ?? saved.id} 저장 완료`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingRowId(null);
    }
  }

  return (
    <>
      <PageHeader title="Room Finish 테이블" description="자동 추출 후보를 검수하고 수정하는 작업 테이블입니다." />

      <section className="panel">
        <form className="toolbar-form compact" onSubmit={handleLoad}>
          <label>
            <span>Drawing File ID</span>
            <input value={drawingFileId} inputMode="numeric" onChange={(event) => setDrawingFileId(event.target.value)} />
          </label>
          <button type="submit" disabled={isLoading}>
            목록 조회
          </button>
          <button type="button" className="button-secondary" disabled={isLoading} onClick={handleExtract}>
            후보 추출
          </button>
        </form>
        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>새 Room Finish 추가</h2>
          <span className="count-label">자동 추출 실패 시 수동 입력</span>
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
            {isCreating ? "추가 중" : "수동 추가"}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Room Finish</h2>
          <span className="count-label">{rows.length}건</span>
        </div>
        {rows.length ? (
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
                  <th>저장</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <input value={textValue(row.room_no)} onChange={(event) => updateLocalRow(row.id, { room_no: event.target.value })} />
                    </td>
                    <td>
                      <input value={textValue(row.room_name)} onChange={(event) => updateLocalRow(row.id, { room_name: event.target.value })} />
                    </td>
                    <td>
                      <input value={textValue(row.floor_finish)} onChange={(event) => updateLocalRow(row.id, { floor_finish: event.target.value })} />
                    </td>
                    <td>
                      <input value={textValue(row.base_finish)} onChange={(event) => updateLocalRow(row.id, { base_finish: event.target.value })} />
                    </td>
                    <td>
                      <input value={textValue(row.wall_finish)} onChange={(event) => updateLocalRow(row.id, { wall_finish: event.target.value })} />
                    </td>
                    <td>
                      <input
                        value={textValue(row.ceiling_finish)}
                        onChange={(event) => updateLocalRow(row.id, { ceiling_finish: event.target.value })}
                      />
                    </td>
                    <td>
                      <input value={textValue(row.height)} onChange={(event) => updateLocalRow(row.id, { height: event.target.value })} />
                    </td>
                    <td>
                      <select value={row.status} onChange={(event) => updateLocalRow(row.id, { status: event.target.value as ReviewStatus })}>
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
                      <button type="button" className="button-secondary" disabled={pendingRowId === row.id} onClick={() => handleSave(row)}>
                        {pendingRowId === row.id ? "저장 중" : "저장"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>조회된 Room Finish가 없습니다.</EmptyState>
        )}
      </section>
    </>
  );
}
