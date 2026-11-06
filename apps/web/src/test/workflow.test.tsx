import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { StrictMode } from "react";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../api/client";
import { WorkflowContent } from "../pages/WorkflowPage";
import { UploadPage } from "../pages/UploadPage";
import type { Measurement } from "../types/api";

vi.mock("../api/client", async original => ({...await original<typeof import("../api/client")>(),
  getWorkflowStatus: vi.fn(), prepareWorkflowStage: vi.fn(), listMeasurements: vi.fn(), searchAssist: vi.fn(),
  downloadMeasurementsExcel: vi.fn(), getReviewEvidence: vi.fn(),
  listProjects: vi.fn(), createProject: vi.fn(),
}));
vi.mock("../components/AssistDraftForm", () => ({AssistDraftForm: ({onSaved}: {onSaved: (r:Measurement)=>void}) => <button onClick={() => onSaved(row)}>합성 저장</button>}));
const row = {id:7,room_no:"110",category:"CEILING",finish_code:"ACST",measurement_type:"CEILING_AREA",formula:"4.2 * 2.7",quantity:"11.34",unit:"m2",status:"DRAFT"} as Measurement;
const state = (completed=0) => ({completed,stages:["페이지 처리","도면 감지","도면 분류","마감 후보 추출","산출 후보 생성"],warnings:[],ready:completed===5,finish_count:2,measurement_count:10});
const result = {run_id:1,status:"NEEDS_REVIEW",warnings:[],evidence:[],trace:[],dimensions:[],finishes:[],mode:"local",elapsed_ms:1};
function deferred<T>() { let resolve!: (v:T)=>void; const promise = new Promise<T>(r => {resolve=r;}); return {promise,resolve}; }
function view(fileId="42") { return <MemoryRouter><WorkflowContent key={fileId} fileId={fileId}/></MemoryRouter>; }
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getWorkflowStatus).mockResolvedValue(state());
  vi.mocked(api.listMeasurements).mockResolvedValue([]);
  vi.mocked(api.searchAssist).mockResolvedValue(result);
  vi.mocked(api.getReviewEvidence).mockResolvedValue({measurement_id:7,room_no:"110",finish_code:"ACST",formula:row.formula,quantity:"11.34",unit:row.unit,status:"DRAFT",inputs:[],sources:[],side_multiplier:null,deductions:[],deductions_reviewed:true,warnings:[]});
  vi.stubGlobal("URL", Object.assign(URL, {createObjectURL:vi.fn(()=>"blob:synthetic"),revokeObjectURL:vi.fn()}));
});

it("prepares in order, searches locally, carries the saved draft into review and downloads once", async () => {
  let completed=0;
  vi.mocked(api.prepareWorkflowStage).mockImplementation(async () => state(++completed));
  vi.mocked(api.listMeasurements).mockResolvedValue([{...row,quantity:null}]);
  const download = deferred<{blob:Blob;filename:string}>();
  vi.mocked(api.downloadMeasurementsExcel).mockReturnValue(download.promise);
  render(view());
  await waitFor(()=>expect(screen.getByRole("button",{name:"도면 준비 시작·이어서 진행"})).toHaveProperty("disabled", false));
  fireEvent.click(screen.getByRole("button",{name:"도면 준비 시작·이어서 진행"}));
  await waitFor(()=>expect(api.prepareWorkflowStage).toHaveBeenCalledTimes(5));
  await waitFor(()=>expect(screen.getByRole("button",{name:"근거 찾기·다시 찾기"})).toHaveProperty("disabled", true));
  fireEvent.change(screen.getByLabelText("찾을 산출 항목"),{target:{value:"110호 ACST 천장"}});
  fireEvent.click(screen.getByRole("button",{name:"근거 찾기·다시 찾기"}));
  fireEvent.click(await screen.findByRole("button",{name:"합성 저장"}));
  expect(api.searchAssist).toHaveBeenCalledWith(42,"110호 ACST 천장","local");
  await screen.findAllByText(/현재 저장값/);
  fireEvent.click(screen.getByRole("checkbox",{name:/선택한 행의 원본/}));
  fireEvent.click(screen.getByRole("button",{name:"Excel 다운로드"}));
  fireEvent.click(screen.getByRole("button",{name:"Excel 다운로드"}));
  expect(api.downloadMeasurementsExcel).toHaveBeenCalledTimes(1);
  const anchor = vi.spyOn(HTMLAnchorElement.prototype,"click").mockImplementation(()=>{});
  download.resolve({blob:new Blob(["synthetic"]),filename:"synthetic.xlsx"});
  await screen.findByText(/Excel 다운로드 완료/);
  expect(anchor).toHaveBeenCalledOnce();
  anchor.mockRestore();
});

it("keeps completed stages after failure and retries only the remaining stage", async () => {
  vi.mocked(api.getWorkflowStatus).mockResolvedValue(state(3));
  vi.mocked(api.prepareWorkflowStage).mockRejectedValueOnce(new Error("합성 추출 오류"));
  render(view());
  fireEvent.click(await screen.findByRole("button",{name:"도면 준비 시작·이어서 진행"}));
  await screen.findByRole("alert");
  expect(screen.getByText("도면 분류 · 완료")).toBeTruthy();
  vi.mocked(api.prepareWorkflowStage).mockResolvedValueOnce(state(4)).mockResolvedValueOnce(state(5));
  fireEvent.click(screen.getByRole("button",{name:"실패 단계부터 준비 재시도"}));
  await waitFor(()=>expect(api.prepareWorkflowStage).toHaveBeenCalledTimes(3));
});

