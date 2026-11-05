import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { assistConfig, searchAssist } from "../api/client";
import type { AssistResult } from "../api/client";
import { DrawingFilePicker, useDrawingFileSelection } from "../components/DrawingFilePicker";
import { ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import { AssistDraftForm } from "../components/AssistDraftForm";
import { ComparisonPanel } from "../components/ComparisonPanel";

export function AssistPage() {
  const [fileId, select] = useDrawingFileSelection();
  return <><PageHeader title="산출 탐색 보조" description="관련 도면의 텍스트 근거를 찾아 원본 페이지에서 검토합니다." />
    <section className="panel toolbar-form"><DrawingFilePicker value={fileId} onChange={select} /></section>
    <AssistContent key={fileId} fileId={fileId} /></>;
}

function AssistContent({ fileId }: { fileId: string }) {
  const [request, setRequest] = useState("");
  const [mode, setMode] = useState<"local" | "ai">("local");
  const [available, setAvailable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AssistResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => { assistConfig().then(c => setAvailable(c.ai_available)).catch(setError); }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(null); setResult(null);
    try { setResult(await searchAssist(Number(fileId), request, mode)); }
    catch (e) { setError(e); }
    finally { setBusy(false); }
  }
  return <section className="panel">
    <form onSubmit={submit} className="form-grid">
      <label><span>산출 요청</span><input value={request} maxLength={500} placeholder="110호 ACST 천장 면적 찾아줘" onChange={e => setRequest(e.target.value)} /></label>
      <label><span>탐색 방식</span><select value={mode} onChange={e => setMode(e.target.value as "local" | "ai")}>
        <option value="local">로컬 규칙 검색 (AI 사용 없음)</option>
        <option value="ai" disabled={!available}>AI 도구 검색{available ? "" : " (서버 설정 필요)"}</option>
      </select></label>
      <p>{mode === "ai" ? "입력한 요청 문장이 외부 모델로 전송됩니다. 기밀 정보를 입력하지 마세요. 도면 원문은 이 탐색 단계에서 외부 전송하지 않습니다." : "도면과 요청을 외부로 전송하지 않고 로컬에서 검색합니다."}</p>
      <button disabled={busy || !fileId || !request.trim()}>{busy ? "검색 실행 중…" : "근거 찾기"}</button>
    </form>
    <ErrorMessage error={error} />
    {result && <>
      <p role="status">실행 #{result.run_id} · {result.status} · {result.elapsed_ms}ms</p>
      {result.warnings.map(w => <p className="message message-warning" key={w}>{w}</p>)}
      {result.evidence.map(e => <article className="panel" key={e.sheet_id}>
        <Link to={`/drawings/${fileId}/pages/${e.page_index}`}>{e.sheet_no ?? "도면 번호 미확인"} · {e.sheet_title ?? "제목 미확인"} · PDF {e.page_index + 1}쪽</Link>
        <pre style={{ whiteSpace: "pre-wrap" }}>{e.quote}</pre><small>추출 방식: {e.method} · 검수 필요</small>
      </article>)}
      <details><summary>실행 기록</summary><pre style={{whiteSpace:"pre-wrap"}}>{JSON.stringify(result.trace, null, 2)}</pre></details>
      {result.status === "NEEDS_REVIEW" && <AssistDraftForm key={result.run_id} fileId={fileId} result={result} />}
    </>}
    <ComparisonPanel fileId={fileId} run={result} />
  </section>;
}
