import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../api/client";
import { ComparisonPanel } from "../components/ComparisonPanel";
vi.mock("../api/client",async original=>({...await original<typeof import("../api/client")>(),getEvaluationTrials:vi.fn(),saveEvaluationTrial:vi.fn(),exportEvaluationTrials:vi.fn()}));
beforeEach(()=>{
  vi.clearAllMocks();
  vi.mocked(api.getEvaluationTrials).mockResolvedValue([]);
  vi.mocked(api.saveEvaluationTrial).mockResolvedValue({trial_id:1} as api.EvaluationTrial);
});
function fillBasic(){
  fireEvent.change(screen.getByLabelText("비교 과제명"),{target:{value:"Synthetic only"}});
  fireEvent.change(screen.getByLabelText("총 소요시간 (초)"),{target:{value:"120"}});
  fireEvent.change(screen.getByLabelText("비교 검수 메모"),{target:{value:"Synthetic DOM fixture, never field data"}});
}
it("keeps legacy entry optional and resets timing when switching drawing",async()=>{
  const view=render(<ComparisonPanel fileId="1" run={null}/>);
  fillBasic();fireEvent.click(screen.getByRole("button",{name:"비교 기록 저장"}));
  await waitFor(()=>expect(api.saveEvaluationTrial).toHaveBeenCalledOnce());
  expect(vi.mocked(api.saveEvaluationTrial).mock.calls[0][1]).not.toHaveProperty("pilot");
  fireEvent.click(screen.getByRole("button",{name:"과제 시간 시작"}));
  view.rerender(<ComparisonPanel fileId="2" run={null}/>);
  expect(screen.queryByText(/시간 측정 중/)).toBeNull();
  expect((screen.getByLabelText("비교 과제명") as HTMLInputElement).value).toBe("");
});
it("records explicit pilot failure before a provider run and keeps setup for the next attempt",async()=>{
  render(<ComparisonPanel fileId="1" run={null}/>);fillBasic();
  fireEvent.click(screen.getByText("파일럿 관찰 상세 (선택)"));
  fireEvent.click(screen.getByLabelText("파일럿 메타데이터 기록"));
  const fields=["비교 묶음 ID","참여자 식별자","관찰자 식별자","동등 과제 정의·공제·면 수 기준","동일 조건: 장치·앱 revision·모델·설정","학습 영향·연습 분리 메모","개입 내용 (없으면 없음)","오류 내용 (없으면 없음)","최종 검수자 (미검수면 미검수)","원본·수량·단위·공제·Excel 검수 근거","채택·거절·실패 이유"];
  for(const label of fields)fireEvent.change(screen.getByLabelText(label),{target:{value:"Synthetic fixture"}});
  fireEvent.change(screen.getByLabelText("실제 관찰 일시 (시간대 포함 ISO)"),{target:{value:"2026-11-09T10:00:00+09:00"}});
  fireEvent.change(screen.getByLabelText("비교 방식"),{target:{value:"ai"}});
  fireEvent.change(screen.getByLabelText("수행 결과"),{target:{value:"failed"}});
  fireEvent.change(screen.getByLabelText("이번 시도의 순번"),{target:{value:"3"}});
  fireEvent.click(screen.getByRole("button",{name:"비교 기록 저장"}));
  await waitFor(()=>expect(api.saveEvaluationTrial).toHaveBeenCalledOnce());
  expect(vi.mocked(api.saveEvaluationTrial).mock.calls[0][1]).toMatchObject({mode:"ai",pilot:{position:3,outcome:"failed",schema_version:1,sequence:["manual","local","ai"]}});
  expect((screen.getByLabelText("참여자 식별자") as HTMLTextAreaElement).value).toBe("Synthetic fixture");
});
it("exports complete observations and shows honest NOT_RUN analysis",async()=>{
  vi.mocked(api.exportEvaluationTrials).mockResolvedValue({schema_version:1,records:[],analysis:{status:"NOT_RUN",record_count:0}});
  vi.stubGlobal("URL",Object.assign(URL,{createObjectURL:vi.fn(()=>"blob:synthetic"),revokeObjectURL:vi.fn()}));
  const click=vi.spyOn(HTMLAnchorElement.prototype,"click").mockImplementation(()=>{});
  render(<ComparisonPanel fileId="1" run={null}/>);
  fireEvent.click(screen.getByRole("button",{name:"관찰 전체 JSON 내보내기·분석"}));
  await screen.findByText(/NOT_RUN/);
  expect(api.exportEvaluationTrials).toHaveBeenCalledWith(1);
  expect(click).toHaveBeenCalledOnce();click.mockRestore();
});
