import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

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
  const drawingFileId = parseRouteNumber(params.drawingFileId, "Drawing File ID", false);
  const pageIndex = parseRouteNumber(params.pageIndex, "Page index", true);
  const [pageInput, setPageInput] = useState(String(pageIndex + 1));
  const [sheet, setSheet] = useState<DrawingSheetSearchResult | null>(null);
  const [imageError, setImageError] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const imageUrl = useMemo(() => pageImageUrl(drawingFileId, pageIndex), [drawingFileId, pageIndex]);

  useEffect(() => {
    let cancelled = false;
    setPageInput(String(pageIndex + 1));
    setSheet(null);
    setImageError(false);
    setError(null);
    searchDrawingSheets(drawingFileId, {})
      .then((response) => {
        if (cancelled) return;
        setSheet(response.results.find((result) => result.page_index === pageIndex) ?? null);
      })
      .catch((caught) => { if (!cancelled) setError(caught); });
    return () => { cancelled = true; };
  }, [drawingFileId, pageIndex]);

  function handlePageMove(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const nextPage = parseRouteNumber(pageInput, "PDF 쪽 번호", false) - 1;
      navigate(`/drawings/${drawingFileId}/pages/${nextPage}`);
    } catch (caught) { setError(caught); }
  }

  return (
    <div className="drawing-workspace">
      <PageHeader
        title={sheet?.sheet_no ? `${sheet.sheet_no} · 도면 측정` : "도면 측정"}
        description="기준 길이로 스케일을 맞춘 뒤 도면 위에서 길이와 면적을 측정하세요."
        actions={<Link to={`/drawings?drawingFileId=${drawingFileId}`}>목록으로</Link>}
      />

      <section className="panel drawing-toolbar" aria-label="도면 정보와 페이지 이동">
        <div className="drawing-sheet-info">
          <strong>{sheet?.sheet_title ?? "도면 정보 불러오는 중…"}</strong>
          <span>PDF {pageIndex + 1}쪽 · {sheet?.sheet_role ?? "역할 미확인"}
            {sheet?.confidence != null ? ` · 분류 신뢰도 ${sheet.confidence.toFixed(2)}` : ""}</span>
        </div>
        <form className="page-jump" onSubmit={handlePageMove}>
          <label><span>PDF 쪽 번호</span><input type="number" min="1" step="1" value={pageInput}
            onChange={(event) => setPageInput(event.target.value)} /></label>
          <button type="submit" className="button-secondary">이동</button>
        </form>
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
