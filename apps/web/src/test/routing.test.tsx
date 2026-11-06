import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import * as api from "../api/client";

vi.mock("../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/client")>(),
  listProjects: vi.fn(),
  listProjectDrawingFiles: vi.fn(),
  searchDrawingSheets: vi.fn(),
  listMeasurements: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.mocked(api.listProjects).mockResolvedValue([{id:1,name:"First",description:null,created_at:"2026-11-05"},{id:2,name:"Second",description:null,created_at:"2026-11-05"}]);
  vi.mocked(api.listProjectDrawingFiles).mockImplementation(async id=>[{id:id===1?42:84,project_id:id,original_filename:`synthetic-${id}.pdf`,stored_path:"synthetic.pdf",page_count:3,created_at:"2026-11-05"}]);
  vi.mocked(api.searchDrawingSheets).mockResolvedValue({ drawing_file_id: 42, results: [] });
  vi.mocked(api.listMeasurements).mockResolvedValue([]);
});

function HistoryControls() {
  const location = useLocation();
  const navigate = useNavigate();
  return <>
    <output aria-label="현재 경로">{location.pathname}{location.search}</output>
    <button onClick={() => navigate(-1)}>뒤로</button>
    <button onClick={() => navigate(1)}>앞으로</button>
    <button onClick={() => navigate("/measurements?drawingFileId=84")}>다른 도면 주소</button>
  </>;
}

function openApp(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /><HistoryControls /></MemoryRouter>);
}

describe("application routing", () => {
  it("updates the selected PDF and project on a same-page URL change and browser back", async () => {
    openApp("/measurements?drawingFileId=42");
    await screen.findByRole("option", {name:/synthetic-1.pdf/});
    expect((screen.getByLabelText("도면 PDF") as HTMLSelectElement).value).toBe("42");
    fireEvent.click(screen.getByRole("button", {name:"다른 도면 주소"}));
    await screen.findByRole("option", {name:/synthetic-2.pdf/});
    expect((screen.getByLabelText("도면 PDF") as HTMLSelectElement).value).toBe("84");
    expect((screen.getByLabelText("프로젝트") as HTMLSelectElement).value).toBe("2");
    fireEvent.click(screen.getByRole("button", {name:"Load"}));
    await waitFor(()=>expect(api.listMeasurements).toHaveBeenCalledWith(84));
    fireEvent.click(screen.getByRole("button", {name:"뒤로"}));
    await screen.findByRole("option", {name:/synthetic-1.pdf/});
    expect((screen.getByLabelText("도면 PDF") as HTMLSelectElement).value).toBe("42");
  });

  it.each(["/", "/missing-page"])("opens guided workflow from %s", async (path) => {
    openApp(path);
    await waitFor(() => expect(screen.getByLabelText("현재 경로").textContent).toBe("/workflow"));
    expect(screen.getByRole("link", { name: "작업 시작·이어서 하기" }).getAttribute("aria-current")).toBe("page");
    await waitFor(() => expect(api.listProjects).toHaveBeenCalled());
  });

  it("navigates all sidebar pages and restores browser history", async () => {
    openApp("/upload");
    for (const [label, path, title] of [
      ["도면 목록/검색", "/drawings", "도면 목록/검색"],
      ["Room Finish", "/room-finishes", "Room Finish Review"],
      ["Measurement", "/measurements", "Measurement Review"],
    ]) {
      fireEvent.click(screen.getByRole("link", { name: label }));
      expect(await screen.findByRole("heading", { name: title, level: 1 })).toBeTruthy();
      expect(screen.getByLabelText("현재 경로").textContent).toBe(path);
      expect(screen.getByRole("link", { name: label }).getAttribute("aria-current")).toBe("page");
    }
    fireEvent.click(screen.getByRole("button", { name: "뒤로" }));
    expect(await screen.findByRole("heading", { name: "Room Finish Review", level: 1 })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "앞으로" }));
    expect(await screen.findByRole("heading", { name: "Measurement Review", level: 1 })).toBeTruthy();
    fireEvent.click(screen.getByRole("link", { name: "PDF 업로드" }));
    expect(screen.getByLabelText("현재 경로").textContent).toBe("/upload");
    await waitFor(() => expect(api.listProjects).toHaveBeenCalled());
  });

  it("preserves drawing and page parameters through page changes and the list link", async () => {
    openApp("/drawings/42/pages/0");
    await waitFor(() => expect(api.searchDrawingSheets).toHaveBeenCalledWith(42, {}));
    expect((screen.getByLabelText("Page Index") as HTMLInputElement).value).toBe("0");
    expect(screen.getByRole("link", { name: "도면 목록/검색" }).getAttribute("aria-current")).toBe("page");
    fireEvent.change(screen.getByLabelText("Page Index"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "이동" }));
    expect(screen.getByLabelText("현재 경로").textContent).toBe("/drawings/42/pages/3");
    expect(screen.getByRole("img").getAttribute("src")).toContain("/drawing-files/42/pages/3/image");
    fireEvent.click(screen.getByRole("link", { name: "목록으로" }));
    expect(await screen.findByRole("heading", { name: "도면 목록/검색", level: 1 })).toBeTruthy();
    expect(screen.getByLabelText("현재 경로").textContent).toBe("/drawings?drawingFileId=42");
    await screen.findByRole("option", {name:/synthetic-1.pdf/});
    expect((screen.getByLabelText("도면 PDF") as HTMLSelectElement).value).toBe("42");
  });
});
