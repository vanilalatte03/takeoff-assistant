import { DrawingFilePicker, useDrawingFileSelection } from "../components/DrawingFilePicker";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

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
import { measurementLabels } from "../measurementLabels";
import { statusLabels, StatusBadge } from "../components/StatusBadge";
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
    throw new Error("도면 PDF를 선택하세요.");
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
  const [drawingFileId, setDrawingFileId] = useDrawingFileSelection();
  return <><section className="panel drawing-context"><DrawingFilePicker value={drawingFileId} onChange={setDrawingFileId} /></section>
    <MeasurementsPageContent key={drawingFileId} drawingFileId={drawingFileId} /></>;
}

function MeasurementsPageContent({ drawingFileId }: { drawingFileId: string }) {
  const [rows, setRows] = useState<Measurement[]>([]);
  const [roomStatus, setRoomStatus] = useState<DrawingFileRoomStatus | null>(null);
  const [isLoading, setIsLoading] = useState(!!drawingFileId);
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
  const inspectorRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (inspectorRef.current) inspectorRef.current.scrollTop = 0;
  }, [selectedMeasurementId]);

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

  async function loadRows(id: number, active = () => true) {
    const [loaded, status] = await Promise.all([listMeasurements(id), getDrawingFileRoomStatus(id)]);
    if (!active()) return loaded;
    setRoomStatus(status);
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
      setMessage(`산출 ${loaded.length}건을 불러왔습니다.`);
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
      setMessage(`후보 ${result.measurements.length}건 생성 · 전체 ${loaded.length}건`);
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
      setMessage(`${exportFile.filename} 파일을 내보냈습니다.`);
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
      setMessage(`산출 #${rejected.id}을 거절했습니다.`);
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
        throw new Error("병합할 원본 산출을 한 건 이상 선택하세요.");
      }
      const merged = await mergeMeasurements({ target_id: targetId, source_ids: sourceIds });
      const id = parseDrawingFileId(drawingFileId);
      const loaded = await loadRows(id);
      setSelectedMeasurementId(merged.id);
      setMergeSourceIds([]);
      setMessage(`원본 ${sourceIds.length}건을 산출 #${merged.id}에 병합했습니다. 전체 ${loaded.length}건`);
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
        title="산출 내역 검수"
        description="산출을 선택해 원본과 계산 근거를 검토한 뒤 확정하고 Excel로 내보내세요."
        actions={
          <button type="button" className="button-secondary" disabled={isDownloading || !drawingFileId || isLoading} onClick={handleDownload}>
            {isDownloading ? "내보내는 중…" : "Excel 내보내기"}
          </button>
        }
      />

      <section className="review-actions">
        <form className="button-row" onSubmit={handleLoad}>

          <button type="submit" disabled={isLoading || !drawingFileId}>
            {isLoading ? "불러오는 중…" : "다시 불러오기"}
          </button>
          <button type="button" className="button-secondary" disabled={isLoading || !drawingFileId} onClick={handleGenerate}>
            산출 후보 생성
          </button>
        </form>
        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
      </section>

      <details className="panel room-progress">
        <summary>실별 검수 현황 · {roomStatus?.rooms.length ?? 0}개 실</summary>
        <div className="section-heading">
          <h2>실별 검수 현황</h2>
          <span className="count-label">{roomStatus?.rooms.length ?? 0}개 실</span>
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
                <span>{room.room_name ?? "이름 없는 실"}</span>
                <dl>
                  <div>
                    <dt>전체</dt>
                    <dd>{room.total_count}</dd>
                  </div>
                  <div>
                    <dt>수량 있음</dt>
                    <dd>{room.quantity_count}</dd>
                  </div>
                  <div>
                    <dt>확정</dt>
                    <dd>{room.confirmed_count}</dd>
                  </div>
                  <div>
                    <dt>검토 필요</dt>
                    <dd>{room.needs_review_count}</dd>
                  </div>
                  <div>
                    <dt>수량 누락</dt>
                    <dd>{room.missing_quantity_count}</dd>
                  </div>
                </dl>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState>도면을 선택하면 실별 검수 현황을 확인할 수 있습니다.</EmptyState>
        )}
      </details>

      <div className="review-workspace">
      <section className="panel measurement-list" aria-label="산출 목록" aria-busy={isLoading}>
        <div className="section-heading">
          <h2>산출 목록</h2>
          <span className="count-label">
            {filteredRows.length} / {rows.length}건
          </span>
        </div>
        <div className="measurement-filter-grid">
          <label>
            <span>실 번호</span>
            <input value={roomNoFilter} placeholder="119" onChange={(event) => setRoomNoFilter(event.target.value)} />
          </label>
          <label>
            <span>검수 상태</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as ReviewStatus | "")}>
              {statusOptions.map((status) => (
                <option key={status || "ALL"} value={status}>
                  {status ? statusLabels[status] : "전체"}
                </option>
              ))}
            </select>
          </label>
        </div>
        <details className="advanced-filters"><summary>상세 필터</summary><div className="measurement-filter-grid">
          <label>
            <span>분류</span>
            <input value={categoryFilter} placeholder="PARTITION" onChange={(event) => setCategoryFilter(event.target.value)} />
          </label>
          <label>
            <span>마감 코드</span>
            <input value={codeFilter} placeholder="GWB or 5A" onChange={(event) => setCodeFilter(event.target.value)} />
          </label>
          <label>
            <span>산출 종류</span>
            <select value={measurementTypeFilter} onChange={(event) => setMeasurementTypeFilter(event.target.value as MeasurementType | "")}>
              {measurementTypeOptions.map((type) => (
                <option key={type || "ALL"} value={type}>
                  {type ? measurementLabels[type] : "전체"}
                </option>
              ))}
            </select>
          </label>
        </div></details>
      {mergeSourceIds.length > 0 && <section className="merge-selection" aria-label="산출 병합">
        <div className="section-heading">
          <h2>산출 병합</h2>
          <span className="count-label">{mergeSourceIds.length} 개 원본 선택</span>
        </div>
        <div className="merge-grid">
          <label>
            <span>병합 대상</span>
            <select value={mergeTargetId} onChange={(event) => { setMergeTargetId(event.target.value); setMergeSourceIds((current) => current.filter((id) => String(id) !== event.target.value)); }} disabled={!mergeableRows.length}>
              {mergeableRows.map((row) => (
                <option key={row.id} value={row.id}>
                  #{row.id} {row.room_no ?? "-"} {row.category} {row.finish_code}
                </option>
              ))}
            </select>
          </label>
          <button type="button" disabled={isMerging || !mergeTargetId || !mergeSourceIds.length} onClick={handleMerge}>
            {isMerging ? "병합 중…" : "선택한 산출 병합"}
          </button>
        </div>
      </section>}

        {filteredRows.length ? (
          <div className="table-wrap measurement-table" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th>검토</th>
                  <th>병합</th>
                  <th>실</th>
                  <th>마감 · 항목</th>
                  <th className="numeric-cell">수량</th>
                  <th>상태</th>
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
                        className="button-secondary compact-button" aria-label={`산출 #${row.id} 검토`} aria-pressed={selectedMeasurementId === row.id}
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedMeasurementId(row.id);
                        }}
                      >
                        검토
                      </button>
                    </td>
                    <td onClick={(event) => event.stopPropagation()}>
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={mergeSourceIds.includes(row.id)}
                          disabled={String(row.id) === mergeTargetId || row.status === "CONFIRMED" || row.status === "REJECTED"}
                          onChange={(event) => toggleMergeSource(row.id, event.target.checked)}
                        />
                        <span className="sr-only">#{row.id} 병합 원본</span>
                      </label>
                    </td>
                    <td>
                      <strong>{row.room_no ?? "-"}</strong>
                      <span className="muted-cell">{row.room_name ?? ""}</span>
                    </td>
                    <td><strong>{row.finish_code}</strong><span className="muted-cell">{row.category} · {measurementLabels[row.measurement_type]}</span></td>
                    <td className="numeric-cell">{row.quantity ?? "—"}<span className="muted-cell">{row.unit ?? ""}</span></td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>{rows.length ? "조건에 맞는 산출이 없습니다. 필터를 조정하세요." : isLoading ? "산출 내역을 불러오는 중…" : error ? "산출 내역을 불러오지 못했습니다. 위 오류를 확인하고 다시 불러오세요." : drawingFileId ? "산출 내역이 없습니다. 마감표 검수 후 산출 후보를 생성하세요." : "프로젝트와 도면 PDF를 선택하면 산출 내역이 표시됩니다."}</EmptyState>
        )}
      </section>
      <aside ref={inspectorRef} className="review-inspector" aria-label="선택한 산출 검토">
        {selectedMeasurement && <div className="inspector-heading">
          <strong>선택한 산출 #{selectedMeasurement.id}</strong>
          <button type="button" className="button-secondary compact-button danger-button"
            disabled={pendingRowId === selectedMeasurement.id || selectedMeasurement.status === "CONFIRMED" || selectedMeasurement.status === "REJECTED"}
            onClick={() => handleReject(selectedMeasurement)}>산출 거절</button>
        </div>}
        <MeasurementCalculationForm measurement={selectedMeasurement} onSaved={handleMeasurementSaved} />
      </aside>
      </div>
    </>
  );
}
