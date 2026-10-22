export type ReviewStatus = "DRAFT" | "NEEDS_REVIEW" | "CONFIRMED" | "REJECTED";

export type DrawingSheetRole =
  | "FINISH_SCHEDULE"
  | "FLOOR_PLAN"
  | "ENLARGED_FLOOR_PLAN"
  | "CEILING_PLAN"
  | "PARTITION_PLAN"
  | "PARTITION_DETAIL"
  | "DOOR_SCHEDULE"
  | "WINDOW_SCHEDULE"
  | "DOOR_WINDOW_NUMBERING_PLAN"
  | "DETAIL"
  | "UNKNOWN";

export type MeasurementType =
  | "FLOOR_AREA"
  | "CEILING_AREA"
  | "PERIMETER_LENGTH"
  | "WALL_AREA"
  | "PARTITION_AREA"
  | "COUNT";

export type CalculationType =
  | "AREA_RECTANGLE"
  | "PERIMETER_RECTANGLE"
  | "WALL_AREA"
  | "PARTITION_AREA"
  | "COUNT"
  | "CUSTOM";

export interface DrawingFile {
  id: number;
  project_id: number;
  original_filename: string;
  stored_path: string;
  page_count: number;
  created_at: string;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  created_at?: string;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface DrawingSheet {
  id: number;
  drawing_file_id: number;
  page_index: number;
  sheet_no: string | null;
  sheet_title: string | null;
  role: DrawingSheetRole;
  text_content: string;
  sheet_detection_confidence: number | null;
  status: ReviewStatus;
}

export interface DrawingSheetSearchResult {
  page_index: number;
  sheet_no: string | null;
  sheet_title: string | null;
  sheet_role: DrawingSheetRole;
  confidence: number | null;
}

export interface DrawingSheetSearchResponse {
  drawing_file_id: number;
  results: DrawingSheetSearchResult[];
}

export interface RoomPageCandidate {
  page_index: number;
  sheet_no: string | null;
  sheet_title: string | null;
  sheet_role: DrawingSheetRole;
  room_no: string | null;
  room_name: string | null;
  evidence: string[];
  confidence: number;
}

export interface RoomPageCandidateResponse {
  drawing_file_id: number;
  room_query: string;
  candidates: RoomPageCandidate[];
  warnings: string[];
}

export interface DimensionRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  image_width?: number | null;
  image_height?: number | null;
  zoom?: number | null;
  pan_x?: number | null;
  pan_y?: number | null;
}

export interface DimensionCandidate {
  raw_text: string;
  normalized_value: string | number | null;
  normalized_unit: string | null;
  unit_guess: string | null;
  source_sheet: string | null;
  page_index: number;
  bbox: Record<string, number> | null;
  confidence: number;
  status: ReviewStatus;
  warning: string | null;
}

export interface DimensionCandidateRequest {
  region?: DimensionRegion | null;
}

export interface DimensionCandidateResponse {
  drawing_file_id: number;
  page_index: number;
  candidates: DimensionCandidate[];
  warnings: string[];
}

export type DimensionCandidateSlot = "width" | "height" | "wall_length" | "wall_height" | "side_multiplier";

export interface DimensionAssistSelectedCandidate extends DimensionCandidate {
  slot: DimensionCandidateSlot;
}

export interface DrawingFilePageProcessResult {
  drawing_file_id: number;
  page_count: number;
  sheets: DrawingSheet[];
}

export interface DrawingFileSheetDetectionResult {
  drawing_file_id: number;
  sheets: DrawingSheet[];
}

export interface DrawingFileSheetClassificationResult {
  drawing_file_id: number;
  sheets: DrawingSheet[];
}

export interface RoomFinish {
  id: number;
  project_id: number;
  drawing_sheet_id: number | null;
  drawing_file_id?: number | null;
  room_no: string | null;
  room_name: string | null;
  floor_material: string | null;
  floor_finish: string | null;
  base_material: string | null;
  base_finish: string | null;
  wall_material: string | null;
  wall_finish: string | null;
  ceiling_material: string | null;
  ceiling_finish: string | null;
  height: string | null;
  remarks: string | null;
  source_sheet_no: string | null;
  confidence: number | null;
  status: ReviewStatus;
}

export type RoomFinishUpdate = Partial<
  Pick<
    RoomFinish,
    | "drawing_sheet_id"
    | "room_no"
    | "room_name"
    | "floor_material"
    | "floor_finish"
    | "base_material"
    | "base_finish"
    | "wall_material"
    | "wall_finish"
    | "ceiling_material"
    | "ceiling_finish"
    | "height"
    | "remarks"
    | "source_sheet_no"
    | "confidence"
    | "status"
  >
>;

export type RoomFinishCreate = Partial<
  Pick<
    RoomFinish,
    | "drawing_sheet_id"
    | "room_no"
    | "room_name"
    | "floor_material"
    | "floor_finish"
    | "base_material"
    | "base_finish"
    | "wall_material"
    | "wall_finish"
    | "ceiling_material"
    | "ceiling_finish"
    | "height"
    | "remarks"
    | "source_sheet_no"
    | "confidence"
    | "status"
  >
>;

export interface RoomFinishExtractionResult {
  drawing_file_id: number;
  room_finishes: RoomFinish[];
  warnings: string[];
}

export interface Measurement {
  id: number;
  project_id: number;
  room_finish_id: number | null;
  room_no: string | null;
  room_name: string | null;
  category: string;
  finish_code: string;
  measurement_type: MeasurementType;
  formula: string | null;
  quantity: string | number | null;
  unit: string | null;
  source_sheets: string;
  status: ReviewStatus;
  memo: string | null;
  coordinates_json: Record<string, unknown> | null;
  deductions_json: Record<string, unknown> | null;
  measurement_confidence: number | null;
  created_at: string;
}

export interface MeasurementGenerationResult {
  drawing_file_id: number;
  measurements: Measurement[];
}

export interface MeasurementMergeInput {
  target_id: number;
  source_ids: number[];
}

export interface RoomMeasurementStatus {
  room_no: string | null;
  room_name: string | null;
  total_count: number;
  quantity_count: number;
  confirmed_count: number;
  needs_review_count: number;
  missing_quantity_count: number;
}

export interface DrawingFileRoomStatus {
  drawing_file_id: number;
  rooms: RoomMeasurementStatus[];
}

export interface MeasurementUpdate {
  category?: string | null;
  finish_code?: string | null;
  measurement_type?: MeasurementType | null;
  formula?: string | null;
  quantity?: number | string | null;
  unit?: string | null;
  source_sheets?: string | null;
  status?: ReviewStatus | null;
  memo?: string | null;
  coordinates_json?: Record<string, unknown> | null;
  deductions_json?: Record<string, unknown> | null;
  measurement_confidence?: number | null;
}

export interface MeasurementDeductionInput {
  amount: string;
  label?: string | null;
  formula?: string | null;
}

export interface MeasurementCalculationInput {
  calculation_type: CalculationType;
  width?: string | null;
  height?: string | null;
  wall_length?: string | null;
  wall_height?: string | null;
  side_multiplier?: string | null;
  count?: string | null;
  custom_formula?: string | null;
  custom_quantity?: string | null;
  unit?: string | null;
  source_sheets?: string | null;
  deductions?: MeasurementDeductionInput[];
}
