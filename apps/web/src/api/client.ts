import type {
  DrawingFile,
  DrawingFilePageProcessResult,
  DrawingFileRoomStatus,
  DrawingFileSheetClassificationResult,
  DrawingFileSheetDetectionResult,
  DrawingSheetRole,
  DrawingSheetSearchResponse,
  DimensionCandidateRequest,
  DimensionCandidateResponse,
  Measurement,
  MeasurementCalculationInput,
  MeasurementGenerationResult,
  MeasurementMergeInput,
  MeasurementUpdate,
  Project,
  ProjectCreate,
  RoomPageCandidateResponse,
  RoomFinish,
  RoomFinishCreate,
  RoomFinishExtractionResult,
  RoomFinishUpdate,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function buildUrl(path: string, params?: Record<string, string | number | undefined>) {
  const normalizedBase = API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${normalizedBase}${normalizedPath}`, window.location.origin);

  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

async function parseError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (payload.detail) {
      return JSON.stringify(payload.detail);
    }
  } catch {
    return response.statusText;
  }
  return response.statusText;
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  params?: Record<string, string | number | undefined>,
) {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path, params), {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response));
  }

  return (await response.json()) as T;
}

export function pageImageUrl(drawingFileId: number, pageIndex: number) {
  return buildUrl(`/drawing-files/${drawingFileId}/pages/${pageIndex}/image`);
}

export function listProjects() {
  return requestJson<Project[]>("/projects");
}

export function listProjectDrawingFiles(projectId: number) {
  return requestJson<DrawingFile[]>(`/projects/${projectId}/drawing-files`);
}

export function createProject(payload: ProjectCreate) {
  return requestJson<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function uploadDrawingFile(projectId: number, file: File) {
  const body = new FormData();
  body.set("project_id", String(projectId));
  body.set("file", file);

  return requestJson<DrawingFile>("/drawing-files/upload", {
    method: "POST",
    body,
  });
}

export function processDrawingPages(drawingFileId: number) {
  return requestJson<DrawingFilePageProcessResult>(`/drawing-files/${drawingFileId}/pages/process`, {
    method: "POST",
  });
}

export function detectDrawingSheets(drawingFileId: number) {
  return requestJson<DrawingFileSheetDetectionResult>(`/drawing-files/${drawingFileId}/sheets/detect`, {
    method: "POST",
  });
}

export function classifyDrawingSheets(drawingFileId: number) {
  return requestJson<DrawingFileSheetClassificationResult>(`/drawing-files/${drawingFileId}/sheets/classify`, {
    method: "POST",
  });
}

export function searchDrawingSheets(
  drawingFileId: number,
  params: { query?: string; sheetNo?: string; keyword?: string; sheetRole?: DrawingSheetRole | "" },
) {
  return requestJson<DrawingSheetSearchResponse>(`/drawing-files/${drawingFileId}/sheets/search`, undefined, {
    query: params.query,
    sheet_no: params.sheetNo,
    keyword: params.keyword,
    sheet_role: params.sheetRole || undefined,
  });
}

export function findRoomPageCandidates(drawingFileId: number, roomQuery: string) {
  return requestJson<RoomPageCandidateResponse>(`/drawing-files/${drawingFileId}/room-page-candidates`, undefined, {
    room_query: roomQuery,
  });
}

export function getDimensionCandidates(drawingFileId: number, pageIndex: number, payload: DimensionCandidateRequest) {
  return requestJson<DimensionCandidateResponse>(`/drawing-files/${drawingFileId}/pages/${pageIndex}/dimension-candidates`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function extractRoomFinishes(drawingFileId: number) {
  return requestJson<RoomFinishExtractionResult>(`/drawing-files/${drawingFileId}/room-finishes/extract`, {
    method: "POST",
  });
}

export function listRoomFinishes(drawingFileId: number) {
  return requestJson<RoomFinish[]>(`/drawing-files/${drawingFileId}/room-finishes`);
}

export function createRoomFinishForDrawingFile(drawingFileId: number, payload: RoomFinishCreate) {
  return requestJson<RoomFinish>(`/drawing-files/${drawingFileId}/room-finishes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateRoomFinish(roomFinishId: number, payload: RoomFinishUpdate) {
  return requestJson<RoomFinish>(`/room-finishes/${roomFinishId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function rejectRoomFinish(roomFinishId: number) {
  return requestJson<RoomFinish>(`/room-finishes/${roomFinishId}`, {
    method: "DELETE",
  });
}

export function generateMeasurements(drawingFileId: number) {
  return requestJson<MeasurementGenerationResult>(`/drawing-files/${drawingFileId}/measurements/generate`, {
    method: "POST",
  });
}

export function listMeasurements(drawingFileId: number) {
  return requestJson<Measurement[]>(`/drawing-files/${drawingFileId}/measurements`);
}

export function getDrawingFileRoomStatus(drawingFileId: number) {
  return requestJson<DrawingFileRoomStatus>(`/drawing-files/${drawingFileId}/room-status`);
}

export async function downloadMeasurementsExcel(drawingFileId: number) {
  const response = await fetch(buildUrl(`/drawing-files/${drawingFileId}/measurements/export`));
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response));
  }

  const contentDisposition = response.headers.get("content-disposition") ?? "";
  const filenameMatch = contentDisposition.match(/filename="?(?<filename>[^";]+)"?/);
  return {
    blob: await response.blob(),
    filename: filenameMatch?.groups?.filename ?? `finish_takeoff_drawing_file_${drawingFileId}.xlsx`,
  };
}

export function updateMeasurement(measurementId: number, payload: MeasurementUpdate) {
  return requestJson<Measurement>(`/measurements/${measurementId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function rejectMeasurement(measurementId: number) {
  return requestJson<Measurement>(`/measurements/${measurementId}`, {
    method: "DELETE",
  });
}

export function mergeMeasurements(payload: MeasurementMergeInput) {
  return requestJson<Measurement>("/measurements/merge", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function calculateMeasurement(measurementId: number, payload: MeasurementCalculationInput) {
  return requestJson<Measurement>(`/measurements/${measurementId}/calculate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
