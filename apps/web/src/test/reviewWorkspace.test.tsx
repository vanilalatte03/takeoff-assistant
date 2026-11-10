import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../api/client";
import { MeasurementsPage } from "../pages/MeasurementsPage";
import { RoomFinishesPage } from "../pages/RoomFinishesPage";
import type { Measurement } from "../types/api";

vi.mock("../api/client", async (original) => ({
  ...await original<typeof import("../api/client")>(),
  listProjects: vi.fn(), listProjectDrawingFiles: vi.fn(), listMeasurements: vi.fn(),
  getDrawingFileRoomStatus: vi.fn(), getReviewEvidence: vi.fn(), listRoomFinishes: vi.fn(),
  generateMeasurements: vi.fn(), mergeMeasurements: vi.fn(), rejectMeasurement: vi.fn(),
}));

const row = (id: number, status: Measurement["status"] = "DRAFT"): Measurement => ({
  id, project_id: 1, room_finish_id: null, room_no: String(100 + id), room_name: "DEMO",
  category: "FLOOR", finish_code: "VCT", measurement_type: "FLOOR_AREA", formula: null,
  quantity: null, unit: "m2", source_sheets: "A101", status, memo: null,
  coordinates_json: null, deductions_json: null, measurement_confidence: null, created_at: "2026-11-10",
});

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  vi.mocked(api.listProjects).mockResolvedValue([{ id: 1, name: "Demo", description: null, created_at: "2026-11-10" }]);
  vi.mocked(api.listProjectDrawingFiles).mockResolvedValue([1, 2].map(id => ({
    id, project_id: 1, original_filename: `demo-${id}.pdf`, stored_path: "demo.pdf", page_count: 1, created_at: "2026-11-10",
  })));
  vi.mocked(api.listMeasurements).mockResolvedValue([row(1), row(2), row(3, "CONFIRMED"), row(4, "REJECTED")]);
  vi.mocked(api.getDrawingFileRoomStatus).mockResolvedValue({ drawing_file_id: 1, rooms: [] });
  vi.mocked(api.getReviewEvidence).mockResolvedValue({
    measurement_id: 1, room_no: "101", finish_code: "VCT", formula: null, quantity: null, unit: "m2",
    status: "DRAFT", inputs: [], sources: [], side_multiplier: null, deductions: [], deductions_reviewed: null, warnings: [],
  });
  vi.mocked(api.listRoomFinishes).mockResolvedValue([]);
});

function openMeasurements() {
  return render(<MemoryRouter initialEntries={["/measurements?drawingFileId=1"]}><MeasurementsPage /></MemoryRouter>);
}

it("loads existing rows without generating candidates and puts the list before its inspector", async () => {
  openMeasurements();
  const select = await screen.findByRole("button", { name: "산출 #2 검토" });
  expect(api.listMeasurements).toHaveBeenCalledWith(1);
  expect(api.generateMeasurements).not.toHaveBeenCalled();
  const list = screen.getByRole("region", { name: "산출 목록" });
  const inspector = screen.getByRole("complementary", { name: "선택한 산출 검토" });
  expect(list.compareDocumentPosition(inspector) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.queryByRole("region", { name: "산출 병합" })).toBeNull();
  inspector.scrollTop = 300;
  fireEvent.click(select);
  expect(within(inspector).getByText("선택한 산출 #2")).toBeTruthy();
  expect(inspector.scrollTop).toBe(0);
  expect(select.getAttribute("aria-pressed")).toBe("true");
  fireEvent.change(screen.getByLabelText("실 번호"), { target: { value: "999" } });
  expect(screen.getByText("조건에 맞는 산출이 없습니다. 필터를 조정하세요.")).toBeTruthy();
});

it("reveals merge controls on selection and keeps confirmed and rejected rows protected", async () => {
  vi.mocked(api.mergeMeasurements).mockResolvedValue(row(1));
  openMeasurements();
  await screen.findByRole("button", { name: "산출 #2 검토" });
  expect((screen.getByLabelText("#3 병합 원본") as HTMLInputElement).disabled).toBe(true);
  expect((screen.getByLabelText("#4 병합 원본") as HTMLInputElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "산출 #3 검토" }));
  expect((screen.getByRole("button", { name: "산출 거절" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByLabelText("#2 병합 원본"));
  const merge = screen.getByRole("region", { name: "산출 병합" });
  fireEvent.click(within(merge).getByRole("button", { name: "선택한 산출 병합" }));
  await waitFor(() => expect(api.mergeMeasurements).toHaveBeenCalledWith({ target_id: 1, source_ids: [2] }));
  await waitFor(() => expect(screen.queryByRole("region", { name: "산출 병합" })).toBeNull());
});

it("discards an old PDF response after a selection change", async () => {
  let resolveOld!: (value: Measurement[]) => void;
  vi.mocked(api.listMeasurements)
    .mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce([row(9)]);
  openMeasurements();
  await screen.findByRole("option", { name: /demo-2.pdf/ });
  await waitFor(() => expect(api.listMeasurements).toHaveBeenCalledWith(1));
  fireEvent.change(screen.getByLabelText("도면 PDF"), { target: { value: "2" } });
  await screen.findByRole("button", { name: "산출 #9 검토" });
  await act(async () => resolveOld([row(8)]));
  expect(screen.queryByRole("button", { name: "산출 #8 검토" })).toBeNull();
  expect(api.generateMeasurements).not.toHaveBeenCalled();
});

it("offers an explicit retry after load failure rather than claiming there are no rows", async () => {
  vi.mocked(api.listMeasurements).mockRejectedValueOnce(new Error("offline"));
  openMeasurements();
  await screen.findByText(/산출 내역을 불러오지 못했습니다/);
  expect(screen.queryByText(/산출 내역이 없습니다/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "다시 불러오기" }));
  await screen.findByRole("button", { name: "산출 #1 검토" });
});

it("loads room finishes automatically while keeping manual creation collapsed", async () => {
  render(<MemoryRouter initialEntries={["/room-finishes?drawingFileId=1"]}><RoomFinishesPage /></MemoryRouter>);
  await waitFor(() => expect(api.listRoomFinishes).toHaveBeenCalledWith(1));
  const summary = screen.getByText("실별 마감 추가");
  const details = summary.closest("details")!;
  expect(details.open).toBe(false);
  fireEvent.click(summary);
  expect(details.open).toBe(true);
  expect(within(details).getByRole("button", { name: "추가" })).toBeTruthy();
});

it("asks for a PDF selection and disables actions until a drawing is selected", async () => {
  render(<MemoryRouter><MeasurementsPage /></MemoryRouter>);
  await screen.findByRole("option", { name: /demo-1.pdf/ });
  expect(api.listMeasurements).not.toHaveBeenCalled();
  expect(screen.getByText("프로젝트와 도면 PDF를 선택하면 산출 내역이 표시됩니다.")).toBeTruthy();
  for (const name of ["다시 불러오기", "산출 후보 생성", "Excel 내보내기"]) {
    expect((screen.getByRole("button", { name }) as HTMLButtonElement).disabled).toBe(true);
  }
});
