import { FormEvent, useEffect, useState, useRef } from "react";
import { getEvaluationTrials, saveEvaluationTrial, exportEvaluationTrials } from "../api/client";
import type { AssistResult, EvaluationTrial } from "../api/client";
import { ErrorMessage } from "./ApiState";

const pilotFields = [
  ['comparison_set','비교 묶음 ID'],['participant','참여자 식별자'],['observer','관찰자 식별자'],
  ['task_definition','동등 과제 정의·공제·면 수 기준'],['conditions','동일 조건: 장치·앱 revision·모델·설정'],
  ['learning_effect','학습 영향·연습 분리 메모'],['intervention_details','개입 내용 (없으면 없음)'],
  ['error_details','오류 내용 (없으면 없음)'],['reviewer','최종 검수자 (미검수면 미검수)'],
  ['review_evidence','원본·수량·단위·공제·Excel 검수 근거'],['adoption_reason','채택·거절·실패 이유'],
] as const;
export function ComparisonPanel(props:{fileId:string;run:AssistResult|null}) {
  return <ComparisonContent key={props.fileId} {...props}/>;
}
function ComparisonContent({fileId,run}:{fileId:string;run:AssistResult|null}) {
  const [pilotEnabled,setPilotEnabled]=useState(false);
  const [pilot,setPilot]=useState<Record<string,string>>({category:'ceiling',preparation:'included',cache:'cold',sequence:'manual,local,ai',position:'1',outcome:'completed',wrong_evidence_count:'0',preparation_seconds:'0'});
  const [observed,setObserved]=useState('');
  const [practice,setPractice]=useState(false);
  const [complete,setComplete]=useState(false);
  const [timing,setTiming]=useState(false);
  const saveLock=useRef(false);
  const [report,setReport]=useState<Record<string,unknown>|null>(null);
  const editPilot=(key:string,value:string)=>setPilot(p=>({...p,[key]:value}));
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
    setTrials([]);setReport(null);setStarted(null);setElapsed("");setObserved("");setError(null);
    if(fileId) getEvaluationTrials(Number(fileId)).then(data=>{if(active)setTrials(data);}).catch(e=>{if(active)setError(e);});
    return ()=>{active=false;};
  },[fileId]);
  async function submit(event:FormEvent) {
    event.preventDefault();if(saveLock.current)return;saveLock.current=true;setBusy(true);setError(null);
    try {
      await saveEvaluationTrial(Number(fileId),{task_key:task,mode,run_id:mode!=="manual"&&run?.mode===mode?run.run_id:null,
        ...(pilotEnabled?{pilot:{...pilot,schema_version:1,synthetic:false,observed_at:observed,
          sequence:pilot.sequence.split(','),position:Number(pilot.position),wrong_evidence_count:Number(pilot.wrong_evidence_count),preparation_seconds:Number(pilot.preparation_seconds),
          practice,observation_complete:complete,timing_scope_confirmed:timing}}:{}),
        elapsed_seconds:Number(elapsed),correction_count:Number(corrections),manual_interventions:Number(interventions),error_count:Number(errors),review_result:review,notes});
      setTrials(await getEvaluationTrials(Number(fileId)));
      setObserved("");setComplete(false);setTiming(false);setReport(null);
    } catch(e){setError(e);} finally{saveLock.current=false;setBusy(false);}
  }
  async function exportReport() {
    setError(null);
    try {
      const data=await exportEvaluationTrials(Number(fileId));setReport(data.analysis);
      const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
      const anchor=document.createElement('a');anchor.href=url;anchor.download=`pilot-${Number(fileId)}.json`;anchor.click();URL.revokeObjectURL(url);
    } catch(e){setError(e);}
  }
  return <section className="panel">
    <h2>실사용 비교 기록</h2>
    <p>같은 과제명을 사용해 수동 방식과 보조 방식을 각각 기록하세요. 시간에는 재검토·수정·Excel 확인을 포함합니다. 기록은 사용자의 관찰값이며 정확도나 시간 절감 성과가 자동 검증되지는 않습니다.</p>
    <p>실제 관찰 기록만 저장하세요. 개발 검증의 가상 시간은 업무 DB에 입력하지 않습니다. 파일럿 상세는 선택 사항이며, 누락한 기록은 시간 비교에서 제외됩니다.</p>
    <button type="button" disabled={!fileId||busy} onClick={exportReport}>관찰 전체 JSON 내보내기·분석</button>
    {report&&<details open><summary>사용자 관찰 분석 (정확도 자동 검증 아님)</summary><pre className="pilot-report">{JSON.stringify(report,null,2)}</pre></details>}
    <form className="form-grid" onSubmit={submit}>
      <label><span>비교 과제명</span><input required maxLength={100} value={task} onChange={e=>setTask(e.target.value)} placeholder="예: 110호 ACST 천장" /></label>
      <label><span>비교 방식</span><select aria-label="비교 방식" value={mode} onChange={e=>setMode(e.target.value)}><option value="manual">수동 기준선</option>{pilotEnabled?["local","ai","vision"].filter(m=>m!==run?.mode).map(m=><option key={m} value={m}>{labels[m]} · 실행 전 실패 기록</option>):null}{run&&<option value={run.mode}>{labels[run.mode]??run.mode} · 현재 실행 #{run.run_id}</option>}</select></label>
      <div className="button-row"><button type="button" disabled={started!==null||!fileId} onClick={()=>{setStarted(Date.now());setElapsed("");}}>과제 시간 시작</button>
        <button type="button" disabled={started===null} onClick={()=>{if(started!==null)setElapsed(String(Math.max(1,Math.round((Date.now()-started)/1000))));setStarted(null);}}>과제 시간 종료</button></div>
      {started!==null&&<p role="status">시간 측정 중입니다. 검수와 Excel 확인까지 마친 뒤 종료하세요.</p>}
      {([['총 소요시간 (초)',elapsed,setElapsed],['수정 횟수',corrections,setCorrections],['수동 개입 횟수',interventions,setInterventions],['확인한 오류 수',errors,setErrors]] as const).map(([label,value,set])=><label key={label}><span>{label}</span><input required type="number" min={label.startsWith('총')?1:0} step="1" value={value} onChange={e=>set(e.target.value)}/></label>)}
      <label><span>최종 검수 결과</span><select aria-label="최종 검수 결과" value={review} onChange={e=>setReview(e.target.value)}><option value="needs_review">추가 검수 필요</option><option value="adopted">실무자가 채택</option><option value="rejected">채택하지 않음</option></select></label>
      <label><span>비교 검수 메모</span><textarea required maxLength={2000} value={notes} onChange={e=>setNotes(e.target.value)} placeholder="공제·면 수 기준, 누락·수정 내용, 검수자, 순서에 따른 학습 영향"/></label>
      <details className="pilot-observation"><summary>파일럿 관찰 상세 (선택)</summary>
        <label className="checkbox-label"><input type="checkbox" checked={pilotEnabled} onChange={e=>setPilotEnabled(e.target.checked)}/>파일럿 메타데이터 기록</label>
        {pilotEnabled&&<div className="form-grid">
          <p>참여자·관찰자·조건은 이 화면에서 유지됩니다. 각 시도마다 실제 순서·관찰 완료·검수 내용을 확인하세요. 실패/중단도 저장합니다.</p>
          {pilotFields.map(([key,label])=><label key={key}><span>{label}</span><textarea required maxLength={1000} value={pilot[key]??''} onChange={e=>editPilot(key,e.target.value)}/></label>)}
          <label><span>실제 관찰 일시 (시간대 포함 ISO)</span><input required value={observed} placeholder="2026-11-09T10:00:00+09:00" onChange={e=>setObserved(e.target.value)}/></label>
          <label><span>과제 분류</span><select value={pilot.category} onChange={e=>editPilot('category',e.target.value)}><option value="floor">바닥</option><option value="ceiling">천장</option><option value="partition">파티션</option><option value="other">기타</option></select></label>
          <label><span>준비 시간</span><select value={pilot.preparation} onChange={e=>editPilot('preparation',e.target.value)}><option value="included">포함</option><option value="excluded">제외 (조건에 별도 소요시간 기록)</option></select></label>
          <label><span>별도 준비 소요시간 (초)</span><input required type="number" min="0" max="86400" value={pilot.preparation_seconds} onChange={e=>editPilot('preparation_seconds',e.target.value)}/></label>
          <label><span>캐시 조건</span><select value={pilot.cache} onChange={e=>editPilot('cache',e.target.value)}><option value="cold">초기</option><option value="warm">준비됨</option></select></label>
          <label><span>실제 실행 순서</span><select value={pilot.sequence} onChange={e=>editPilot('sequence',e.target.value)}>{['manual,local,ai','local,ai,manual','ai,manual,local','manual,local,vision','local,vision,manual','vision,manual,local'].map(order=><option key={order}>{order}</option>)}</select></label>
          <label><span>이번 시도의 순번</span><input required type="number" min="1" max="3" value={pilot.position} onChange={e=>editPilot('position',e.target.value)}/></label>
          <label><span>수행 결과</span><select value={pilot.outcome} onChange={e=>editPilot('outcome',e.target.value)}><option value="completed">완료</option><option value="failed">실패</option><option value="aborted">중단</option></select></label>
          <label><span>잘못된 근거 선택 수</span><input required type="number" min="0" max="10000" value={pilot.wrong_evidence_count} onChange={e=>editPilot('wrong_evidence_count',e.target.value)}/></label>
          <label className="checkbox-label"><input type="checkbox" checked={practice} onChange={e=>setPractice(e.target.checked)}/>연습 시도 (시간 비교 제외)</label>
          <label className="checkbox-label"><input type="checkbox" checked={complete} onChange={e=>setComplete(e.target.checked)}/>관찰 항목 기록 완료</label>
          <label className="checkbox-label"><input type="checkbox" checked={timing} onChange={e=>setTiming(e.target.checked)}/>재검토·수정·Excel 확인 포함 시간</label>
        </div>}
      </details>
      <button disabled={busy||!fileId||started!==null||mode!=="manual"&&(!run||run.mode!==mode)&&!(pilotEnabled&&pilot.outcome!=="completed")}>비교 기록 저장</button>
    </form><ErrorMessage error={error}/>
    {trials.length>0&&<div className="table-wrap"><table><thead><tr><th>과제</th><th>방식</th><th>시간(초)</th><th>수정</th><th>오류</th><th>검수</th></tr></thead><tbody>{trials.map(t=><tr key={t.trial_id}><td>{t.task_key}</td><td>{labels[t.mode]??t.mode}</td><td>{t.elapsed_seconds}</td><td>{t.correction_count}</td><td>{t.error_count}</td><td>{t.review_result}</td></tr>)}</tbody></table></div>}
  </section>;
}
