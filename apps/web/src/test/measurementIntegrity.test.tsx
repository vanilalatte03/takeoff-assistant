import { MemoryRouter } from "react-router-dom";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ManualMeasurementViewer } from "../components/ManualMeasurementViewer";
import { MeasurementCalculationForm } from "../components/MeasurementCalculationForm";
import { RoomFinishesPage } from "../pages/RoomFinishesPage";
import * as api from "../api/client";
import type { Measurement, RoomFinish } from "../types/api";

vi.mock("../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/client")>(),
  listMeasurements: vi.fn(), updateMeasurement: vi.fn(),
  listProjects: vi.fn(), listProjectDrawingFiles: vi.fn(),
  getDimensionCandidates: vi.fn(), calculateMeasurement: vi.fn(),
  listRoomFinishes: vi.fn(), updateRoomFinish: vi.fn(), rejectRoomFinish: vi.fn(),
  createRoomFinishForDrawingFile: vi.fn(), extractRoomFinishes: vi.fn(),
}));

const measurement = (patch: Partial<Measurement> = {}): Measurement => ({
  id: 1, project_id: 1, room_finish_id: 1, room_no: "103", room_name: "Office",
  category: "FLOOR", finish_code: "VCT", measurement_type: "FLOOR_AREA",
  formula: null, quantity: null, unit: "m2", source_sheets: "AE601", status: "DRAFT",
  memo: "reviewer note", coordinates_json: null, deductions_json: null,
  measurement_confidence: null, created_at: "2026-05-10", ...patch,
});

beforeEach(() => {
  vi.resetAllMocks();
  sessionStorage.clear();
  vi.mocked(api.listProjects).mockResolvedValue([{id:1,name:"Test",created_at:"2026-11-05",description:null}]);
  vi.mocked(api.listProjectDrawingFiles).mockResolvedValue([{id:1,project_id:1,original_filename:"synthetic.pdf",stored_path:"synthetic.pdf",page_count:1,created_at:"2026-11-05"}]);
  vi.mocked(api.listMeasurements).mockResolvedValue([measurement()]);
  vi.mocked(api.updateMeasurement).mockImplementation(async (_id, patch) => measurement(patch as Partial<Measurement>));
});

function viewerProps(pageIndex = 0) {
  return { drawingFileId: 1, pageIndex, imageUrl: `/image/${pageIndex}`, sourceSheetNo: `AE10${pageIndex + 1}`, onImageError: vi.fn() };
}

async function readyViewer(rows: Measurement[] = [measurement()]) {
  vi.mocked(api.listMeasurements).mockResolvedValue(rows);
  const view = render(<ManualMeasurementViewer {...viewerProps()} />);
  await waitFor(() => expect(screen.getByLabelText("저장할 Measurement 후보").querySelectorAll("option").length).toBeGreaterThan(0));
  const image = screen.getByRole("img");
  Object.defineProperties(image, { naturalWidth: { value: 1000 }, naturalHeight: { value: 1000 } });
  fireEvent.load(image);
  const canvas = view.container.querySelector("canvas")!;
  canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 1000, height: 1000 } as DOMRect);
  return { ...view, canvas };
}

function calibrate(canvas: HTMLCanvasElement) {
  fireEvent.click(canvas, { clientX: 0, clientY: 0 });
  fireEvent.click(canvas, { clientX: 100, clientY: 0 });
}

