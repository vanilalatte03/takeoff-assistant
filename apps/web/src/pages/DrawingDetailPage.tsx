import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { drawingSearchParams, readDrawingSearch } from "../drawingSearch";
import { pageImageUrl, searchDrawingSheets } from "../api/client";
import { EmptyState, ErrorMessage } from "../components/ApiState";
import { ManualMeasurementViewer } from "../components/ManualMeasurementViewer";
import { PageHeader } from "../components/PageHeader";
import type { DrawingSheetSearchResult } from "../types/api";

function parseRouteNumber(value: string | undefined, label: string, allowZero: boolean) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || (allowZero ? parsed < 0 : parsed <= 0)) {
    throw new Error(`${label} 값이 올바르지 않습니다.`);
  }
  return parsed;
}

export function DrawingDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const drawingFileId = parseRouteNumber(params.drawingFileId, "Drawing File ID", false);
  const pageIndex = parseRouteNumber(params.pageIndex, "Page index", true);
  const listSearch = drawingSearchParams(drawingFileId, readDrawingSearch(searchParams)).toString();
  const detailSearch = searchParams.size ? `?${listSearch}` : "";
  const [pageInput, setPageInput] = useState(String(pageIndex + 1));
  const [sheets, setSheets] = useState<DrawingSheetSearchResult[]>([]);
  const [loadedFileId, setLoadedFileId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadRevision, retryLoad] = useState(0);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [imageError, setImageError] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const imageUrl = useMemo(() => pageImageUrl(drawingFileId, pageIndex), [drawingFileId, pageIndex]);
  const currentSheets = loadedFileId === drawingFileId ? sheets : [];
  const sheet = currentSheets.find((item) => item.page_index === pageIndex);
  const availablePages = [...new Set(currentSheets.map((item) => item.page_index))].sort((a, b) => a - b);
  const previousPage = [...availablePages].reverse().find((index) => index < pageIndex);
  const nextPage = availablePages.find((index) => index > pageIndex);
  const canNavigate = !isLoading && !loadError && availablePages.length > 0;

  useEffect(() => {
    setPageInput(String(pageIndex + 1));
    setImageError(false);
    setError(null);
  }, [drawingFileId, pageIndex]);

  useEffect(() => {
    let cancelled = false;
    setSheets([]);
    setLoadedFileId(null);
    setIsLoading(true);
    setLoadError(null);
    searchDrawingSheets(drawingFileId, {})
      .then((response) => {
        if (cancelled) return;
        setSheets(response.results);
        setLoadedFileId(drawingFileId);
      })
      .catch((caught) => { if (!cancelled) setLoadError(caught); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [drawingFileId, loadRevision]);

  function moveToPage(index: number) {
    setError(null);
    navigate(`/drawings/${drawingFileId}/pages/${index}${detailSearch}`);
  }

  function handlePageMove(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canNavigate) return;
    try {
      const nextPage = parseRouteNumber(pageInput, "PDF 쪽 번호", false) - 1;
      if (!availablePages.includes(nextPage)) {
        throw new Error("해당 쪽은 처리된 도면 목록에 없습니다. 도면 목록에서 처리 상태를 확인하세요.");
      }
      moveToPage(nextPage);
    } catch (caught) { setError(caught); }
  }

  return (
    <div className="drawing-workspace">
      <PageHeader
        title={sheet?.sheet_no ? `${sheet.sheet_no} · 도면 측정` : "도면 측정"}
        description="기준 길이로 스케일을 맞춘 뒤 도면 위에서 길이와 면적을 측정하세요."
        actions={<Link to={`/drawings?${listSearch}`}>목록으로</Link>}
      />

      <section className="panel drawing-toolbar" aria-label="도면 정보와 페이지 이동">
        <div className="drawing-sheet-info">
          <strong>{sheet?.sheet_title ?? (isLoading ? "도면 정보 불러오는 중…" : "도면 정보 없음")}</strong>
          <span>PDF {pageIndex + 1}쪽 · {sheet?.sheet_role ?? "역할 미확인"}
            {sheet?.confidence != null ? ` · 분류 신뢰도 ${sheet.confidence.toFixed(2)}` : ""}</span>
        </div>
        <div className="page-navigation" aria-label="PDF 쪽 이동">
          <button type="button" className="button-secondary" disabled={!canNavigate || previousPage === undefined}
            onClick={() => { if (previousPage !== undefined) moveToPage(previousPage); }}>이전 쪽</button>
          <form className="page-jump" onSubmit={handlePageMove}>
          <label><span>PDF 쪽 번호</span><input type="number" min="1" step="1" value={pageInput}
            disabled={!canNavigate} onChange={(event) => setPageInput(event.target.value)} /></label>
          <button type="submit" className="button-secondary" disabled={!canNavigate}>이동</button>
          </form>
          <button type="button" className="button-secondary" disabled={!canNavigate || nextPage === undefined}
            onClick={() => { if (nextPage !== undefined) moveToPage(nextPage); }}>다음 쪽</button>
        </div>
        {!isLoading && !loadError && !availablePages.length && <p className="page-navigation-note">처리된 도면이 없습니다. 도면 목록에서 페이지 처리를 확인하세요.</p>}
        {!isLoading && !loadError && availablePages.length > 0 && !sheet && <p className="page-navigation-note">현재 쪽은 처리된 도면 목록에 없습니다. 이전·다음 쪽이나 목록에서 도면을 선택하세요.</p>}
        <ErrorMessage error={loadError} />
        {loadError ? <button type="button" className="button-secondary" onClick={() => retryLoad((revision) => revision + 1)}>도면 정보 다시 불러오기</button> : null}
        <ErrorMessage error={error} />
      </section>

      {imageError ? (
        <section className="panel">
          <EmptyState>페이지 이미지가 없습니다. PDF 업로드 후 페이지 처리를 먼저 실행해야 합니다.</EmptyState>
        </section>
      ) : (
        <ManualMeasurementViewer
          drawingFileId={drawingFileId}
          pageIndex={pageIndex}
          imageUrl={imageUrl}
          sourceSheetNo={sheet?.sheet_no}
          onImageError={() => setImageError(true)}
        />
      )}
    </div>
  );
}
