import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createAssistDraft, listMeasurements } from "../api/client";
import type { AssistResult } from "../api/client";
import type { Measurement } from "../types/api";
import { ErrorMessage } from "./ApiState";
import { ReviewEvidencePanel } from "./ReviewEvidencePanel";

const fields: Record<string, Array<[string, string]>> = {
  FLOOR_AREA: [["width", "가로"], ["height", "세로"]],
  CEILING_AREA: [["width", "가로"], ["height", "세로"]],
  PERIMETER_LENGTH: [["width", "가로"], ["height", "세로"]],
  WALL_AREA: [["wall_length", "벽 길이"], ["wall_height", "벽 높이"]],
  PARTITION_AREA: [["wall_length", "벽 길이"], ["wall_height", "벽 높이"]],
  COUNT: [["count", "개수"]],
};
type Entry = { candidate: string; value: string; unit: string; sheet: string; note: string };
const blank = (): Entry => ({ candidate: "", value: "", unit: "", sheet: "", note: "" });
type Deduction = { amount: string; unit: string; sheet: string; note: string };

export function AssistDraftForm({ fileId, result }: { fileId: string; result: AssistResult }) {
  const [rows, setRows] = useState<Measurement[]>([]);
  const [selected, setSelected] = useState("");
  const [code, setCode] = useState("");
  const [inputs, setInputs] = useState<Record<string, Entry>>({});
  const [sides, setSides] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [deductions, setDeductions] = useState<Deduction[]>([]);
  const [saved, setSaved] = useState<Measurement | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const row = rows.find(r => String(r.id) === selected);
  const room = result.trace.find(t => t.tool === "search_sheets")?.arguments?.room_no;
  useEffect(() => {
    let active = true;
    listMeasurements(Number(fileId)).then(r => { if (active) setRows(r); }).catch(e => { if(active) setError(e); });
    return () => { active = false; };
  }, [fileId]);
  function setInput(name: string, change: Partial<Entry>) {
    setInputs(old => ({ ...old, [name]: { ...blank(), ...old[name], ...change } }));
    setReviewed(false); setSaved(null);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!row) return;
    setBusy(true); setError(null); setSaved(null);
    try {
      const evidence = Object.fromEntries((fields[row.measurement_type] ?? []).map(([name]) => {
        const v = inputs[name] ?? blank();
        return [name, { candidate_id: v.candidate || null, value: v.candidate ? null : v.value,
          unit: v.unit, unit_confirmed: reviewed, sheet_id: Number(v.sheet), note: v.note }];
      }));
      const draft = await createAssistDraft(Number(fileId), { run_id: result.run_id, measurement_id: row.id,
        finish_code: code, inputs: evidence, side_multiplier: row.measurement_type === "PARTITION_AREA" ? Number(sides) : null,
        deductions_reviewed: reviewed, deductions: deductions.map(d => ({amount:d.amount,unit:d.unit,sheet_id:Number(d.sheet),note:d.note})) });
      setSaved(draft);
    } catch(e) { setError(e); }
    finally { setBusy(false); }
  }
  function sourceOptions() { return <><option value="">출처를 선택하세요</option>{result.evidence.map(e => <option key={e.sheet_id} value={e.sheet_id}>{e.sheet_no ?? "번호 미확인"} · PDF {e.page_index + 1}쪽</option>)}</>; }
  return <section className="panel">
    <h2>근거 확인 후 계산 초안</h2>
    <p>숫자 후보는 실 번호나 다른 치수일 수 있습니다. 원본 페이지에서 해당 실에 적용되는 치수·단위·공제를 확인하세요.</p>
    {!rows.length && <p><Link to={`/measurements?drawingFileId=${fileId}`}>산출 목록에서 후보를 먼저 생성하세요.</Link></p>}
    <form onSubmit={submit} className="form-grid">
      <label><span>산출 행</span><select value={selected} onChange={e => {
        setSelected(e.target.value); setCode(rows.find(r => String(r.id) === e.target.value)?.finish_code ?? "");
        setInputs({}); setSides(""); setDeductions([]); setReviewed(false); setSaved(null);
      }}><option value="">검토할 산출 행을 선택하세요</option>
        {rows.filter(r => !room || r.room_no === room).map(r => <option key={r.id} value={r.id} disabled={r.status === "CONFIRMED" || r.status === "REJECTED"}>{r.room_no} · {r.measurement_type} · {r.finish_code} · {r.status}</option>)}
      </select></label>
      {row && <>
        <label><span>확인한 마감 코드</span><input required maxLength={128} value={code} onChange={e => {setCode(e.target.value);setReviewed(false);}} /></label>
        {(fields[row.measurement_type] ?? []).map(([name, label]) => {
          const v = inputs[name] ?? blank();
          return <fieldset key={name}><legend>{label}</legend>
            <label><span>{label} 출처</span><select required value={v.sheet} onChange={e => setInput(name,{sheet:e.target.value,candidate:""})}>{sourceOptions()}</select></label>
            {!v.sheet && <p>치수 후보를 보려면 출처 페이지를 먼저 선택하세요.</p>}
            <label><span>{label} 후보</span><select disabled={!v.sheet} value={v.candidate} onChange={e => {
              const c = result.dimensions.find(c => c.candidate_id === e.target.value);
              setInput(name, {candidate:e.target.value, value:"", sheet:c ? String(c.sheet_id) : v.sheet, unit:""});
            }}><option value="">수동 측정값 입력</option>{result.dimensions.filter(c=>String(c.sheet_id)===v.sheet).map(c => <option key={c.candidate_id} value={c.candidate_id}>{c.raw_text} · PDF {c.page_index + 1}쪽 · 단위 추정 {c.unit_guess ?? "없음"}</option>)}</select></label>
            {!v.candidate && <label><span>{label} 수동값</span><input required type="number" step="any" min={name === "count" ? "0" : "0.000001"} value={v.value} onChange={e => setInput(name,{value:e.target.value})} /></label>}
            <label><span>{label} 확인 단위</span><select required value={v.unit} onChange={e => setInput(name,{unit:e.target.value})}><option value="">원본에서 단위 확인 필요</option>{(name === "count" ? ["EA"] : v.candidate ? ["m","mm","ft-in"] : ["m","mm"]).map(u => <option key={u}>{u}</option>)}</select></label>
            <label><span>{label} 확인 메모</span><input required maxLength={500} value={v.note} placeholder="적용 구간·원문 치수 또는 수동 측정 근거" onChange={e => setInput(name,{note:e.target.value})} /></label>
          </fieldset>;
        })}
        {row.measurement_type === "PARTITION_AREA" && <label><span>확인한 산출 면 수</span><input required min="1" max="10" type="number" value={sides} onChange={e => {setSides(e.target.value);setReviewed(false);}} /></label>}
        {deductions.map((d,index) => <fieldset key={index}><legend>공제 {index+1}</legend>
          {([['amount','공제 수량'],['note','공제 근거']] as const).map(([key,label]) => <label key={key}><span>{label} {index+1}</span><input required value={d[key]} onChange={e => {setDeductions(old=>old.map((v,i)=>i===index?{...v,[key]:e.target.value}:v));setReviewed(false);}} /></label>)}
          <label><span>공제 단위 {index+1}</span><select required value={d.unit} onChange={e=>{setDeductions(old=>old.map((v,i)=>i===index?{...v,unit:e.target.value}:v));setReviewed(false);}}><option value="">단위 선택</option>{['m2','m','EA'].map(u=><option key={u}>{u}</option>)}</select></label>
          <label><span>공제 출처 {index+1}</span><select required value={d.sheet} onChange={e=>{setDeductions(old=>old.map((v,i)=>i===index?{...v,sheet:e.target.value}:v));setReviewed(false);}}>{sourceOptions()}</select></label>
          <button type="button" onClick={()=>{setDeductions(old=>old.filter((_,i)=>i!==index));setReviewed(false);}}>공제 삭제</button>
        </fieldset>)}
        {row.measurement_type !== "COUNT" && <button type="button" disabled={deductions.length>=50} onClick={()=>{setDeductions(old=>[...old,{amount:"",unit:"",sheet:"",note:""}]);setReviewed(false);}}>공제 추가</button>}
        <label className="checkbox-label"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)} /><span>치수·단위·출처·마감 코드·면 수·공제 여부를 원본과 대조했습니다</span></label>
        <button disabled={busy || !reviewed}>{busy ? "계산 중…" : "계산하고 미확정 초안 저장"}</button>
      </>}
    </form>
    <ErrorMessage error={error}/>
    {saved && <p role="status">{saved.formula} = {saved.quantity} {saved.unit} · DRAFT (미확정). <Link to={`/measurements?drawingFileId=${fileId}`}>산출 목록에서 수정·최종 검수</Link></p>}
    {saved&&<ReviewEvidencePanel measurement={saved}/>}
  </section>;
}
