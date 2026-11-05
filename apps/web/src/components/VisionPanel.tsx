import { useEffect, useState } from "react";
import { assistConfig, previewVision, readVision } from "../api/client";
import type { AssistResult } from "../api/client";
import type { DimensionRegion } from "../types/api";
import { ErrorMessage } from "./ApiState";
import { AssistDraftForm } from "./AssistDraftForm";
import { ComparisonPanel } from "./ComparisonPanel";

export function VisionPanel({fileId, pageIndex, region}: {fileId:number; pageIndex:number; region:DimensionRegion}) {
  const [available, setAvailable] = useState(false);
  const [preview, setPreview] = useState<{url:string;hash:string}|null>(null);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<AssistResult|null>(null);
  useEffect(() => { assistConfig().then(c=>setAvailable(c.vision_available)).catch(setError); }, []);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview.url); }, [preview]);
  function cropRegion() {
    return {x:region.x,y:region.y,width:region.width,height:region.height,image_width:region.image_width ?? 0,image_height:region.image_height ?? 0};
  }
  async function loadPreview() {
    setBusy(true);setError(null);setConsent(false);setResult(null);
    try {
      const data = await previewVision(fileId,pageIndex,cropRegion());
      setPreview({url:URL.createObjectURL(data.blob),hash:data.hash});
    } catch(e) {setError(e);}
    finally {setBusy(false);}
  }
  async function read() {
    if(!preview) return;
    setBusy(true);setError(null);setResult(null);
    try {setResult(await readVision(fileId,pageIndex,{region:cropRegion(),preview_sha256:preview.hash,consent,failure_reason:reason,note}));}
    catch(e) {setError(e);}
    finally {setBusy(false);}
  }
  const names:Record<string,string> = {dimension:"치수",finish_code:"마감 코드",room_no:"실 번호"};
  return <section className="panel">
    <h3>선택 영역 이미지 판독 보완</h3>
    <p>텍스트 추출이 부족한 영역만 보완합니다. 미리보기는 로컬에서 만들며, 판독 실행 시 표시된 영역만 외부 모델로 전송합니다.</p>
    {!available && <p>Vision 서버 설정이 없어 현재 이미지 판독은 사용할 수 없습니다. 영역 미리보기와 수동 측정은 사용할 수 있습니다.</p>}
    <button type="button" disabled={busy} onClick={loadPreview}>전송할 영역 미리보기</button>
    {preview && <>
      <img src={preview.url} alt="외부 모델로 전송할 선택 영역 미리보기" style={{maxWidth:"100%",maxHeight:400,objectFit:"contain"}} />
      <label><span>기존 추출의 문제</span><select aria-label="기존 추출의 문제" value={reason} onChange={e=>{setReason(e.target.value);setConsent(false);}}>
        <option value="">문제를 선택하세요</option><option value="no_text">스캔 등으로 텍스트 없음</option><option value="table_layout">표 구조 추출 실패</option><option value="unreadable_text">치수·코드 판독이 부정확함</option>
      </select></label>
      <label><span>실패 상황 메모</span><input maxLength={500} value={note} onChange={e=>{setNote(e.target.value);setConsent(false);}} placeholder="확인할 실·치수·마감 코드와 추출 문제" /></label>
      <label className="checkbox-label"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)} /><span>미리보기의 기밀 정보를 확인했고, 이 선택 영역을 외부 모델로 전송할 권한이 있습니다</span></label>
      <button type="button" disabled={busy || !available || !reason || !note.trim() || !consent} onClick={read}>{busy?"판독 중…":"선택 영역만 판독"}</button>
    </>}
    <ErrorMessage error={error} />
    {result && <>
      <p role="status">이미지 판독 #{result.run_id} · {result.status}</p>
      {result.warnings.map(w=><p className="message message-warning" key={w}>{w}</p>)}
      {(result.vision_candidates??[]).map((c,i)=><p key={i}>{names[c.kind]??c.kind}: {c.raw_text} · 단위 {c.unit === "unknown"?"미확인":c.unit} · 검수 필요</p>)}
      {result.status === "NEEDS_REVIEW" && <AssistDraftForm key={result.run_id} fileId={String(fileId)} result={result} />}
      <ComparisonPanel fileId={String(fileId)} run={result} />
    </>}
  </section>;
}
