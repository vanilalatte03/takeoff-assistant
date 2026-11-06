import { FormEvent, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { downloadMeasurementsExcel, getWorkflowStatus, listMeasurements, pageImageUrl, prepareWorkflowStage, searchAssist } from "../api/client";
import type { AssistResult, WorkflowStatus } from "../api/client";
import type { Measurement } from "../types/api";
import { DrawingFilePicker, useDrawingFileSelection } from "../components/DrawingFilePicker";
import { ErrorMessage } from "../components/ApiState";
import { AssistDraftForm } from "../components/AssistDraftForm";
import { MeasurementCalculationForm } from "../components/MeasurementCalculationForm";
import { ReviewEvidencePanel } from "../components/ReviewEvidencePanel";
import { PageHeader } from "../components/PageHeader";
import { measurementLabels } from "../measurementLabels";

export function WorkflowPage() {
  const [fileId, select] = useDrawingFileSelection();
  return <>
    <PageHeader title="도면에서 Excel까지" description="도면 준비 → 근거 찾기와 계산 → 원본 검토 → Excel 받기. 결과는 직접 검수하기 전까지 미확정입니다." />
    <section className="panel"><h2>1. 작업할 PDF 선택</h2>
      <p>처음이면 PDF를 올리세요. 이어서 작업할 때는 저장된 PDF를 선택하면 됩니다.</p>
      <Link className="button" to="/upload">새 PDF 업로드</Link>
      <div className="toolbar-form"><DrawingFilePicker value={fileId} onChange={select} /></div>
    </section>
    {fileId ? <WorkflowContent key={fileId} fileId={fileId} /> : <p role="status">프로젝트와 도면 PDF를 선택하세요.</p>}
  </>;
}

export function WorkflowContent({ fileId }: { fileId: string }) {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [rows, setRows] = useState<Measurement[]>([]);
  const [selected, setSelected] = useState("");
  const [request, setRequest] = useState("");
  const [result, setResult] = useState<AssistResult | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [downloaded, setDownloaded] = useState(false);
  const [checked, setChecked] = useState(false);
  const [evidenceVersion, setEvidenceVersion] = useState(0);
  const active = useRef(false);
  const running = useRef(false);
  const loadGeneration = useRef(0);
  const row = rows.find(r => String(r.id) === selected);
  async function load() {
    const generation = ++loadGeneration.current;
    try {
      const [s, r] = await Promise.all([getWorkflowStatus(Number(fileId)), listMeasurements(Number(fileId))]);
      if (!active.current || generation !== loadGeneration.current) return;
      setStatus(s); setRows(r);
      setSelected(old => r.some(v => String(v.id) === old) ? old : String(r.find(v => v.quantity !== null)?.id ?? ""));
    } catch (e) {
      if (active.current && generation === loadGeneration.current) throw e;
    }
  }
  useEffect(() => {
    active.current = true;
    void load().catch(e => { if (active.current) setError(e); });
    return () => { active.current = false; ++loadGeneration.current; };
  }, [fileId]);
  async function run(label: string, action: () => Promise<void>) {
    if (running.current) return;
    running.current = true; setBusy(label); setError(null);
    try { await action(); }
    catch(e) { if (active.current) setError(e); }
    finally { running.current = false; if (active.current) setBusy(""); }
  }
  async function prepare() {
    await run("도면 준비", async () => {
      let current = await getWorkflowStatus(Number(fileId));
      while (active.current && current.completed < current.stages.length) {
        setBusy(current.stages[current.completed]);
        current = await prepareWorkflowStage(Number(fileId));
        if (active.current) setStatus(current);
      }
      if (active.current) await load();
    });
  }
  async function search(event: FormEvent) {
    event.preventDefault();
    await run("근거 검색", async () => {
      setResult(null);
      const found = await searchAssist(Number(fileId), request, "local");
      if (active.current) setResult(found);
    });
  }
  function saved(value: Measurement) {
    if (!active.current) return;
    ++loadGeneration.current;
    setRows(old => old.some(r => r.id === value.id) ? old.map(r => r.id === value.id ? value : r) : [...old, value]);
    setSelected(String(value.id)); setChecked(false); setDownloaded(false);
  }
  async function download() {
    await run("Excel", async () => {
      const exportFile = await downloadMeasurementsExcel(Number(fileId));
      if (!active.current) return;
      const url = URL.createObjectURL(exportFile.blob);
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = exportFile.filename; document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
      setDownloaded(true);
    });
  }
  return <>
    <section className="panel" aria-label="작업 진행">
      <h2>현재 작업</h2>
      <p role="status">{busy ? `${busy} 실행 중…` : downloaded ? "Excel 다운로드 완료. Details와 Review 시트에서 미확정·누락 항목을 확인하세요." : row?.quantity != null ? "다음: 4. 원본·단위·공제를 검토하고 Excel을 받으세요." : status?.ready ? "다음: 3. 원하는 실과 마감 항목의 근거를 찾아 계산하세요." : "다음: 2. 도면 준비를 실행하세요."}</p>
      <p><a href="#workflow-prepare">도면 준비로 이동</a> · <a href="#workflow-search">근거 찾기·계산으로 이동</a> · <a href="#workflow-review">원본 검토·Excel로 이동</a></p>
      <ErrorMessage error={error} />
      {!!error && <button disabled={!!busy} onClick={() => run("상태 확인", load)}>저장 상태 다시 불러오기</button>}
    </section>
    <section className="panel" id="workflow-prepare">
      <h2>2. 도면과 산출 후보 준비</h2>
      <p>처리·감지·분류·마감 추출·후보 생성을 순서대로 진행합니다. 완료한 단계와 저장된 수정·확정·제외 행은 보존합니다.</p>
      {!status && !error && <p>저장 상태를 불러오는 중…</p>}
      <ol>{status?.stages.map((name, index) => <li key={name}>{name} · {index < status.completed ? "완료" : index === status.completed && error ? "실패 또는 미완료 · 재시도 가능" : "대기"}</li>)}</ol>
      <button disabled={!!busy || !status || status.completed === status.stages.length} onClick={prepare}>{error ? "실패 단계부터 준비 재시도" : "도면 준비 시작·이어서 진행"}</button>
      {status?.warnings.map(w => <p className="message message-warning" key={w}>{w}</p>)}
      {status && <p>마감 후보 {status.finish_count}개 · 산출 후보 {rows.length}개</p>}
      {status && status.completed === status.stages.length && !status.ready && <p className="message message-warning">자동 후보가 부족합니다. <Link to={`/drawings?drawingFileId=${fileId}`}>도면 분류 확인</Link> → <Link to={`/room-finishes?drawingFileId=${fileId}`}>마감 후보 직접 입력·수정</Link> → <Link to={`/measurements?drawingFileId=${fileId}`}>산출 후보 생성</Link> 후 돌아와 <button onClick={() => run("상태 확인", load)} disabled={!!busy}>후보 다시 불러오기</button></p>}
    </section>
    <section className="panel" id="workflow-search">
      <h2>3. 근거 찾기와 계산 초안</h2>
      <p>원하는 실 번호·마감 코드·항목을 적으세요. 예: 실 번호와 천장 면적. 도면은 외부 전송 없이 로컬에서 검색합니다.</p>
      <form onSubmit={search} className="form-grid">
        <label><span>찾을 산출 항목</span><input value={request} maxLength={500} onChange={e => setRequest(e.target.value)} placeholder="실 번호, 마감 코드, 천장 면적" /></label>
        <button disabled={!!busy || !request.trim() || !rows.length}>근거 찾기·다시 찾기</button>
      </form>
      {result && <>
        <p role="status">{result.status === "NEEDS_REVIEW" ? "근거를 찾았습니다. 아래 원본을 확인하고 산출 행을 선택하세요." : "근거를 찾지 못했거나 검색이 실패했습니다. 요청을 바꿔 재시도하거나 수동 계산을 사용하세요."}</p>
        {result.warnings.map(w => <p key={w} className="message message-warning">{w}</p>)}
        <div className="workflow-sources">{result.evidence.map(e => <details key={e.sheet_id}><summary>{e.sheet_no ?? "번호 미확인"} · PDF {e.page_index + 1}쪽 · {e.sheet_title}</summary><img className="evidence-review-image" src={pageImageUrl(Number(fileId), e.page_index)} alt={`검색 근거 PDF ${e.page_index + 1}쪽`} /><pre style={{whiteSpace:"pre-wrap"}}>{e.quote}</pre></details>)}</div>
        {result.status === "NEEDS_REVIEW" && <AssistDraftForm key={result.run_id} fileId={fileId} result={result} onSaved={saved} showEvidence={false} />}
      </>}
    </section>
    <section className="panel" id="workflow-review">
      <h2>4. 저장된 산출 검토·Excel 받기</h2>
      <p>계산 후 같은 화면에서 원본과 단위·공제·수량을 대조하세요. 이전에 저장한 행도 선택해 재개할 수 있습니다.</p>
      <label><span>검토할 저장 행</span><select value={selected} onChange={e => {setSelected(e.target.value);setChecked(false);setDownloaded(false);}}><option value="">산출 행을 선택하세요</option>{rows.map(r => <option key={r.id} value={r.id}>{r.room_no} · {measurementLabels[r.measurement_type]} · {r.finish_code} · {r.quantity ?? "미계산"} {r.unit} · {r.status}</option>)}</select></label>
      {row && <>
        <ReviewEvidencePanel key={`${row.id}-${evidenceVersion}`} measurement={row} />
        <button className="button-secondary" disabled={!!busy} onClick={() => setEvidenceVersion(v => v + 1)}>원본 근거 다시 불러오기</button>
        <details><summary>직접 계산·수정 또는 최종 확정</summary><p>근거를 찾지 못하면 원본을 측정한 값으로 계산할 수 있습니다. 확정은 이곳에서 직접 선택할 때만 적용됩니다.</p><MeasurementCalculationForm key={row.id} measurement={row} onSaved={saved} showEvidence={false} /></details>
      </>}
      <p>Excel에는 이 PDF의 모든 산출 행이 담깁니다. 미확정·미계산 행도 상태와 함께 포함되고, 제외 행은 합계에서 빠집니다.</p>
      <label className="checkbox-label"><input type="checkbox" checked={checked} disabled={!row || row.quantity === null} onChange={e => setChecked(e.target.checked)} /><span>선택한 행의 원본·식·수량·단위·출처·공제를 검토했고 나머지 행의 미검수 상태도 확인했습니다</span></label>
      <button disabled={!!busy || !checked} onClick={download}>Excel 다운로드</button>
      {downloaded && <p className="message message-success">Excel을 내려받았습니다. Details에서 저장한 식·단위·출처·상태를, Review에서 남은 검수 항목을 확인하세요.</p>}
    </section>
  </>;
}
