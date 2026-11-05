import { FormEvent, useEffect, useState } from "react";
import { getEvaluationTrials, saveEvaluationTrial } from "../api/client";
import type { AssistResult, EvaluationTrial } from "../api/client";
import { ErrorMessage } from "./ApiState";

export function ComparisonPanel({fileId,run}:{fileId:string;run:AssistResult|null}) {
  const [task,setTask]=useState("");
  const [mode,setMode]=useState("manual");
  const [elapsed,setElapsed]=useState("");
  const [started,setStarted]=useState<number|null>(null);
  const [corrections,setCorrections]=useState("0");
  const [interventions,setInterventions]=useState("0");
  const [errors,setErrors]=useState("0");
  const [review,setReview]=useState("needs_review");
  const [notes,setNotes]=useState("");
  const [trials,setTrials]=useState<EvaluationTrial[]>([]);
  const [error,setError]=useState<unknown>(null);
  const [busy,setBusy]=useState(false);
  const labels:Record<string,string>={manual:"수동 기준선",local:"로컬 검색 보조",ai:"AI 검색 보조",vision:"이미지 판독 보조"};
  useEffect(()=>{
    let active=true;
    if(fileId) getEvaluationTrials(Number(fileId)).then(data=>{if(active)setTrials(data);}).catch(e=>{if(active)setError(e);});
    return ()=>{active=false;};
  },[fileId]);
  async function submit(event:FormEvent) {
    event.preventDefault();setBusy(true);setError(null);
    try {
      await saveEvaluationTrial(Number(fileId),{task_key:task,mode,run_id:mode==="manual"?null:run?.run_id,
        elapsed_seconds:Number(elapsed),correction_count:Number(corrections),manual_interventions:Number(interventions),error_count:Number(errors),review_result:review,notes});
      setTrials(await getEvaluationTrials(Number(fileId)));
    } catch(e){setError(e);} finally{setBusy(false);}
  }
  return <section className="panel">
    <h2>실사용 비교 기록</h2>
    <p>같은 과제명을 사용해 수동 방식과 보조 방식을 각각 기록하세요. 시간에는 재검토·수정·Excel 확인을 포함합니다. 기록은 사용자의 관찰값이며 정확도나 시간 절감 성과가 자동 검증되지는 않습니다.</p>
    <form className="form-grid" onSubmit={submit}>
      <label><span>비교 과제명</span><input required maxLength={100} value={task} onChange={e=>setTask(e.target.value)} placeholder="예: 110호 ACST 천장" /></label>
      <label><span>비교 방식</span><select aria-label="비교 방식" value={mode} onChange={e=>setMode(e.target.value)}><option value="manual">수동 기준선</option>{run&&<option value={run.mode}>{labels[run.mode]??run.mode} · 현재 실행 #{run.run_id}</option>}</select></label>
      <div className="button-row"><button type="button" disabled={started!==null||!fileId} onClick={()=>{setStarted(Date.now());setElapsed("");}}>과제 시간 시작</button>
        <button type="button" disabled={started===null} onClick={()=>{if(started!==null)setElapsed(String(Math.max(1,Math.round((Date.now()-started)/1000))));setStarted(null);}}>과제 시간 종료</button></div>
      {started!==null&&<p role="status">시간 측정 중입니다. 검수와 Excel 확인까지 마친 뒤 종료하세요.</p>}
      {([['총 소요시간 (초)',elapsed,setElapsed],['수정 횟수',corrections,setCorrections],['수동 개입 횟수',interventions,setInterventions],['확인한 오류 수',errors,setErrors]] as const).map(([label,value,set])=><label key={label}><span>{label}</span><input required type="number" min={label.startsWith('총')?1:0} step="1" value={value} onChange={e=>set(e.target.value)}/></label>)}
      <label><span>최종 검수 결과</span><select aria-label="최종 검수 결과" value={review} onChange={e=>setReview(e.target.value)}><option value="needs_review">추가 검수 필요</option><option value="adopted">실무자가 채택</option><option value="rejected">채택하지 않음</option></select></label>
      <label><span>비교 검수 메모</span><textarea required maxLength={2000} value={notes} onChange={e=>setNotes(e.target.value)} placeholder="공제·면 수 기준, 누락·수정 내용, 검수자, 순서에 따른 학습 영향"/></label>
      <button disabled={busy||!fileId||started!==null||mode!=="manual"&&(!run||run.mode!==mode)}>비교 기록 저장</button>
    </form><ErrorMessage error={error}/>
    {trials.length>0&&<div className="table-wrap"><table><thead><tr><th>과제</th><th>방식</th><th>시간(초)</th><th>수정</th><th>오류</th><th>검수</th></tr></thead><tbody>{trials.map(t=><tr key={t.trial_id}><td>{t.task_key}</td><td>{labels[t.mode]??t.mode}</td><td>{t.elapsed_seconds}</td><td>{t.correction_count}</td><td>{t.error_count}</td><td>{t.review_result}</td></tr>)}</tbody></table></div>}
  </section>;
}
