import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { classifyDrawingSheets, detectDrawingSheets, processDrawingPages, uploadDrawingFile } from "../api/client";
import { ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import type { DrawingFile } from "../types/api";

type UploadStep = "upload" | "process" | "detect" | "classify";

const stepLabels: Record<UploadStep, string> = {
  upload: "업로드",
  process: "페이지 처리",
  detect: "도면 정보 추출",
  classify: "역할 분류",
};

function toPositiveInteger(value: string, label: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${label}는 1 이상의 정수여야 합니다.`);
  }
  return parsed;
}

export function UploadPage() {
  const [projectId, setProjectId] = useState("1");
  const [file, setFile] = useState<File | null>(null);
  const [drawingFile, setDrawingFile] = useState<DrawingFile | null>(null);
  const [pendingStep, setPendingStep] = useState<UploadStep | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    try {
      if (!file) {
        throw new Error("업로드할 PDF 파일을 선택해 주세요.");
      }
      setPendingStep("upload");
      const uploaded = await uploadDrawingFile(toPositiveInteger(projectId, "Project ID"), file);
      setDrawingFile(uploaded);
      setMessage(`업로드 완료: ${uploaded.original_filename}`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingStep(null);
    }
  }

  async function runStep(step: Exclude<UploadStep, "upload">) {
    if (!drawingFile) {
      return;
    }

    setError(null);
    setMessage(null);
    setPendingStep(step);
    try {
      if (step === "process") {
        const result = await processDrawingPages(drawingFile.id);
        setDrawingFile({ ...drawingFile, page_count: result.page_count });
        setMessage(`페이지 처리 완료: ${result.page_count} 페이지`);
      }
      if (step === "detect") {
        const result = await detectDrawingSheets(drawingFile.id);
        setMessage(`도면 정보 추출 완료: ${result.sheets.length} 페이지`);
      }
      if (step === "classify") {
        const result = await classifyDrawingSheets(drawingFile.id);
        setMessage(`역할 분류 완료: ${result.sheets.length} 페이지`);
      }
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingStep(null);
    }
  }

  return (
    <>
      <PageHeader
        title="PDF 업로드"
        description="텍스트 추출 가능한 PDF는 페이지 처리 후 검색과 후보 추출 흐름으로 이어집니다."
      />

      <section className="panel">
        <form className="form-grid" onSubmit={handleUpload}>
          <label>
            <span>Project ID</span>
            <input value={projectId} inputMode="numeric" onChange={(event) => setProjectId(event.target.value)} />
          </label>
          <label className="file-input">
            <span>PDF 파일</span>
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={pendingStep !== null}>
              {pendingStep === "upload" ? "업로드 중" : "PDF 업로드"}
            </button>
          </div>
        </form>

        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
      </section>

      {drawingFile ? (
        <section className="panel">
          <div className="section-heading">
            <h2>업로드된 도면 파일</h2>
            <Link className="button button-secondary" to={`/drawings?drawingFileId=${drawingFile.id}`}>
              도면 검색으로 이동
            </Link>
          </div>
          <dl className="metadata-grid">
            <div>
              <dt>파일명</dt>
              <dd>{drawingFile.original_filename}</dd>
            </div>
            <div>
              <dt>Drawing File ID</dt>
              <dd>{drawingFile.id}</dd>
            </div>
            <div>
              <dt>페이지 수</dt>
              <dd>{drawingFile.page_count}</dd>
            </div>
            <div>
              <dt>업로드 시각</dt>
              <dd>{new Date(drawingFile.created_at).toLocaleString()}</dd>
            </div>
          </dl>
          <div className="button-row">
            {(["process", "detect", "classify"] as const).map((step) => (
              <button
                key={step}
                type="button"
                className="button-secondary"
                disabled={pendingStep !== null}
                onClick={() => runStep(step)}
              >
                {pendingStep === step ? `${stepLabels[step]} 중` : stepLabels[step]}
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
