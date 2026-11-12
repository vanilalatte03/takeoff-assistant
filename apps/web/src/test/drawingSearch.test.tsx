import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { App } from "../App";
import * as api from "../api/client";
import type { DrawingSheetSearchResponse } from "../types/api";

vi.mock("../api/client", async (original) => ({
  ...await original<typeof import("../api/client")>(),
  listProjects: vi.fn(), listProjectDrawingFiles: vi.fn(), searchDrawingSheets: vi.fn(),
  findRoomPageCandidates: vi.fn(), listMeasurements: vi.fn(),
}));

const sheet = { page_index: 0, sheet_no: "SYN101", sheet_title: "SYNTHETIC PLAN", sheet_role: "FLOOR_PLAN" as const, confidence: 0.9 };
const response: DrawingSheetSearchResponse = { drawing_file_id: 1, results: [sheet] };

beforeEach(() => {
  vi.resetAllMocks(); sessionStorage.clear();
  vi.mocked(api.listProjects).mockResolvedValue([
    { id: 1, name: "First", description: null, created_at: "2026-11-11" },
    { id: 2, name: "Second", description: null, created_at: "2026-11-11" },
  ]);
  vi.mocked(api.listProjectDrawingFiles).mockImplementation(async id => [{
    id, project_id: id, original_filename: `synthetic-${id}.pdf`, stored_path: "demo.pdf", page_count: 3, created_at: "2026-11-11",
  }]);
  vi.mocked(api.searchDrawingSheets).mockImplementation(async (id, filters) => Object.keys(filters).length ? response : { drawing_file_id: id, results: [sheet, { ...sheet, page_index: 1, sheet_no: "SYN102" }] });
  vi.mocked(api.listMeasurements).mockResolvedValue([]);
  vi.mocked(api.findRoomPageCandidates).mockResolvedValue({ drawing_file_id: 1, room_query: "101", warnings: [],
    candidates: [{ ...sheet, room_no: "101", room_name: "DEMO", evidence: ["synthetic evidence"] }],
  });
});

function History() {
  const location = useLocation(); const navigate = useNavigate();
  return <><output aria-label="URL">{location.pathname}{location.search}</output>
    <button onClick={() => navigate(-1)}>브라우저 뒤로</button>
    <button onClick={() => navigate(1)}>브라우저 앞으로</button></>;
}

function open(path = "/drawings?drawingFileId=1") {
  return render(<MemoryRouter initialEntries={[path]}><App /><History /></MemoryRouter>);
}

it("restores applied filters and results through detail, page changes, and the list link", async () => {
  open(); await screen.findByRole("link", { name: "열기" });
  fireEvent.change(screen.getByLabelText("Sheet No"), { target: { value: " SYN101 " } });
  fireEvent.change(screen.getByLabelText("Keyword"), { target: { value: "DEMO & office" } });
  fireEvent.change(screen.getByLabelText("역할"), { target: { value: "FLOOR_PLAN" } });
  fireEvent.click(screen.getByRole("button", { name: "검색" }));
  await waitFor(() => expect(api.searchDrawingSheets).toHaveBeenLastCalledWith(1, {sheetNo:"SYN101", keyword:"DEMO & office", sheetRole:"FLOOR_PLAN"}));
  fireEvent.click(await screen.findByRole("link", { name: "열기" }));
  await waitFor(() => expect((screen.getByRole("button", { name: "이동" }) as HTMLButtonElement).disabled).toBe(false));
  fireEvent.change(screen.getByLabelText("PDF 쪽 번호"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "이동" }));
  expect(screen.getByLabelText("URL").textContent).toContain("/pages/1?");
  fireEvent.click(screen.getByRole("link", { name: "목록으로" }));
  await screen.findByRole("link", { name: "열기" });
  expect((screen.getByLabelText("Sheet No") as HTMLInputElement).value).toBe("SYN101");
  expect((screen.getByLabelText("Keyword") as HTMLInputElement).value).toBe("DEMO & office");
  expect((screen.getByLabelText("역할") as HTMLSelectElement).value).toBe("FLOOR_PLAN");
  expect(api.searchDrawingSheets).toHaveBeenLastCalledWith(1, {sheetNo:"SYN101", keyword:"DEMO & office", sheetRole:"FLOOR_PLAN"});
});

it("applies bookmarked queries and browser back/forward to both the form and results", async () => {
  open("/drawings?drawingFileId=1&keyword=first");
  await screen.findByRole("link", { name: "열기" });
  fireEvent.change(screen.getByLabelText("Keyword"), { target: { value: "second" } });
  fireEvent.click(screen.getByRole("button", { name: "검색" }));
  await waitFor(() => expect(api.searchDrawingSheets).toHaveBeenLastCalledWith(1, expect.objectContaining({ keyword: "second" })));
  fireEvent.click(screen.getByRole("button", { name: "브라우저 뒤로" }));
  await waitFor(() => expect(api.searchDrawingSheets).toHaveBeenLastCalledWith(1, expect.objectContaining({ keyword: "first" })));
  expect((screen.getByLabelText("Keyword") as HTMLInputElement).value).toBe("first");
  fireEvent.click(screen.getByRole("button", { name: "브라우저 앞으로" }));
  await waitFor(() => expect(api.searchDrawingSheets).toHaveBeenLastCalledWith(1, expect.objectContaining({ keyword: "second" })));
});

