import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import * as api from "../api/client";

vi.mock("../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/client")>(),
  listProjects: vi.fn(),
  searchDrawingSheets: vi.fn(),
  listMeasurements: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listProjects).mockResolvedValue([]);
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
  </>;
}

function openApp(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><App /><HistoryControls /></MemoryRouter>);
}

describe("application routing", () => {
  it.each(["/", "/missing-page"])("opens upload from %s", async (path) => {
    openApp(path);
    await waitFor(() => expect(screen.getByLabelText("현재 경로").textContent).toBe("/upload"));
    expect(screen.getByRole("link", { name: "PDF 업로드" }).getAttribute("aria-current")).toBe("page");
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
    for (const input of screen.getAllByLabelText("Drawing File ID")) {
      expect((input as HTMLInputElement).value).toBe("42");
    }
  });
});
