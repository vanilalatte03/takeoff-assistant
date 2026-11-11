import { DrawingFilePicker, useDrawingFileSelection } from "../components/DrawingFilePicker";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { findRoomPageCandidates, searchDrawingSheets } from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import { drawingSearchParams, readDrawingSearch, sheetRoles } from "../drawingSearch";
import type { DrawingSheetRole, DrawingSheetSearchResult, RoomPageCandidate } from "../types/api";

export function SheetsPage() {
  const [drawingFileId, selectDrawingFile] = useDrawingFileSelection();
  return <><section className="panel drawing-context"><DrawingFilePicker value={drawingFileId} onChange={(next) => selectDrawingFile(next, true)} /></section>
    <SheetsPageContent key={drawingFileId} drawingFileId={drawingFileId} /></>;
}

function SheetsPageContent({ drawingFileId }: { drawingFileId: string }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const applied = readDrawingSearch(searchParams);
  const [sheetNo, setSheetNo] = useState(applied.sheetNo);
  const [keyword, setKeyword] = useState(applied.keyword);
  const [sheetRole, setSheetRole] = useState<DrawingSheetRole | "">(applied.sheetRole);
  const [roomQuery, setRoomQuery] = useState(applied.roomQuery);
  const [results, setResults] = useState<DrawingSheetSearchResult[]>([]);
  const [roomCandidates, setRoomCandidates] = useState<RoomPageCandidate[]>([]);
  const [roomWarnings, setRoomWarnings] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(!!drawingFileId);
  const [isRoomLoading, setIsRoomLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [roomError, setRoomError] = useState<unknown>(null);
  const [searchRevision, retrySearch] = useState(0);
  const [roomRevision, retryRoomSearch] = useState(0);

  const resolvedDrawingFileId = useMemo(() => {
    const parsed = Number(drawingFileId);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  }, [drawingFileId]);

  useEffect(() => {
    setSheetNo(applied.sheetNo);
    setKeyword(applied.keyword);
    setSheetRole(applied.sheetRole);
  }, [applied.sheetNo, applied.keyword, applied.sheetRole]);

  useEffect(() => { setRoomQuery(applied.roomQuery); }, [applied.roomQuery]);

  useEffect(() => {
    let active = true;
    setResults([]);
    setError(null);
    setIsLoading(!!resolvedDrawingFileId);
    if (!resolvedDrawingFileId) return;
    void searchDrawingSheets(resolvedDrawingFileId, {
      sheetNo: applied.sheetNo, keyword: applied.keyword, sheetRole: applied.sheetRole,
    }).then((response) => { if (active) setResults(response.results); })
      .catch((caught) => { if (active) setError(caught); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [resolvedDrawingFileId, applied.sheetNo, applied.keyword, applied.sheetRole, searchRevision]);

  useEffect(() => {
    let active = true;
    setRoomCandidates([]);
    setRoomWarnings([]);
    setRoomError(null);
    setIsRoomLoading(!!resolvedDrawingFileId && !!applied.roomQuery);
    if (!resolvedDrawingFileId || !applied.roomQuery) return;
    void findRoomPageCandidates(resolvedDrawingFileId, applied.roomQuery)
      .then((response) => {
        if (!active) return;
        setRoomCandidates(response.candidates);
        setRoomWarnings(response.warnings);
      })
      .catch((caught) => { if (active) setRoomError(caught); })
      .finally(() => { if (active) setIsRoomLoading(false); });
    return () => { active = false; };
  }, [resolvedDrawingFileId, applied.roomQuery, roomRevision]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resolvedDrawingFileId) return;
    const next = drawingSearchParams(drawingFileId, { ...applied, sheetNo, keyword, sheetRole });
    const unchanged = next.toString() === drawingSearchParams(drawingFileId, applied).toString();
    if (unchanged) retrySearch((revision) => revision + 1);
    setSearchParams(next, { replace: unchanged });
  }

  function handleRoomSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!resolvedDrawingFileId) return;
    const next = drawingSearchParams(drawingFileId, { ...applied, roomQuery });
    const unchanged = next.toString() === drawingSearchParams(drawingFileId, applied).toString();
    if (unchanged) retryRoomSearch((revision) => revision + 1);
    setSearchParams(next, { replace: unchanged });
  }

  const contextSearch = drawingSearchParams(drawingFileId, applied).toString();

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
            <span>Room No / Name</span>
            <input value={roomQuery} placeholder="119 or OFFICE" onChange={(event) => setRoomQuery(event.target.value)} />
          </label>
          <button type="submit" disabled={isRoomLoading || !resolvedDrawingFileId || !roomQuery.trim()}>
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
                        <Link to={`/drawings/${resolvedDrawingFileId}/pages/${candidate.page_index}?${contextSearch}`}>Open</Link>
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
        <ErrorMessage error={roomError} />
        {applied.roomQuery && !isRoomLoading && !roomError && !roomCandidates.length ? (
          <EmptyState>조건에 맞는 실 도면 후보가 없습니다.</EmptyState>
        ) : null}
      </section>

      <section className="panel">
        <form className="toolbar-form" onSubmit={handleSearch}>

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
              {sheetRoles.map((role) => (
                <option key={role || "ALL"} value={role}>
                  {role || "전체"}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={isLoading || !resolvedDrawingFileId}>
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
                        <Link to={`/drawings/${resolvedDrawingFileId}/pages/${sheet.page_index}?${contextSearch}`}>열기</Link>
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
          <EmptyState>{!resolvedDrawingFileId ? "프로젝트와 도면 PDF를 선택하세요." : isLoading ? "도면 목록을 불러오는 중…" : error ? "도면 목록을 불러오지 못했습니다. 검색을 눌러 다시 시도하세요." : "검색 결과가 없습니다."}</EmptyState>
        )}
      </section>
    </>
  );
}