it("resumes saved rows without preparation or search, and blocks duplicate prepare clicks", async () => {
  vi.mocked(api.getWorkflowStatus).mockResolvedValue(state(5));
  vi.mocked(api.listMeasurements).mockResolvedValue([row]);
  const rendered=render(view());
  await screen.findAllByText(/현재 저장값/);
  expect(api.prepareWorkflowStage).not.toHaveBeenCalled();
  expect(api.searchAssist).not.toHaveBeenCalled();
  rendered.unmount();
  vi.mocked(api.getWorkflowStatus).mockResolvedValue(state());
  const next=deferred<api.WorkflowStatus>();
  vi.mocked(api.prepareWorkflowStage).mockReturnValue(next.promise);
  render(view());
  await waitFor(()=>expect(screen.getByRole("button",{name:"도면 준비 시작·이어서 진행"})).toHaveProperty("disabled", false));
  fireEvent.click(screen.getByRole("button",{name:"도면 준비 시작·이어서 진행"}));
  fireEvent.click(screen.getByRole("button",{name:"도면 준비 시작·이어서 진행"}));
  await waitFor(()=>expect(api.prepareWorkflowStage).toHaveBeenCalledOnce());
  next.resolve(state(5));
});

it("discards old search and stops the remaining preparation when switching PDFs", async () => {
  const old=deferred<api.AssistResult>();
  vi.mocked(api.getWorkflowStatus).mockResolvedValue(state(5));
  vi.mocked(api.listMeasurements).mockImplementation(async id => id===42 ? [row] : []);
  vi.mocked(api.searchAssist).mockReturnValue(old.promise);
  const rendered=render(view());
  await screen.findAllByText(/현재 저장값/);
  fireEvent.change(screen.getByLabelText("찾을 산출 항목"),{target:{value:"old request"}});
  fireEvent.click(screen.getByRole("button",{name:"근거 찾기·다시 찾기"}));
  rendered.rerender(view("84"));
  old.resolve({...result,warnings:["OLD RESULT MUST NOT APPEAR"]});
  await waitFor(()=>expect(api.listMeasurements).toHaveBeenCalledWith(84));
  expect(screen.queryByText("OLD RESULT MUST NOT APPEAR")).toBeNull();
  expect(screen.queryAllByText(/현재 저장값/)).toHaveLength(0);
  const pending=deferred<api.WorkflowStatus>();
  vi.mocked(api.getWorkflowStatus).mockResolvedValue(state());
  vi.mocked(api.prepareWorkflowStage).mockReturnValue(pending.promise);
  rendered.rerender(view("12"));
  await waitFor(()=>expect(screen.getByRole("button",{name:"도면 준비 시작·이어서 진행"})).toHaveProperty("disabled", false));
  fireEvent.click(screen.getByRole("button",{name:"도면 준비 시작·이어서 진행"}));
  await waitFor(()=>expect(api.prepareWorkflowStage).toHaveBeenCalledOnce());
  rendered.rerender(view("13"));
  pending.resolve(state(1));
  await waitFor(()=>expect(api.listMeasurements).toHaveBeenCalledWith(13));
  expect(api.prepareWorkflowStage).toHaveBeenCalledTimes(1);
});

it("ignores the older StrictMode initialization response after the newer saved state", async () => {
  const oldStatus=deferred<api.WorkflowStatus>();
  const oldRows=deferred<Measurement[]>();
  vi.mocked(api.getWorkflowStatus).mockReturnValueOnce(oldStatus.promise).mockResolvedValue(state(5));
  vi.mocked(api.listMeasurements).mockReturnValueOnce(oldRows.promise).mockResolvedValue([row]);
  render(<StrictMode>{view()}</StrictMode>);
  await screen.findAllByText(/현재 저장값/);
  oldStatus.resolve(state()); oldRows.resolve([]);
  await waitFor(()=>expect(api.getWorkflowStatus).toHaveBeenCalledTimes(2));
  expect(screen.getByText("산출 후보 생성 · 완료")).toBeTruthy();
  expect(screen.getAllByText(/현재 저장값/).length).toBeGreaterThan(0);
});

it.each([false, true])("preserves a created project when initial project lists arrive late (StrictMode=%s)", async strict => {
  const initial=deferred<Awaited<ReturnType<typeof api.listProjects>>>();
  vi.mocked(api.listProjects).mockReturnValue(initial.promise);
  vi.mocked(api.createProject).mockResolvedValue({id:9,name:"새 합성 프로젝트",description:null});
  const upload=<MemoryRouter><UploadPage/></MemoryRouter>;
  render(strict ? <StrictMode>{upload}</StrictMode> : upload);
  fireEvent.change(screen.getByLabelText("새 프로젝트 이름"), {target:{value:"새 합성 프로젝트"}});
  fireEvent.click(screen.getByRole("button", {name:"프로젝트 만들기"}));
  await screen.findByRole("option", {name:"새 합성 프로젝트"});
  await act(async () => initial.resolve([]));
  expect((screen.getByLabelText("프로젝트") as HTMLSelectElement).value).toBe("9");
  expect(screen.getByRole("option", {name:"새 합성 프로젝트"})).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});
