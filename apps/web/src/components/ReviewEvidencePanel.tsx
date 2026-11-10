import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getReviewEvidence, pageImageUrl } from "../api/client";
import type { ReviewEvidence } from "../api/client";
import type { Measurement } from "../types/api";
import { ErrorMessage } from "./ApiState";

const names:Record<string,string>={width:"가로",height:"세로",wall_length:"벽 길이",wall_height:"벽 높이",count:"개수"};

export function ReviewEvidencePanel({measurement, defaultOpen = true}:{measurement:Measurement; defaultOpen?:boolean}) {
  const [data,setData]=useState<ReviewEvidence|null>(null);
  const [selected,setSelected]=useState<number|null>(null);
  const [error,setError]=useState<unknown>(null);
  const [imageError,setImageError]=useState(false);
  useEffect(()=>{
    let active=true;setData(null);setError(null);
    getReviewEvidence(measurement.id).then(value=>{if(active){setData(value);setSelected(value.sources[0]?.sheet_id??null);}}).catch(e=>{if(active)setError(e);});
    return ()=>{active=false;};
  },[measurement.id,measurement.formula,measurement.quantity,measurement.unit,measurement.status,measurement.finish_code,measurement.source_sheets,measurement.coordinates_json,measurement.deductions_json]);
  useEffect(()=>{setImageError(false);},[selected]);
  const source=data?.sources.find(s=>s.sheet_id===selected);
  return <details className="evidence-review" open={defaultOpen}>
    <summary>저장된 산출과 원본 대조</summary>
    <ErrorMessage error={error}/>
    {!data&&!error&&<p>저장 근거를 불러오는 중…</p>}
    {data&&<>
      <p>현재 저장값: <strong>{data.formula??"계산식 없음"} = {data.quantity??"미계산"} {data.unit??""}</strong> · {data.status}</p>
      <p>이 화면은 저장된 근거를 보여줍니다. 원본 이미지와 대조해도 저장값이나 확정 상태가 자동으로 바뀌지는 않습니다.</p>
      {data.warnings.map(w=><p key={w} className="message message-warning">{w}</p>)}
      <div className="evidence-review-grid">
        <div>
          {data.inputs.map(i=><article className="evidence-input" key={i.name}>
              <h4>{names[i.name]??i.name}</h4>
              <p>원문·수동값: {i.raw_value??"기록 없음"} · 확인 단위: {i.unit??"미확인"}</p>
              <p>계산 입력: <strong>{i.normalized_value===null?"이전 기록 없음":`${i.normalized_value} ${i.normalized_unit}`}</strong></p>
              {i.source_sheet_id!==null&&<button type="button" className="button-secondary" onClick={()=>setSelected(i.source_sheet_id)}>{names[i.name]??i.name} 출처 보기</button>}
              <p>{i.note??"메모 없음"}</p>
            </article>)}
          <p>산출 면 수: {data.side_multiplier??"적용 없음 또는 기록 없음"}</p>
          <p>공제: {data.deductions.length?`${data.deductions.length}건`:data.deductions_reviewed?"없음 (사용자 확인)":"확인 기록 없음"}</p>
          {data.deductions.map((d,i)=><p key={i}>{d.amount} {d.unit} · {d.note}</p>)}
        </div>
        <div>
          <label><span>대조할 원본 페이지</span><select aria-label="대조할 원본 페이지" value={selected??""} onChange={e=>setSelected(Number(e.target.value))}>
            {!data.sources.length&&<option value="">연결된 출처 없음</option>}
            {data.sources.map(s=><option key={s.sheet_id} value={s.sheet_id}>{s.sheet_no??"번호 미확인"} · PDF {s.page_index+1}쪽 · {s.sheet_title??"제목 미확인"}</option>)}
          </select></label>
          {source&&<>
            <Link to={`/drawings/${source.drawing_file_id}/pages/${source.page_index}`}>원본을 크게 열고 측정하기</Link>
            {source.changed_since_saved&&<p className="message message-warning">저장 후 변경된 원본입니다.</p>}
            {imageError?<p>원본 이미지를 불러오지 못했습니다. 페이지 처리 상태를 확인하세요.</p>:<img className="evidence-review-image" src={pageImageUrl(source.drawing_file_id,source.page_index)} alt={`산출 근거 원본 PDF ${source.page_index+1}쪽`} onError={()=>setImageError(true)}/>}
            {source.quote&&<pre style={{whiteSpace:"pre-wrap"}}>{source.quote}</pre>}
          </>}
        </div>
      </div>
    </>}
  </details>;
}
