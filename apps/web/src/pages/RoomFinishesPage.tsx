import { DrawingFilePicker, useDrawingFileSelection } from "../components/DrawingFilePicker";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createRoomFinishForDrawingFile,
  extractRoomFinishes,
  listRoomFinishes,
  rejectRoomFinish,
  updateRoomFinish,
} from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import { statusLabels, StatusBadge } from "../components/StatusBadge";
import type { ReviewStatus, RoomFinish, RoomFinishCreate } from "../types/api";

const statuses: ReviewStatus[] = ["DRAFT", "NEEDS_REVIEW", "CONFIRMED", "REJECTED"];
const statusFilters: Array<ReviewStatus | ""> = ["", ...statuses];

function parseDrawingFileId(value: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error("도면 PDF를 선택하세요.");
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
  const [drawingFileId, setDrawingFileId] = useDrawingFileSelection();
  return <><section className="panel drawing-context"><DrawingFilePicker value={drawingFileId} onChange={setDrawingFileId} /></section>
    <RoomFinishesPageContent key={drawingFileId} drawingFileId={drawingFileId} /></>;
}

function RoomFinishesPageContent({ drawingFileId }: { drawingFileId: string }) {
  const [rows, setRows] = useState<RoomFinish[]>([]);
  const [persistedStatuses, setPersistedStatuses] = useState<Record<number, ReviewStatus>>({});
  const [warnings, setWarnings] = useState<string[]>([]);
  const [draft, setDraft] = useState<RoomFinishCreate>(emptyDraft);
  const [pendingRowId, setPendingRowId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(!!drawingFileId);
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

  async function loadRows(id: number, active = () => true) {
    const loaded = await listRoomFinishes(id);
    if (!active()) return loaded;
    setRows(loaded);
    setPersistedStatuses(Object.fromEntries(loaded.map((row) => [row.id, row.status])));
    return loaded;
  }

  useEffect(() => {
    if (!drawingFileId) return;
    let active = true;
    setIsLoading(true);
    void Promise.resolve().then(() => loadRows(parseDrawingFileId(drawingFileId), () => active))
      .catch((caught) => { if (active) setError(caught); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [drawingFileId]);

  async function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const loaded = await loadRows(parseDrawingFileId(drawingFileId));
      setMessage(`마감 ${loaded.length}건을 불러왔습니다.`);
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
      setMessage(`마감 후보 ${result.room_finishes.length}건 추출 · 전체 ${loaded.length}건`);
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
      setMessage(`실 ${saved.room_no ?? saved.id}의 마감을 추가했습니다.`);
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
      setMessage(`실 ${saved.room_no ?? saved.id}의 마감을 저장했습니다.`);
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
      setMessage(`실 ${rejected.room_no ?? rejected.id}의 마감을 거절했습니다.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingRowId(null);
    }
  }

  return (
    <>
      <PageHeader title="실별 마감표 검수" description="마감표를 원본과 비교해 수정하고, 검수가 끝난 행을 확정하세요." />

      <section className="panel">
        <form className="toolbar-form compact" onSubmit={handleLoad}>

          <button type="submit" disabled={isLoading || !drawingFileId}>
            {isLoading ? "불러오는 중…" : "다시 불러오기"}
          </button>
          <button type="button" className="button-secondary" disabled={isLoading || !drawingFileId} onClick={handleExtract}>
            마감표 후보 추출
          </button>
        </form>
        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
        {warnings.length ? (
          <div className="message message-warning">
            <strong>마감표 추출 주의사항</strong>
            <ul className="message-list">
              {warnings.map((warning, index) => (
                <li key={`${warning}-${index}`}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <details className="panel secondary-disclosure">
        <summary>실별 마감 추가</summary>
        <form className="room-finish-create-grid" onSubmit={handleCreate}>
          <label>
            <span>실 번호</span>
            <input value={draft.room_no ?? ""} onChange={(event) => updateDraft({ room_no: event.target.value })} />
          </label>
          <label>
            <span>실 이름</span>
            <input value={draft.room_name ?? ""} onChange={(event) => updateDraft({ room_name: event.target.value })} />
          </label>
          <label>
            <span>바닥</span>
            <input value={draft.floor_finish ?? ""} onChange={(event) => updateDraft({ floor_finish: event.target.value })} />
          </label>
          <label>
            <span>걸레받이</span>
            <input value={draft.base_finish ?? ""} onChange={(event) => updateDraft({ base_finish: event.target.value })} />
          </label>
          <label>
            <span>벽</span>
            <input value={draft.wall_finish ?? ""} onChange={(event) => updateDraft({ wall_finish: event.target.value })} />
          </label>
          <label>
            <span>천장</span>
            <input value={draft.ceiling_finish ?? ""} onChange={(event) => updateDraft({ ceiling_finish: event.target.value })} />
          </label>
          <label>
            <span>높이</span>
            <input value={draft.height ?? ""} onChange={(event) => updateDraft({ height: event.target.value })} />
          </label>
          <label>
            <span>출처 도면</span>
            <input value={draft.source_sheet_no ?? ""} placeholder="AE601" onChange={(event) => updateDraft({ source_sheet_no: event.target.value })} />
          </label>
          <label className="wide-field">
            <span>비고</span>
            <input value={draft.remarks ?? ""} onChange={(event) => updateDraft({ remarks: event.target.value })} />
          </label>
          <button type="submit" disabled={isCreating || isLoading || !drawingFileId}>
            {isCreating ? "추가 중…" : "추가"}
          </button>
        </form>
      </details>

      <section className="panel">
        <div className="section-heading">
          <h2>실별 마감표</h2>
          <span className="count-label">
            {filteredRows.length} / {rows.length}건
          </span>
        </div>
        <div className="measurement-filter-grid">
          <label>
            <span>실</span>
            <input value={roomFilter} placeholder="119 or lobby" onChange={(event) => setRoomFilter(event.target.value)} />
          </label>
          <label>
            <span>마감</span>
            <input value={finishFilter} placeholder="tile, paint, GWB" onChange={(event) => setFinishFilter(event.target.value)} />
          </label>
          <label>
            <span>검수 상태</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as ReviewStatus | "")}>
              {statusFilters.map((status) => (
                <option key={status || "ALL"} value={status}>
                  {status ? statusLabels[status] : "전체"}
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
                  <th>실 번호</th>
                  <th>실 이름</th>
                  <th>바닥</th>
                  <th>걸레받이</th>
                  <th>벽</th>
                  <th>천장</th>
                  <th>높이</th>
                  <th>검수 상태</th>
                  <th>출처</th>
                  <th>작업</th>
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
                            {statusLabels[status]}
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
                          저장
                        </button>
                        <button
                          type="button"
                          className="button-secondary compact-button danger-button"
                          disabled={pendingRowId === row.id || isReadOnly(row)}
                          onClick={() => handleReject(row)}
                        >
                          거절
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>{rows.length ? "조건에 맞는 마감이 없습니다. 필터를 조정하세요." : isLoading ? "마감표를 불러오는 중…" : error ? "마감표를 불러오지 못했습니다. 위 오류를 확인하고 다시 불러오세요." : drawingFileId ? "마감표가 없습니다. 후보를 추출하거나 실별 마감을 추가하세요." : "프로젝트와 도면 PDF를 선택하면 마감표가 표시됩니다."}</EmptyState>
        )}
      </section>
    </>
  );
}
