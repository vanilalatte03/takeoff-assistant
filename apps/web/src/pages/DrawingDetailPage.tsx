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
  const [pageInput, setPageInput] = useState(String(pageIndex));
  const [sheet, setSheet] = useState<DrawingSheetSearchResult | null>(null);
  const [imageError, setImageError] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const imageUrl = useMemo(() => pageImageUrl(drawingFileId, pageIndex), [drawingFileId, pageIndex]);

  useEffect(() => {
    setPageInput(String(pageIndex));
    setImageError(false);
    setError(null);
    searchDrawingSheets(drawingFileId, {})
      .then((response) => {
        setSheet(response.results.find((result) => result.page_index === pageIndex) ?? null);
      })
      .catch(setError);
  }, [drawingFileId, pageIndex]);

  function handlePageMove(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPage = parseRouteNumber(pageInput, "Page index", true);
    navigate(`/drawings/${drawingFileId}/pages/${nextPage}`);
  }

  return (
    <>
      <PageHeader
        title="도면 상세"
        description="렌더링된 페이지 이미지 위에 canvas overlay를 올려 사용자가 직접 스케일과 측정선을 지정합니다."
        actions={<Link to={`/drawings?drawingFileId=${drawingFileId}`}>목록으로</Link>}
      />

      <section className="panel">
        <form className="toolbar-form compact" onSubmit={handlePageMove}>
          <label>
            <span>Drawing File ID</span>
            <input value={drawingFileId} readOnly />
          </label>
          <label>
            <span>Page Index</span>
            <input value={pageInput} inputMode="numeric" onChange={(event) => setPageInput(event.target.value)} />
          </label>
          <button type="submit">이동</button>
        </form>
        <ErrorMessage error={error} />
      </section>

      <section className="panel metadata-panel">
        <dl className="metadata-grid">
          <div>
            <dt>Page</dt>
            <dd>{pageIndex}</dd>
          </div>
          <div>
            <dt>Sheet No</dt>
            <dd>{sheet?.sheet_no ?? "-"}</dd>
          </div>
          <div>
            <dt>Sheet Title</dt>
            <dd>{sheet?.sheet_title ?? "-"}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>{sheet?.sheet_role ?? "-"}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{sheet?.confidence === null || sheet?.confidence === undefined ? "-" : sheet.confidence.toFixed(2)}</dd>
          </div>
        </dl>
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
    </>
  );
}
