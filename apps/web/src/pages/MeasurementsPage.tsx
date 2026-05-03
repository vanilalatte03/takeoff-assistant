import { FormEvent, useMemo, useState } from "react";

import { downloadMeasurementsExcel, generateMeasurements, listMeasurements } from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { MeasurementCalculationForm } from "../components/MeasurementCalculationForm";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import type { Measurement, MeasurementType, ReviewStatus } from "../types/api";

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
    throw new Error("Drawing File ID는 1 이상의 정수여야 합니다.");
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
  const [isLoading, setIsLoading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [selectedMeasurementId, setSelectedMeasurementId] = useState<number | null>(null);
  const [roomNoFilter, setRoomNoFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [codeFilter, setCodeFilter] = useState("");
  const [measurementTypeFilter, setMeasurementTypeFilter] = useState<MeasurementType | "">("");
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | "">("");

  const selectedMeasurement = useMemo(
    () => rows.find((row) => row.id === selectedMeasurementId) ?? null,
    [rows, selectedMeasurementId],
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

  async function loadRows(id: number) {
    const loaded = await listMeasurements(id);
    setRows(loaded);
    setSelectedMeasurementId((current) => {
      if (current && loaded.some((row) => row.id === current)) {
        return current;
      }
      return loaded[0]?.id ?? null;
    });
    return loaded;
  }

  async function handleLoad(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const loaded = await loadRows(parseDrawingFileId(drawingFileId));
      setMessage(`Measurement ${loaded.length}건`);
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
      setMessage(`후보 ${result.measurements.length}건 생성, 전체 ${loaded.length}건`);
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
      setMessage(`${exportFile.filename} 다운로드를 시작했습니다.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsDownloading(false);
    }
  }

  function handleMeasurementSaved(saved: Measurement) {
    setRows((current) => current.map((row) => (row.id === saved.id ? saved : row)));
    setSelectedMeasurementId(saved.id);
  }

  return (
    <>
      <PageHeader
        title="Measurement 목록"
        description="Room Finish 기반 산출 후보를 검수하고 계산 결과를 확인하는 목록입니다."
        actions={
          <button type="button" className="button-secondary" disabled={isDownloading} onClick={handleDownload}>
            {isDownloading ? "Excel 생성 중" : "Excel 다운로드"}
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
            목록 조회
          </button>
          <button type="button" className="button-secondary" disabled={isLoading} onClick={handleGenerate}>
            후보 생성
          </button>
        </form>
        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
      </section>

      <MeasurementCalculationForm measurement={selectedMeasurement} onSaved={handleMeasurementSaved} />

      <section className="panel">
        <div className="section-heading">
          <h2>Measurements</h2>
          <span className="count-label">
            {filteredRows.length} / {rows.length}건
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
                  {type || "전체"}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as ReviewStatus | "")}>
              {statusOptions.map((status) => (
                <option key={status || "ALL"} value={status}>
                  {status || "전체"}
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
                  <th>선택</th>
                  <th>Room</th>
                  <th>Category</th>
                  <th>Finish Code</th>
                  <th>Type</th>
                  <th>Formula</th>
                  <th>Quantity</th>
                  <th>Unit</th>
                  <th>Source Sheets</th>
                  <th>Status</th>
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
                        선택
                      </button>
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>{rows.length ? "필터 조건에 맞는 Measurement가 없습니다." : "조회된 Measurement가 없습니다."}</EmptyState>
        )}
      </section>
    </>
  );
}