it("restores room search candidates and warnings after opening a candidate", async () => {
  open("/drawings?drawingFileId=1&roomQuery=101&keyword=demo");
  fireEvent.click(await screen.findByRole("link", { name: "Open" }));
  fireEvent.click(screen.getByRole("link", { name: "목록으로" }));
  await screen.findByRole("link", { name: "Open" });
  expect((screen.getByLabelText("Room No / Name") as HTMLInputElement).value).toBe("101");
  expect(api.findRoomPageCandidates).toHaveBeenLastCalledWith(1, "101");
  expect((screen.getByLabelText("Keyword") as HTMLInputElement).value).toBe("demo");
});

it("clears search context when switching project and PDF, including stored selection", async () => {
  open("/drawings?drawingFileId=1&keyword=old&roomQuery=101");
  await screen.findByRole("option", { name: /synthetic-1.pdf/ });
  fireEvent.change(screen.getByLabelText("프로젝트"), { target: { value: "2" } });
  expect((screen.getByLabelText("도면 PDF") as HTMLSelectElement).value).toBe("");
  expect(sessionStorage.getItem("takeoff.drawingFileId")).toBe("");
  expect((screen.getByLabelText("Keyword") as HTMLInputElement).value).toBe("");
  fireEvent.change(screen.getByLabelText("도면 PDF"), { target: { value: "2" } });
  await waitFor(() => expect(api.searchDrawingSheets).toHaveBeenLastCalledWith(2, { sheetNo:"", keyword:"", sheetRole:"" }));
  expect(screen.getByLabelText("URL").textContent).toBe("/drawings?drawingFileId=2");
});

it("ignores delayed results from an older query", async () => {
  let finishOld!: (value: DrawingSheetSearchResponse) => void;
  vi.mocked(api.searchDrawingSheets).mockResolvedValueOnce(response)
    .mockReturnValueOnce(new Promise(resolve => { finishOld = resolve; }))
    .mockResolvedValueOnce({ drawing_file_id: 1, results: [{ ...sheet, sheet_no: "CURRENT" }] });
  open(); await screen.findByRole("link", { name: "열기" });
  fireEvent.change(screen.getByLabelText("Keyword"), { target: { value: "old" } });
  fireEvent.click(screen.getByRole("button", { name: "검색" }));
  // A URL/history change may supersede an in-flight search even while submit is disabled.
  fireEvent.click(screen.getByRole("button", { name: "브라우저 뒤로" }));
  await screen.findByText("CURRENT");
  await act(async () => finishOld({ drawing_file_id: 1, results: [{ ...sheet, sheet_no: "STALE" }] }));
  expect(screen.queryByText("STALE")).toBeNull();
});

it("retries a failed query without changing its URL and distinguishes failure from empty results", async () => {
  vi.mocked(api.searchDrawingSheets).mockRejectedValueOnce(new Error("offline"));
  open("/drawings?drawingFileId=1&keyword=demo");
  await screen.findByText(/도면 목록을 불러오지 못했습니다/);
  expect(screen.queryByText("검색 결과가 없습니다.")).toBeNull();
  const url = screen.getByLabelText("URL").textContent;
  fireEvent.click(screen.getByRole("button", { name: "검색" }));
  await screen.findByRole("link", { name: "열기" });
  expect(screen.getByLabelText("URL").textContent).toBe(url);
});

it("uses the detail route's PDF for return links and drops unrelated or invalid parameters", async () => {
  open("/drawings/1/pages/0?drawingFileId=2&keyword=demo&sheetRole=INVALID&returnTo=https://example.com");
  const href = screen.getByRole("link", { name: "목록으로" }).getAttribute("href");
  expect(href).toBe("/drawings?drawingFileId=1&keyword=demo");
});

it.each(["/drawings?keyword=demo&drawingFileId=1", "/drawings?drawingFileId=1&extra=unused", "/drawings"])(
  "retries on the first click even when the query must be normalized: %s", async path => {
    sessionStorage.setItem("takeoff.drawingFileId", "1");
    vi.mocked(api.searchDrawingSheets).mockRejectedValueOnce(new Error("offline"));
    open(path);
    await screen.findByText(/도면 목록을 불러오지 못했습니다/);
    fireEvent.click(screen.getByRole("button", { name: "검색" }));
    await screen.findByRole("link", { name: "열기" });
    expect(api.searchDrawingSheets).toHaveBeenCalledTimes(2);
  },
);

it("retries a failed room query on the first click with reordered URL parameters", async () => {
  vi.mocked(api.findRoomPageCandidates).mockRejectedValueOnce(new Error("room offline"));
  open("/drawings?roomQuery=101&drawingFileId=1");
  await screen.findByText(/room offline/);
  fireEvent.click(screen.getByRole("button", { name: "Find room" }));
  await screen.findByRole("link", { name: "Open" });
  expect(api.findRoomPageCandidates).toHaveBeenCalledTimes(2);
});