describe("measurement integrity", () => {
  it("restores saved calculation inputs and deductions when a row is reopened", async () => {
    const row = measurement({ measurement_type: "WALL_AREA", category: "WALL", quantity: "17.43", formula: "4.2 * 4.6 - 0.9 * 2.1",
      deductions_json: { items: [{ amount: "1.89", label: "door", formula: "0.9 * 2.1" }] },
      coordinates_json: { calculation_inputs: { calculation_type: "WALL_AREA", wall_length: "4.2", wall_height: "4.6", deductions: [{ amount: "1.89", label: "door", formula: "0.9 * 2.1" }] } },
    });
    vi.mocked(api.calculateMeasurement).mockResolvedValue(row);
    const view = render(<MeasurementCalculationForm measurement={row} onSaved={vi.fn()} />);
    view.rerender(<MeasurementCalculationForm measurement={measurement({ id: 2 })} onSaved={vi.fn()} />);
    view.rerender(<MeasurementCalculationForm measurement={row} onSaved={vi.fn()} />);
    expect((screen.getByLabelText("Length (m)") as HTMLInputElement).value).toBe("4.2");
    expect((screen.getByLabelText("Deduction amount") as HTMLInputElement).value).toBe("1.89");
    fireEvent.click(screen.getByRole("button", { name: "계산 저장" }));
    await waitFor(() => expect(api.calculateMeasurement).toHaveBeenCalledWith(1, expect.objectContaining({ wall_length: "4.2", wall_height: "4.6", deductions: [{ amount: "1.89", label: "door", formula: "0.9 * 2.1" }] })));
  });

  it("keeps legacy deductions when only dimension candidates were saved", () => {
    const row = measurement({ measurement_type: "WALL_AREA", deductions_json: { items: [{ amount: "1.89", label: "door", formula: "0.9 * 2.1" }] }, coordinates_json: { dimension_assist: { selected_candidates: [
      { slot: "wall_length", raw_text: "4200", normalized_value: "4.2", source_sheet: "AE101" },
      { slot: "wall_height", raw_text: "4600", normalized_value: "4.6", source_sheet: "AE101" },
    ] } } });
    render(<MeasurementCalculationForm measurement={row} onSaved={vi.fn()} />);
    expect((screen.getByLabelText("Deduction amount") as HTMLInputElement).value).toBe("1.89");
    expect(screen.getByText("17.43 m2")).toBeTruthy();
    expect((screen.getByLabelText("Source Sheets") as HTMLInputElement).value).toBe("AE601, AE101");
  });

  it("prefers exact saved deduction inputs over rounded legacy display evidence", async () => {
    const row = measurement({ quantity: "1.00", deductions_json: { items: [{ amount: "0.01" }] }, coordinates_json: { calculation_inputs: {
      calculation_type: "AREA_RECTANGLE", width: "1", height: "1", deductions: [{ amount: "0.005", label: null, formula: null }],
    } } });
    vi.mocked(api.calculateMeasurement).mockResolvedValue(row);
    render(<MeasurementCalculationForm measurement={row} onSaved={vi.fn()} />);
    expect((screen.getByLabelText("Deduction amount") as HTMLInputElement).value).toBe("0.005");
    expect(screen.getByText("1.00 m2")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "계산 저장" }));
    await waitFor(() => expect(api.calculateMeasurement).toHaveBeenCalledWith(1, expect.objectContaining({ deductions: [{ amount: "0.005", label: null, formula: null }] })));
  });

  it("clears scale and unsaved geometry on page changes", async () => {
    const view = await readyViewer();
    calibrate(view.canvas);
    fireEvent.click(screen.getByRole("button", { name: "사각형 면적" }));
    fireEvent.click(view.canvas, { clientX: 0, clientY: 0 });
    fireEvent.click(view.canvas, { clientX: 100, clientY: 100 });
    expect((screen.getByRole("button", { name: "Measurement에 저장" }) as HTMLButtonElement).disabled).toBe(false);
    view.rerender(<ManualMeasurementViewer {...viewerProps(1)} />);
    expect(screen.getByText("스케일 모드에서 두 점을 선택하세요.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Measurement에 저장" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("does not offer area rows as targets for length measurements", async () => {
    const view = await readyViewer();
    calibrate(view.canvas);
    fireEvent.click(screen.getByRole("button", { name: "선 길이" }));
    calibrate(view.canvas);
    expect(screen.getByLabelText("저장할 Measurement 후보").querySelectorAll("option")).toHaveLength(0);
    expect((screen.getByRole("button", { name: "Measurement에 저장" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("preserves provenance and notes while replacing obsolete calculation evidence", async () => {
    const row = measurement({ coordinates_json: { dimension_assist: { selected_candidates: [] }, calculation_inputs: { width: "1" }, merged_sources: [{ id: 9 }] }, deductions_json: { items: [{ amount: "1.89" }] } });
    const view = await readyViewer([row]);
    calibrate(view.canvas);
    fireEvent.click(screen.getByRole("button", { name: "사각형 면적" }));
    fireEvent.click(view.canvas, { clientX: 0, clientY: 0 });
    fireEvent.click(view.canvas, { clientX: 100, clientY: 100 });
    fireEvent.click(screen.getByRole("button", { name: "Measurement에 저장" }));
    await waitFor(() => expect(api.updateMeasurement).toHaveBeenCalled());
    const patch = vi.mocked(api.updateMeasurement).mock.calls[0][1];
    expect(patch.source_sheets).toBe("AE601, AE101");
    expect(patch.memo).toBe("reviewer note");
    expect(patch).toHaveProperty("deductions_json", null);
    expect(patch.coordinates_json?.dimension_assist).toEqual(row.coordinates_json?.dimension_assist);
    expect(patch.coordinates_json?.merged_sources).toEqual([{ id: 9 }]);
    expect(patch.coordinates_json).not.toHaveProperty("calculation_inputs");
  });

  it("reopens a manual result in custom mode instead of reusing older dimension candidates", async () => {
    const row = measurement({ coordinates_json: { dimension_assist: { selected_candidates: [
      { slot: "width", raw_text: "99000", normalized_value: "99", source_sheet: "AE101" },
      { slot: "height", raw_text: "99000", normalized_value: "99", source_sheet: "AE101" },
    ] } } });
    const view = await readyViewer([row]);
    calibrate(view.canvas);
    fireEvent.click(screen.getByRole("button", { name: "사각형 면적" }));
    fireEvent.click(view.canvas, { clientX: 0, clientY: 0 });
    fireEvent.click(view.canvas, { clientX: 100, clientY: 100 });
    fireEvent.click(screen.getByRole("button", { name: "Measurement에 저장" }));
    await waitFor(() => expect(api.updateMeasurement).toHaveBeenCalled());
    const saved = await vi.mocked(api.updateMeasurement).mock.results[0].value;
    view.unmount();
    render(<MeasurementCalculationForm measurement={saved} onSaved={vi.fn()} />);
    expect((screen.getByLabelText("Calculation Type") as HTMLSelectElement).value).toBe("CUSTOM");
    expect((screen.getByLabelText("Quantity") as HTMLInputElement).value).toBe("17.64");
    expect(screen.queryByLabelText("Width (m)")).toBeNull();
  });

  it("requires an explicit review transition before editing a confirmed row", async () => {
    const row = measurement({ status: "CONFIRMED" });
    const onSaved = vi.fn();
    vi.mocked(api.updateMeasurement).mockResolvedValue(measurement());
    render(<MeasurementCalculationForm measurement={row} onSaved={onSaved} />);
    expect(screen.getByLabelText("Category").matches(":disabled")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "재검토 시작" }));
    await waitFor(() => expect(api.updateMeasurement).toHaveBeenCalledWith(1, { status: "DRAFT" }));
    expect(onSaved).toHaveBeenCalled();
  });

  it("replaces an invalid legacy quantity after explicit reopening instead of validating it as new metadata", async () => {
    const legacy = measurement({ quantity: "-8", formula: "legacy invalid", unit: "EA" });
    vi.mocked(api.updateMeasurement).mockImplementation(async (_id, patch) => {
      if (patch.quantity !== null || patch.formula !== null) throw new Error("Clear the invalid previous calculation before applying metadata.");
      return measurement({ unit: "m2", quantity: null, formula: null });
    });
    vi.mocked(api.calculateMeasurement).mockResolvedValue(measurement({ quantity: "6.00", formula: "2 * 3" }));
    render(<MeasurementCalculationForm measurement={legacy} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Width (m)"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Height (m)"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "계산 저장" }));
    await waitFor(() => expect(api.calculateMeasurement).toHaveBeenCalledWith(1, expect.objectContaining({ width: "2", height: "3" })));
    expect(api.updateMeasurement).toHaveBeenCalledWith(1, expect.objectContaining({ quantity: null, formula: null, unit: "m2" }));
  });

  it("clears the previous area quantity before calculating a count after a type change", async () => {
    const row = measurement({ quantity: "17.43", formula: "4.2 * 4.6 - 1.89" });
    vi.mocked(api.updateMeasurement).mockImplementation(async (_id, patch) => {
      if (patch.quantity !== null || patch.formula !== null) throw new Error("The previous fractional area is not a valid COUNT quantity.");
      return measurement({ measurement_type: "COUNT", unit: "EA", quantity: null, formula: null });
    });
    vi.mocked(api.calculateMeasurement).mockResolvedValue(measurement({ measurement_type: "COUNT", quantity: "2", formula: "2", unit: "EA" }));
    render(<MeasurementCalculationForm measurement={row} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Measurement Type"), { target: { value: "COUNT" } });
    fireEvent.change(screen.getByLabelText("Count"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "계산 저장" }));
    await waitFor(() => expect(api.calculateMeasurement).toHaveBeenCalledWith(1, expect.objectContaining({ calculation_type: "COUNT", count: "2" })));
    expect(api.updateMeasurement).toHaveBeenCalledWith(1, expect.objectContaining({ measurement_type: "COUNT", unit: "EA", quantity: null, formula: null }));
  });

  it("invalidates the previous calculation when saving a changed measurement type without calculating", async () => {
    render(<MeasurementCalculationForm measurement={measurement({ quantity: "17.43", formula: "old area" })} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Measurement Type"), { target: { value: "COUNT" } });
    fireEvent.click(screen.getByRole("button", { name: "후보 정보 저장" }));
    await waitFor(() => expect(api.updateMeasurement).toHaveBeenCalledWith(1, expect.objectContaining({ measurement_type: "COUNT", quantity: null, formula: null })));
    expect(api.calculateMeasurement).not.toHaveBeenCalled();
  });

  it.each(["COUNT", "CUSTOM"] as const)("blocks fractional %s quantities in EA before making any API changes", (calculationType) => {
    const row = measurement({ measurement_type: "COUNT", quantity: "2", unit: "EA", formula: "2", coordinates_json: { calculation_inputs: {
      calculation_type: calculationType, count: "2", custom_quantity: "2", custom_formula: "2", unit: "EA",
    } } });
    render(<MeasurementCalculationForm measurement={row} onSaved={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(calculationType === "COUNT" ? "Count" : "Quantity"), { target: { value: "2.5" } });
    expect((screen.getByRole("button", { name: "계산 저장" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.submit(screen.getByRole("button", { name: "계산 저장" }).closest("form")!);
    expect(api.updateMeasurement).not.toHaveBeenCalled();
    expect(api.calculateMeasurement).not.toHaveBeenCalled();
  });

  it.each(["network", "validation"] as const)("preserves a valid previous calculation when replacement fails with a %s error", async (failure) => {
    const row = measurement({ measurement_type: "COUNT", quantity: "2", unit: "EA", formula: "2", coordinates_json: { calculation_inputs: { calculation_type: "COUNT", count: "2" } } });
    const onSaved = vi.fn();
    vi.mocked(api.updateMeasurement).mockImplementation(async (_id, patch) => ({ ...row, quantity: patch.quantity === null ? null : row.quantity, formula: patch.formula === null ? null : row.formula }));
    vi.mocked(api.calculateMeasurement).mockRejectedValue(failure === "network" ? new TypeError("Failed to fetch") : new api.ApiError(400, "Calculation rejected"));
    render(<MeasurementCalculationForm measurement={row} onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText("Count"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "계산 저장" }));
    await screen.findByRole("alert");
    expect(api.calculateMeasurement).toHaveBeenCalled();
    const metadataPatch = vi.mocked(api.updateMeasurement).mock.calls[0][1];
    expect(metadataPatch).not.toHaveProperty("quantity");
    expect(metadataPatch).not.toHaveProperty("formula");
    expect(onSaved).toHaveBeenCalledWith(expect.objectContaining({ quantity: "2", formula: "2" }));
  });

  it("ignores a dimension response for a page that is no longer open", async () => {
    let resolve!: (value: Awaited<ReturnType<typeof api.getDimensionCandidates>>) => void;
    vi.mocked(api.getDimensionCandidates).mockReturnValue(new Promise((done) => { resolve = done; }));
    const view = await readyViewer();
    fireEvent.click(screen.getByRole("button", { name: "Dimension region" }));
    fireEvent.click(view.canvas, { clientX: 0, clientY: 0 });
    fireEvent.click(view.canvas, { clientX: 100, clientY: 100 });
    view.rerender(<ManualMeasurementViewer {...viewerProps(1)} />);
    await act(async () => resolve({ drawing_file_id: 1, page_index: 0, warnings: ["old page warning"], candidates: [] }));
    expect(screen.queryByText("old page warning")).toBeNull();
  });

  it("ignores older region responses that arrive after the current region", async () => {
    const responses: Array<(value: Awaited<ReturnType<typeof api.getDimensionCandidates>>) => void> = [];
    vi.mocked(api.getDimensionCandidates).mockImplementation(() => new Promise((resolve) => responses.push(resolve)));
    const view = await readyViewer();
    fireEvent.click(screen.getByRole("button", { name: "Dimension region" }));
    fireEvent.click(view.canvas, { clientX: 0, clientY: 0 });
    fireEvent.click(view.canvas, { clientX: 100, clientY: 100 });
    fireEvent.click(view.canvas, { clientX: 200, clientY: 200 });
    await act(async () => responses[1]({ drawing_file_id: 1, page_index: 0, candidates: [], warnings: ["current region"] }));
    await act(async () => responses[0]({ drawing_file_id: 1, page_index: 0, candidates: [], warnings: ["stale region"] }));
    expect(screen.getByText("current region")).toBeTruthy();
    expect(screen.queryByText("stale region")).toBeNull();
  });

  it("clears file-specific state and ignores measurements from the previously open file", async () => {
    let resolveOld!: (rows: Measurement[]) => void;
    vi.mocked(api.listMeasurements)
      .mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }))
      .mockResolvedValueOnce([measurement({ id: 3, room_no: "new-file" })]);
    const view = render(<ManualMeasurementViewer {...viewerProps()} />);
    view.rerender(<ManualMeasurementViewer {...viewerProps()} drawingFileId={2} imageUrl="/other-file" />);
    await screen.findByRole("option", { name: /new-file/ });
    await act(async () => resolveOld([measurement({ id: 1, room_no: "old-file" })]));
    expect(screen.queryByRole("option", { name: /old-file/ })).toBeNull();
    expect(screen.getByRole("option", { name: /new-file/ })).toBeTruthy();
    expect(screen.getByText("스케일 모드에서 두 점을 선택하세요.")).toBeTruthy();
  });

  it("blocks manual edits to confirmed rows and omits rejected targets", async () => {
    const view = await readyViewer([measurement({ status: "CONFIRMED" }), measurement({ id: 2, status: "REJECTED" })]);
    expect(screen.getByLabelText("저장할 Measurement 후보").querySelectorAll("option")).toHaveLength(1);
    calibrate(view.canvas);
    fireEvent.click(screen.getByRole("button", { name: "사각형 면적" }));
    fireEvent.click(view.canvas, { clientX: 0, clientY: 0 });
    fireEvent.click(view.canvas, { clientX: 100, clientY: 100 });
    expect((screen.getByRole("button", { name: "Measurement에 저장" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "재검토 시작" }));
    await waitFor(() => expect(api.updateMeasurement).toHaveBeenCalledWith(1, { status: "DRAFT" }));
    await waitFor(() => expect((screen.getByRole("button", { name: "Measurement에 저장" }) as HTMLButtonElement).disabled).toBe(false));
  });

  it("uses newly selected dimension evidence after the server invalidates old inputs, retaining deductions", async () => {
    const row = measurement({ measurement_type: "WALL_AREA", coordinates_json: { active_input_source: "manual_geometry", measurement_mode: "RECTANGLE_AREA", result: { quantity: "17.64" }, calculation_inputs: { calculation_type: "WALL_AREA", wall_length: "4.2", wall_height: "4.6" } }, deductions_json: { items: [{ amount: "1.89", label: "door" }] } });
    vi.mocked(api.getDimensionCandidates).mockResolvedValue({ drawing_file_id: 1, page_index: 0, warnings: [], candidates: [{ raw_text: "4500", normalized_value: "4.5", normalized_unit: "m", unit_guess: "mm", source_sheet: "AE101", page_index: 0, bbox: null, confidence: 0.78, status: "NEEDS_REVIEW", warning: null }] });
    let saved = row;
    vi.mocked(api.updateMeasurement).mockImplementation(async (_id, patch) => {
      const { calculation_inputs: _obsolete, ...coordinates } = patch.coordinates_json ?? {};
      saved = { ...row, source_sheets: patch.source_sheets ?? row.source_sheets, coordinates_json: coordinates };
      return saved;
    });
    const view = await readyViewer([row]);
    fireEvent.click(screen.getByRole("button", { name: "Dimension region" }));
    fireEvent.click(view.canvas, { clientX: 0, clientY: 0 });
    fireEvent.click(view.canvas, { clientX: 100, clientY: 100 });
    fireEvent.click(await screen.findByRole("button", { name: /^Length$/ }));
    fireEvent.click(screen.getByRole("button", { name: "Save evidence for calculation" }));
    await waitFor(() => expect(api.updateMeasurement).toHaveBeenCalled());
    expect(saved.source_sheets).toBe("AE601, AE101");
    view.unmount();
    render(<MeasurementCalculationForm measurement={saved} onSaved={vi.fn()} />);
    expect((screen.getByLabelText("Length (m)") as HTMLInputElement).value).toBe("4.5");
    expect((screen.getByLabelText("Deduction amount") as HTMLInputElement).value).toBe("1.89");
  });

  it.each([
    { type: "PERIMETER_LENGTH", input: { calculation_type: "PERIMETER_RECTANGLE", width: "4.2", height: "2.7" }, label: "Width (m)", value: "4.2" },
    { type: "PARTITION_AREA", input: { calculation_type: "PARTITION_AREA", wall_length: "4.2", wall_height: "4.6", side_multiplier: "2" }, label: "Side Count", value: "2" },
    { type: "COUNT", input: { calculation_type: "COUNT", count: "7" }, label: "Count", value: "7" },
    { type: "FLOOR_AREA", input: { calculation_type: "CUSTOM", custom_formula: "3 + 4", custom_quantity: "7", unit: "m2" }, label: "Quantity", value: "7" },
  ] as const)("restores the saved $type calculation mode and inputs", ({ type, input, label, value }) => {
    render(<MeasurementCalculationForm measurement={measurement({ measurement_type: type, coordinates_json: { calculation_inputs: input } })} onSaved={vi.fn()} />);
    expect((screen.getByLabelText("Calculation Type") as HTMLSelectElement).value).toBe(input.calculation_type);
    expect((screen.getByLabelText(label) as HTMLInputElement).value).toBe(value);
  });

  it("reopens a confirmed RoomFinish with a status-only PATCH and keeps rejected rows immutable", async () => {
    const room: RoomFinish = { id: 1, project_id: 1, drawing_file_id: 1, drawing_sheet_id: 1, room_no: "103", room_name: "Office", floor_material: null, floor_finish: "VCT", base_material: null, base_finish: null, wall_material: null, wall_finish: null, ceiling_material: null, ceiling_finish: null, height: null, remarks: null, source_sheet_no: "AE601", confidence: 0.7, status: "CONFIRMED" };
    vi.mocked(api.listRoomFinishes).mockResolvedValue([room, { ...room, id: 2, room_no: "104", status: "REJECTED" }]);
    vi.mocked(api.updateRoomFinish).mockResolvedValue({ ...room, status: "DRAFT" });
    render(<MemoryRouter initialEntries={["/room-finishes?drawingFileId=1"]}><RoomFinishesPage /></MemoryRouter>);
    await screen.findByRole("option", {name:/synthetic.pdf/});
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    const confirmed = await screen.findByDisplayValue("103");
    const rejected = screen.getByDisplayValue("104");
    expect((confirmed as HTMLInputElement).disabled).toBe(true);
    expect((rejected as HTMLInputElement).disabled).toBe(true);
    expect(within(rejected.closest("tr")!).queryByRole("button", { name: "재검토 시작" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "재검토 시작" }));
    await waitFor(() => expect(api.updateRoomFinish).toHaveBeenCalledWith(1, { status: "DRAFT" }));
    await waitFor(() => expect((screen.getByDisplayValue("103") as HTMLInputElement).disabled).toBe(false));
  });

  it("allows a draft RoomFinish to be confirmed without prematurely locking unsaved status", async () => {
    const room = { id: 1, project_id: 1, drawing_sheet_id: 1, room_no: "103", room_name: "Office", floor_finish: "VCT", base_finish: null, wall_finish: null, ceiling_finish: null, height: null, remarks: null, source_sheet_no: "AE601", status: "DRAFT" } as RoomFinish;
    vi.mocked(api.listRoomFinishes).mockResolvedValue([room]);
    vi.mocked(api.updateRoomFinish).mockResolvedValue({ ...room, status: "CONFIRMED" });
    render(<MemoryRouter initialEntries={["/room-finishes?drawingFileId=1"]}><RoomFinishesPage /></MemoryRouter>);
    await screen.findByRole("option", {name:/synthetic.pdf/});
    fireEvent.click(screen.getByRole("button", { name: "Load" }));
    const row = (await screen.findByDisplayValue("103")).closest("tr")!;
    fireEvent.change(within(row).getByRole("combobox"), { target: { value: "CONFIRMED" } });
    expect((within(row).getByRole("button", { name: "Save" }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(within(row).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.updateRoomFinish).toHaveBeenCalledWith(1, expect.objectContaining({ status: "CONFIRMED" })));
    await screen.findByRole("button", { name: "재검토 시작" });
    expect((screen.getByDisplayValue("103") as HTMLInputElement).disabled).toBe(true);
  });
});
