import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import * as api from "../api/client";
import { DrawingDetailPage } from "../pages/DrawingDetailPage";
import type { DrawingSheetSearchResponse } from "../types/api";

vi.mock("../api/client", async original => ({
  ...await original<typeof import("../api/client")>(), searchDrawingSheets: vi.fn(), listMeasurements: vi.fn(),
}));

const index = (pages: number[], fileId = 1): DrawingSheetSearchResponse => ({ drawing_file_id: fileId,
  results: pages.map(page_index => ({ page_index, sheet_no: `SYN${fileId}-${page_index}`, sheet_title: `SYNTHETIC ${fileId}-${page_index}`, sheet_role: "FLOOR_PLAN", confidence: 0.9 })),
});

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.listMeasurements).mockResolvedValue([]);
  vi.mocked(api.searchDrawingSheets).mockResolvedValue(index([0, 1, 2]));
});

function History() {
  const location = useLocation(); const navigate = useNavigate();
  return <><output aria-label="현재 주소">{location.pathname}{location.search}</output>
    <button onClick={() => navigate(-1)}>뒤로</button>
    <button onClick={() => navigate("/drawings/2/pages/0")}>다른 PDF</button></>;
}
function open(pageIndex = 0, query = "") {
  return render(<MemoryRouter initialEntries={[`/drawings/1/pages/${pageIndex}${query}`]}>
    <Routes><Route path="/drawings/:drawingFileId/pages/:pageIndex" element={<DrawingDetailPage />} /></Routes><History />
  </MemoryRouter>);
}
const button = (name: string) => screen.getByRole("button", { name }) as HTMLButtonElement;
async function ready() { await waitFor(() => expect(button("이동").disabled).toBe(false)); }

it("moves between processed pages, preserves search context, and disables the boundaries", async () => {
  open(0, "?keyword=demo&sheetRole=FLOOR_PLAN"); await ready();
  expect(button("이전 쪽").disabled).toBe(true);
  fireEvent.click(button("다음 쪽"));
  expect(screen.getByLabelText("현재 주소").textContent).toBe("/drawings/1/pages/1?drawingFileId=1&keyword=demo&sheetRole=FLOOR_PLAN");
  expect((screen.getByLabelText("PDF 쪽 번호") as HTMLInputElement).value).toBe("2");
  expect(screen.getByRole("heading", { level: 1 }).textContent).toContain("SYN1-1");
  fireEvent.click(button("다음 쪽"));
  expect(button("다음 쪽").disabled).toBe(true);
  fireEvent.click(button("이전 쪽"));
  expect(screen.getByLabelText("현재 주소").textContent).toContain("/pages/1?");
  fireEvent.click(button("뒤로"));
  expect((screen.getByLabelText("PDF 쪽 번호") as HTMLInputElement).value).toBe("3");
  expect(screen.getByRole("link", { name: "목록으로" }).getAttribute("href")).toContain("keyword=demo");
  expect(api.searchDrawingSheets).toHaveBeenCalledTimes(1);
});

it("uses actual page indices rather than row order and rejects missing or out-of-range jumps", async () => {
  vi.mocked(api.searchDrawingSheets).mockResolvedValue(index([4, 0, 2, 2]));
  open(); await ready();
  fireEvent.click(button("다음 쪽"));
  expect((screen.getByLabelText("PDF 쪽 번호") as HTMLInputElement).value).toBe("3");
  const input = screen.getByLabelText("PDF 쪽 번호");
  for (const value of ["2", "99", "0", "1.5", ""]) {
    fireEvent.change(input, { target: { value } });
    fireEvent.submit(button("이동").closest("form")!);
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByLabelText("현재 주소").textContent).toBe("/drawings/1/pages/2");
  }
  fireEvent.change(input, { target: { value: "5" } }); fireEvent.click(button("이동"));
  expect(screen.queryByRole("alert")).toBeNull();
  expect(button("다음 쪽").disabled).toBe(true);
});

it("keeps movement disabled while loading and retries failed metadata reads", async () => {
  let reject!: (reason: Error) => void;
  vi.mocked(api.searchDrawingSheets).mockReturnValueOnce(new Promise((_resolve, failed) => { reject = failed; }));
  open();
  for (const name of ["이전 쪽", "다음 쪽", "이동"]) expect(button(name).disabled).toBe(true);
  await act(async () => reject(new Error("metadata offline")));
  expect(screen.getByRole("alert").textContent).toContain("metadata offline");
  fireEvent.click(button("도면 정보 다시 불러오기")); await ready();
  expect(button("다음 쪽").disabled).toBe(false);
  expect(api.searchDrawingSheets).toHaveBeenCalledTimes(2);
});

it("keeps an empty processed index distinct from a load failure", async () => {
  vi.mocked(api.searchDrawingSheets).mockResolvedValue(index([])); open();
  await screen.findByText(/처리된 도면이 없습니다/);
  expect(button("이동").disabled).toBe(true);
  expect(screen.queryByRole("alert")).toBeNull();
});

it("does not reuse the old PDF index when delayed metadata arrives after a file switch", async () => {
  let resolveOld!: (value: DrawingSheetSearchResponse) => void;
  vi.mocked(api.searchDrawingSheets).mockReturnValueOnce(new Promise(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce(index([0], 2));
  open(); fireEvent.click(button("다른 PDF")); await ready();
  await act(async () => resolveOld(index([0, 1, 2])));
  expect(screen.getByRole("heading", { level: 1 }).textContent).toContain("SYN2-0");
  expect(button("다음 쪽").disabled).toBe(true);
  expect(screen.getByRole("link", { name: "목록으로" }).getAttribute("href")).toBe("/drawings?drawingFileId=2");
});

it("can recover from a direct URL for a missing page through adjacent processed pages", async () => {
  vi.mocked(api.searchDrawingSheets).mockResolvedValue(index([0, 2])); open(1); await ready();
  expect(screen.getByText(/현재 쪽은 처리된 도면 목록에 없습니다/)).toBeTruthy();
  fireEvent.click(button("다음 쪽"));
  expect(screen.getByRole("img").getAttribute("src")).toContain("/pages/2/image");
  expect(screen.queryByText(/현재 쪽은 처리된 도면 목록에 없습니다/)).toBeNull();
});
