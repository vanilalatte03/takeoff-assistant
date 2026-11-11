import type { DrawingSheetRole } from "./types/api";

export const sheetRoles: Array<DrawingSheetRole | ""> = [
  "", "FINISH_SCHEDULE", "FLOOR_PLAN", "ENLARGED_FLOOR_PLAN", "CEILING_PLAN",
  "PARTITION_PLAN", "PARTITION_DETAIL", "DOOR_SCHEDULE", "WINDOW_SCHEDULE", "DETAIL", "UNKNOWN",
];

export function readDrawingSearch(params: URLSearchParams) {
  const role = params.get("sheetRole") ?? "";
  const sheetRole: DrawingSheetRole | "" = sheetRoles.includes(role as DrawingSheetRole) ? role as DrawingSheetRole : "";
  return {
    sheetNo: (params.get("sheetNo") ?? "").trim(),
    keyword: (params.get("keyword") ?? "").trim(),
    sheetRole,
    roomQuery: (params.get("roomQuery") ?? "").trim(),
  };
}

// Carry only search fields. The route's PDF always owns detail and return links.
export function drawingSearchParams(drawingFileId: string | number, search: ReturnType<typeof readDrawingSearch>) {
  const params = new URLSearchParams({ drawingFileId: String(drawingFileId) });
  for (const [key, value] of Object.entries(search)) {
    if (value.trim()) params.set(key, value.trim());
  }
  return params;
}
