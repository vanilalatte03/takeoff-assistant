import type { Measurement, MeasurementType } from "./types/api";

export function mergeSourceSheets(...values: Array<string | null | undefined>) {
  return [...new Set(values.flatMap((value) => (value ?? "").split(/[,;]/).map((sheet) => sheet.trim()).filter(Boolean)))].join(", ");
}

export const measurementUnits: Record<MeasurementType, "m" | "m2" | "EA"> = {
  FLOOR_AREA: "m2", CEILING_AREA: "m2", PERIMETER_LENGTH: "m",
  WALL_AREA: "m2", PARTITION_AREA: "m2", COUNT: "EA",
};

export function hasInvalidStoredQuantity(measurement: Measurement) {
  if (measurement.quantity === null) return false;
  const quantity = Number(measurement.quantity);
  return !String(measurement.quantity).trim() || !Number.isFinite(quantity) || quantity < 0
    || quantity > 9999999999.99 // Matches the API's Numeric(12, 2) capacity.
    || (measurement.measurement_type === "COUNT" && !Number.isInteger(quantity));
}
