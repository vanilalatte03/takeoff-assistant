import type { MeasurementType } from "./types/api";

export const measurementLabels: Record<MeasurementType, string> = {
  FLOOR_AREA: "바닥 면적", CEILING_AREA: "천장 면적", WALL_AREA: "벽 면적",
  PARTITION_AREA: "파티션 면적", PERIMETER_LENGTH: "둘레 길이", COUNT: "개수",
};
