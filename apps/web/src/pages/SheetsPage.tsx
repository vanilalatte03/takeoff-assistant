import { FormEvent, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { findRoomPageCandidates, searchDrawingSheets } from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import type { DrawingSheetRole, DrawingSheetSearchResult, RoomPageCandidate } from "../types/api";

const roleOptions: Array<DrawingSheetRole | ""> = [
  "",
  "FINISH_SCHEDULE",
  "FLOOR_PLAN",
  "ENLARGED_FLOOR_PLAN",
  "CEILING_PLAN",
  "PARTITION_PLAN",
  "PARTITION_DETAIL",
  "DOOR_SCHEDULE",
  "WINDOW_SCHEDULE",
  "DETAIL",
  "UNKNOWN",
];

function parseDrawingFileId(value: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error("Drawing File ID는 1 이상의 정수여야 합니다.");
  }
  return parsed;
}

export function SheetsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialDrawingFileId = searchParams.get("drawingFileId") ?? "";
  const [drawingFileId, setDrawingFileId] = useState(initialDrawingFileId);
  const [sheetNo, setSheetNo] = useState("");
  const [keyword, setKeyword] = useState("");
  const [sheetRole, setSheetRole] = useState<DrawingSheetRole | "">("");
  const [roomQuery, setRoomQuery] = useState("");
  const [results, setResults] = useState<DrawingSheetSearchResult[]>([]);
  const [roomCandidates, setRoomCandidates] = useState<RoomPageCandidate[]>([]);
  const [roomWarnings, setRoomWarnings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRoomLoading, setIsRoomLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const resolvedDrawingFileId = useMemo(() => {
    const parsed = Number(drawingFileId);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  }, [drawingFileId]);

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const id = parseDrawingFileId(drawingFileId);
      const response = await searchDrawingSheets(id, { sheetNo, keyword, sheetRole });
      setResults(response.results);
      setSearchParams({ drawingFileId: String(id) });
    } catch (caught) {
      setError(caught);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRoomSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsRoomLoading(true);
    setRoomWarnings([]);

    try {
      const id = parseDrawingFileId(drawingFileId);
      const response = await findRoomPageCandidates(id, roomQuery);
      setRoomCandidates(response.candidates);
      setRoomWarnings(response.warnings);
      setSearchParams({ drawingFileId: String(id) });
    } catch (caught) {
      setError(caught);
    } finally {
      setIsRoomLoading(false);
    }
  }

  return (
    <>
      <PageHeader title="도면 목록/검색" description="도면 번호, 키워드, 역할을 분리해 필요한 도면만 좁혀 조회합니다." />

      <section className="panel">
        <div className="section-heading">
          <h2>Room page candidates</h2>
          <span className="count-label">{roomCandidates.length} candidates</span>
        </div>
        <form className="toolbar-form compact" onSubmit={handleRoomSearch}>
          <label>
            <span>Drawing File ID</span>
            <input value={drawingFileId} inputMode="numeric" onChange={(event) => setDrawingFileId(event.target.value)} />
          </label>
          <label>
            <span>Room No / Name</span>
            <input value={roomQuery} placeholder="119 or OFFICE" onChange={(event) => setRoomQuery(event.target.value)} />
          </label>
          <button type="submit" disabled={isRoomLoading || !roomQuery.trim()}>
            {isRoomLoading ? "Finding..." : "Find room"}
          </button>
        </form>
        {roomWarnings.length ? (
          <div className="message message-warning">
            <ul className="message-list">
              {roomWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {roomCandidates.length ? (
          <div className="table-wrap room-candidate-table">
            <table>
              <thead>
                <tr>
                  <th>Page</th>
                  <th>Sheet</th>
                  <th>Room</th>
                  <th>Role</th>
                  <th>Confidence</th>
                  <th>Evidence</th>
                  <th>Open</th>
                </tr>
              </thead>
              <tbody>
                {roomCandidates.map((candidate) => (
                  <tr key={`${candidate.page_index}-${candidate.sheet_no ?? "unknown"}`}>
                    <td>{candidate.page_index}</td>
                    <td>
                      <strong>{candidate.sheet_no ?? "-"}</strong>
                      <span className="muted-cell">{candidate.sheet_title ?? ""}</span>
                    </td>
                    <td>
                      <strong>{candidate.room_no ?? "-"}</strong>
                      <span className="muted-cell">{candidate.room_name ?? ""}</span>
                    </td>
                    <td>{candidate.sheet_role}</td>
                    <td>{candidate.confidence.toFixed(2)}</td>
                    <td>{candidate.evidence.join("; ")}</td>
                    <td>
                      {resolvedDrawingFileId ? (
                        <Link to={`/drawings/${resolvedDrawingFileId}/pages/${candidate.page_index}`}>Open</Link>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        <ErrorMessage error={error} />
      </section>

      <section className="panel">
        <form className="toolbar-form" onSubmit={handleSearch}>
          <label>
            <span>Drawing File ID</span>
            <input value={drawingFileId} inputMode="numeric" onChange={(event) => setDrawingFileId(event.target.value)} />
          </label>
          <label>
            <span>Sheet No</span>
            <input value={sheetNo} placeholder="AE101" onChange={(event) => setSheetNo(event.target.value)} />
          </label>
          <label>
            <span>Keyword</span>
            <input value={keyword} placeholder="Room 110, VCT, GWB" onChange={(event) => setKeyword(event.target.value)} />
          </label>
          <label>
            <span>역할</span>
            <select value={sheetRole} onChange={(event) => setSheetRole(event.target.value as DrawingSheetRole | "")}>
              {roleOptions.map((role) => (
                <option key={role || "ALL"} value={role}>
                  {role || "전체"}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={isLoading}>
            {isLoading ? "검색 중" : "검색"}
          </button>
        </form>
        <ErrorMessage error={error} />
        {results.length > 50 ? (
          <div className="message message-warning">검색 결과가 많습니다. Sheet No, Keyword, Role 조건을 더 좁혀 검색하세요.</div>
        ) : null}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>검색 결과</h2>
          <span className="count-label">{results.length}건</span>
        </div>
        {results.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Page</th>
                  <th>Sheet No</th>
                  <th>Sheet Title</th>
                  <th>Role</th>
                  <th>Confidence</th>
                  <th>상세</th>
                </tr>
              </thead>
              <tbody>
                {results.map((sheet) => (
                  <tr key={`${sheet.page_index}-${sheet.sheet_no ?? "unknown"}`}>
                    <td>{sheet.page_index}</td>
                    <td>{sheet.sheet_no ?? "-"}</td>
                    <td>{sheet.sheet_title ?? "-"}</td>
                    <td>{sheet.sheet_role}</td>
                    <td>{sheet.confidence === null ? "-" : sheet.confidence.toFixed(2)}</td>
                    <td>
                      {resolvedDrawingFileId ? (
                        <Link to={`/drawings/${resolvedDrawingFileId}/pages/${sheet.page_index}`}>열기</Link>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>검색 결과가 없습니다.</EmptyState>
        )}
      </section>
    </>
  );
}
