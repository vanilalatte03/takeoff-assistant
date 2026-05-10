import { MouseEvent, PointerEvent, useEffect, useMemo, useRef, useState } from "react";

import { getDimensionCandidates, listMeasurements, updateMeasurement } from "../api/client";
import type { DimensionCandidate, DimensionCandidateSlot, DimensionRegion, Measurement } from "../types/api";
import { ErrorMessage } from "./ApiState";

type Point = {
  x: number;
  y: number;
};

type Size = {
  width: number;
  height: number;
};

type MeasurementMode = "SCALE" | "LINE_LENGTH" | "RECTANGLE_AREA" | "POLYGON_AREA" | "COUNT_CLICK" | "DIMENSION_REGION";

type MeasurementResult = {
  mode: MeasurementMode;
  quantity: number;
  unit: "m" | "m2" | "EA";
  formula: string;
  points: Point[];
};

type ScaleState = {
  referenceLengthM: number;
  pixelsPerMeter: number;
  points: [Point, Point];
};

type PanDragState = {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startPan: Point;
};

interface ManualMeasurementViewerProps {
  drawingFileId: number;
  pageIndex: number;
  imageUrl: string;
  sourceSheetNo?: string | null;
  onImageError: () => void;
}

const modeLabels: Record<MeasurementMode, string> = {
  SCALE: "스케일",
  LINE_LENGTH: "선 길이",
  RECTANGLE_AREA: "사각형 면적",
  POLYGON_AREA: "다각형 면적",
  COUNT_CLICK: "개수 클릭",
  DIMENSION_REGION: "Dimension region",
};

const measurementModes: MeasurementMode[] = ["SCALE", "LINE_LENGTH", "RECTANGLE_AREA", "POLYGON_AREA", "COUNT_CLICK", "DIMENSION_REGION"];
const dimensionSlots: DimensionCandidateSlot[] = ["width", "height", "wall_length", "wall_height", "side_multiplier"];
const dimensionSlotLabels: Record<DimensionCandidateSlot, string> = {
  width: "Width",
  height: "Height",
  wall_length: "Length",
  wall_height: "Wall height",
  side_multiplier: "Side count",
};

function modeLabel(mode: MeasurementMode) {
  return modeLabels[mode];
}

function distance(first: Point, second: Point) {
  return Math.hypot(second.x - first.x, second.y - first.y);
}

function polygonArea(points: Point[]) {
  const sum = points.reduce((total, point, index) => {
    const next = points[(index + 1) % points.length];
    return total + point.x * next.y - next.x * point.y;
  }, 0);
  return Math.abs(sum) / 2;
}

function round2(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function formatNumber(value: number) {
  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

function parsePositiveNumber(value: string, label: string) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${label}은 0보다 큰 숫자여야 합니다.`);
  }
  return parsed;
}

function pointKey(point: Point) {
  return `${Math.round(point.x)},${Math.round(point.y)}`;
}

function measurementOptionLabel(measurement: Measurement) {
  const room = measurement.room_no ? `Room ${measurement.room_no}` : "Room -";
  const roomName = measurement.room_name ?? "-";
  const category = measurement.category
    ? measurement.category.toLowerCase().replace(/^\w/, (value) => value.toUpperCase())
    : "-";
  return `[#${measurement.id}] ${room} / ${roomName} / ${category} / ${measurement.finish_code} / ${measurement.status}`;
}

function dimensionCandidateLabel(candidate: DimensionCandidate) {
  const value = candidate.normalized_value === null ? "?" : `${candidate.normalized_value} ${candidate.normalized_unit ?? ""}`.trim();
  return `${candidate.raw_text} -> ${value}`;
}

function normalizedDimensionValue(candidate: DimensionCandidate) {
  return candidate.normalized_value === null || candidate.normalized_value === undefined ? "" : String(candidate.normalized_value);
}

function emptyDimensionSelections(): Record<DimensionCandidateSlot, DimensionCandidate | null> {
  return {
    width: null,
    height: null,
    wall_length: null,
    wall_height: null,
    side_multiplier: null,
  };
}

function buildDimensionRegion(points: Point[], naturalSize: Size, zoom: number, pan: Point): DimensionRegion | null {
  if (points.length < 2 || !naturalSize.width || !naturalSize.height) {
    return null;
  }
  const [start, end] = points;
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);
  if (width < 1 || height < 1) {
    return null;
  }
  return {
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    width,
    height,
    image_width: naturalSize.width,
    image_height: naturalSize.height,
    zoom,
    pan_x: pan.x,
    pan_y: pan.y,
  };
}

function clampZoom(value: number) {
  return Math.min(Math.max(value, 0.1), 6);
}

export function ManualMeasurementViewer({
  drawingFileId,
  pageIndex,
  imageUrl,
  sourceSheetNo,
  onImageError,
}: ManualMeasurementViewerProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const panDragRef = useRef<PanDragState | null>(null);
  const [mode, setMode] = useState<MeasurementMode>("SCALE");
  const [isPanMode, setIsPanMode] = useState(false);
  const [points, setPoints] = useState<Point[]>([]);
  const [scaleLength, setScaleLength] = useState("4.2");
  const [scale, setScale] = useState<ScaleState | null>(null);
  const [result, setResult] = useState<MeasurementResult | null>(null);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [selectedMeasurementId, setSelectedMeasurementId] = useState("");
  const [isLoadingMeasurements, setIsLoadingMeasurements] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [naturalSize, setNaturalSize] = useState<Size>({ width: 0, height: 0 });
  const [viewportSize, setViewportSize] = useState<Size>({ width: 0, height: 0 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Point>({ x: 16, y: 16 });
  const [dimensionRegion, setDimensionRegion] = useState<DimensionRegion | null>(null);
  const [dimensionCandidates, setDimensionCandidates] = useState<DimensionCandidate[]>([]);
  const [dimensionSelections, setDimensionSelections] = useState<Record<DimensionCandidateSlot, DimensionCandidate | null>>(emptyDimensionSelections);
  const [dimensionWarnings, setDimensionWarnings] = useState<string[]>([]);
  const [isLoadingDimensions, setIsLoadingDimensions] = useState(false);

  const selectedMeasurement = useMemo(
    () => measurements.find((measurement) => String(measurement.id) === selectedMeasurementId) ?? null,
    [measurements, selectedMeasurementId],
  );
  const selectableMeasurements = useMemo(
    () => (mode === "COUNT_CLICK" ? measurements.filter((measurement) => measurement.measurement_type === "COUNT") : measurements),
    [measurements, mode],
  );
  const canMeasure = scale !== null || mode === "SCALE" || mode === "COUNT_CLICK" || mode === "DIMENSION_REGION";
  const hasMeasurementCandidates = selectableMeasurements.length > 0;

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return undefined;
    }

    const updateSize = () => {
      const rect = viewport.getBoundingClientRect();
      setViewportSize({ width: rect.width, height: rect.height });
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setIsLoadingMeasurements(true);
    listMeasurements(drawingFileId)
      .then((loaded) => {
        setMeasurements(loaded);
        setSelectedMeasurementId(loaded[0] ? String(loaded[0].id) : "");
      })
      .catch(setError)
      .finally(() => setIsLoadingMeasurements(false));
  }, [drawingFileId]);

  useEffect(() => {
    drawOverlay();
  }, [points, result, scale, mode, naturalSize, zoom, dimensionRegion]);

  function viewportRect() {
    return viewportRef.current?.getBoundingClientRect() ?? null;
  }

  function centerPan(nextZoom: number, size: Size = naturalSize) {
    const rect = viewportRect();
    if (!rect || !size.width || !size.height) {
      return { x: 16, y: 16 };
    }
    return {
      x: Math.max((rect.width - size.width * nextZoom) / 2, 16),
      y: Math.max((rect.height - size.height * nextZoom) / 2, 16),
    };
  }

  function fitToScreen(size: Size = naturalSize) {
    const rect = viewportRect();
    if (!rect || !size.width || !size.height) {
      return;
    }
    const nextZoom = clampZoom(Math.min((rect.width - 32) / size.width, (rect.height - 32) / size.height));
    setZoom(nextZoom);
    setPan(centerPan(nextZoom, size));
  }

  function fitToWidth(size: Size = naturalSize) {
    const rect = viewportRect();
    if (!rect || !size.width) {
      return;
    }
    const nextZoom = clampZoom((rect.width - 32) / size.width);
    setZoom(nextZoom);
    setPan({ x: 16, y: 16 });
  }

  function resetZoom() {
    setZoom(1);
    setPan(centerPan(1));
  }

  function zoomBy(factor: number) {
    const nextZoom = clampZoom(zoom * factor);
    const rect = viewportRect();
    if (!rect) {
      setZoom(nextZoom);
      return;
    }
    const center = {
      x: (rect.width / 2 - pan.x) / zoom,
      y: (rect.height / 2 - pan.y) / zoom,
    };
    setZoom(nextZoom);
    setPan({
      x: rect.width / 2 - center.x * nextZoom,
      y: rect.height / 2 - center.y * nextZoom,
    });
  }

  function handleImageLoad() {
    const image = imageRef.current;
    if (!image) {
      return;
    }
    const nextSize = {
      width: image.naturalWidth,
      height: image.naturalHeight,
    };
    setNaturalSize(nextSize);
    requestAnimationFrame(() => fitToWidth(nextSize));
  }

  function toImagePoint(event: MouseEvent<HTMLCanvasElement>): Point | null {
    const canvas = canvasRef.current;
    if (!canvas || !naturalSize.width || !naturalSize.height) {
      return null;
    }

    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * naturalSize.width,
      y: ((event.clientY - rect.top) / rect.height) * naturalSize.height,
    };
  }

  function drawOverlay() {
    const canvas = canvasRef.current;
    if (!canvas || !naturalSize.width || !naturalSize.height) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    canvas.width = naturalSize.width * dpr;
    canvas.height = naturalSize.height * dpr;
    canvas.style.width = `${naturalSize.width}px`;
    canvas.style.height = `${naturalSize.height}px`;

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, naturalSize.width, naturalSize.height);
    context.lineWidth = Math.max(2 / zoom, 1);
    context.lineCap = "round";
    context.lineJoin = "round";

    if (scale?.points.length === 2) {
      drawLine(context, scale.points, "#7a4b00");
    }

    if (result?.mode === "RECTANGLE_AREA") {
      drawRectangle(context, result.points, "#1659c7", true);
    } else if (result?.mode === "POLYGON_AREA") {
      drawPolygon(context, result.points, "#1659c7", true);
    } else if (result?.mode === "LINE_LENGTH") {
      drawLine(context, result.points, "#1659c7");
    }

    if (dimensionRegion) {
      drawRegion(context, dimensionRegion, "#8d4cf6");
    }

    if (mode === "COUNT_CLICK") {
      // Count mode should show independent click markers, not connect them as a line.
    } else if (mode === "DIMENSION_REGION" && points.length === 2) {
      drawRectangle(context, points, "#8d4cf6", false);
    } else if (mode === "RECTANGLE_AREA" && points.length === 2) {
      drawRectangle(context, points, "#1f6feb", false);
    } else if (mode === "POLYGON_AREA" && points.length > 1) {
      drawPolygon(context, points, "#1f6feb", false);
    } else if (points.length > 1) {
      drawLine(context, points, "#1f6feb");
    }

    [...(scale?.points ?? []), ...points].forEach((point) => drawPoint(context, point));
  }

  function drawPoint(context: CanvasRenderingContext2D, point: Point) {
    context.beginPath();
    context.arc(point.x, point.y, Math.max(5 / zoom, 3), 0, Math.PI * 2);
    context.fillStyle = "#ffffff";
    context.fill();
    context.strokeStyle = "#172026";
    context.stroke();
  }

  function drawLine(context: CanvasRenderingContext2D, linePoints: Point[], color: string) {
    if (linePoints.length < 2) {
      return;
    }
    context.beginPath();
    context.moveTo(linePoints[0].x, linePoints[0].y);
    context.lineTo(linePoints[1].x, linePoints[1].y);
    context.strokeStyle = color;
    context.stroke();
  }

  function drawRectangle(context: CanvasRenderingContext2D, rectanglePoints: Point[], color: string, fill: boolean) {
    if (rectanglePoints.length < 2) {
      return;
    }
    const [start, end] = rectanglePoints;
    const left = Math.min(start.x, end.x);
    const top = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    if (fill) {
      context.fillStyle = "rgb(31 111 235 / 12%)";
      context.fillRect(left, top, width, height);
    }
    context.strokeStyle = color;
    context.strokeRect(left, top, width, height);
  }

  function drawPolygon(context: CanvasRenderingContext2D, polygonPoints: Point[], color: string, fill: boolean) {
    if (polygonPoints.length < 2) {
      return;
    }
    context.beginPath();
    context.moveTo(polygonPoints[0].x, polygonPoints[0].y);
    polygonPoints.slice(1).forEach((point) => context.lineTo(point.x, point.y));
    if (fill && polygonPoints.length > 2) {
      context.closePath();
      context.fillStyle = "rgb(31 111 235 / 12%)";
      context.fill();
    }
    context.strokeStyle = color;
    context.stroke();
  }

  function drawRegion(context: CanvasRenderingContext2D, region: DimensionRegion, color: string) {
    context.fillStyle = "rgb(141 76 246 / 10%)";
    context.fillRect(region.x, region.y, region.width, region.height);
    context.strokeStyle = color;
    context.strokeRect(region.x, region.y, region.width, region.height);
  }

  function handlePanPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!isPanMode) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    panDragRef.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startPan: pan,
    };
  }

  function handlePanPointerMove(event: PointerEvent<HTMLDivElement>) {
    const drag = panDragRef.current;
    if (!isPanMode || !drag || drag.pointerId !== event.pointerId) {
      return;
    }
    setPan({
      x: drag.startPan.x + event.clientX - drag.startClientX,
      y: drag.startPan.y + event.clientY - drag.startClientY,
    });
  }

  function handlePanPointerUp(event: PointerEvent<HTMLDivElement>) {
    if (panDragRef.current?.pointerId === event.pointerId) {
      panDragRef.current = null;
    }
  }

  function handleCanvasClick(event: MouseEvent<HTMLCanvasElement>) {
    if (isPanMode) {
      return;
    }
    setError(null);
    setSaveMessage(null);
    if (!canMeasure) {
      setError(new Error("먼저 스케일을 설정해 주세요."));
      return;
    }

    const point = toImagePoint(event);
    if (!point) {
      return;
    }

    if (mode === "DIMENSION_REGION") {
      const nextPoints = [...points, point].slice(-2);
      setPoints(nextPoints);
      if (nextPoints.length === 2) {
        void loadDimensionCandidates(nextPoints);
      }
      return;
    }

    if (mode === "COUNT_CLICK") {
      const nextPoints = [...points, point];
      setPoints(nextPoints);
      setResult({
        mode,
        quantity: nextPoints.length,
        unit: "EA",
        formula: `count(${nextPoints.length})`,
        points: nextPoints,
      });
      return;
    }

    if (mode === "POLYGON_AREA") {
      setPoints((current) => [...current, point]);
      return;
    }

    const nextPoints = [...points, point].slice(-2);
    setPoints(nextPoints);
    if (nextPoints.length === 2) {
      buildResult(nextPoints);
    }
  }

  async function loadDimensionCandidates(regionPoints: Point[]) {
    const region = buildDimensionRegion(regionPoints, naturalSize, zoom, pan);
    if (!region) {
      setError(new Error("Select a valid region on the rendered page."));
      return;
    }

    setDimensionRegion(region);
    setDimensionCandidates([]);
    setDimensionSelections(emptyDimensionSelections());
    setDimensionWarnings([]);
    setIsLoadingDimensions(true);
    try {
      const response = await getDimensionCandidates(drawingFileId, pageIndex, { region });
      setDimensionCandidates(response.candidates);
      setDimensionWarnings(response.warnings);
      if (!response.candidates.length) {
        setSaveMessage(null);
      }
    } catch (caught) {
      setError(caught);
    } finally {
      setIsLoadingDimensions(false);
    }
  }

  function assignDimensionCandidate(slot: DimensionCandidateSlot, candidate: DimensionCandidate) {
    setDimensionSelections((current) => ({ ...current, [slot]: candidate }));
    setSaveMessage(null);
    setError(null);
  }

  async function saveDimensionAssistEvidence() {
    setError(null);
    setSaveMessage(null);
    if (!selectedMeasurement) {
      setError(new Error("Choose a Measurement candidate before saving dimension evidence."));
      return;
    }
    if (!dimensionRegion) {
      setError(new Error("Select a dimension region first."));
      return;
    }
    const selectedCandidates = dimensionSlots.flatMap((slot) => {
      const candidate = dimensionSelections[slot];
      return candidate
        ? [
            {
              ...candidate,
              slot,
            },
          ]
        : [];
    });
    if (!selectedCandidates.length) {
      setError(new Error("Map at least one dimension candidate to a calculation input."));
      return;
    }

    setIsSaving(true);
    try {
      const nextCoordinates = {
        ...(selectedMeasurement.coordinates_json ?? {}),
        dimension_assist: {
          region: {
            drawing_file_id: drawingFileId,
            page_index: pageIndex,
            source_sheet_no: sourceSheetNo ?? null,
            image: {
              natural_width: naturalSize.width,
              natural_height: naturalSize.height,
            },
            view_transform: {
              zoom,
              pan,
            },
            rect: dimensionRegion,
          },
          selected_candidates: selectedCandidates,
        },
      };
      const saved = await updateMeasurement(selectedMeasurement.id, {
        coordinates_json: nextCoordinates,
        source_sheets: selectedMeasurement.source_sheets || sourceSheetNo || selectedCandidates[0]?.source_sheet || "",
      });
      setMeasurements((current) => current.map((measurement) => (measurement.id === saved.id ? saved : measurement)));
      setSelectedMeasurementId(String(saved.id));
      setSaveMessage(`Dimension evidence saved to Measurement ${saved.id}. Open Measurement Review to calculate with prefilled values.`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsSaving(false);
    }
  }

  function buildResult(candidatePoints: Point[]) {
    try {
      if (mode === "SCALE") {
        const referenceLengthM = parsePositiveNumber(scaleLength, "실제 길이");
        const pixelLength = distance(candidatePoints[0], candidatePoints[1]);
        if (pixelLength <= 0) {
          throw new Error("서로 다른 두 점을 선택해 주세요.");
        }
        setScale({
          referenceLengthM,
          pixelsPerMeter: pixelLength / referenceLengthM,
          points: [candidatePoints[0], candidatePoints[1]],
        });
        setResult(null);
        return;
      }

      if (!scale) {
        throw new Error("먼저 스케일을 설정해 주세요.");
      }

      if (mode === "LINE_LENGTH") {
        const lengthM = round2(distance(candidatePoints[0], candidatePoints[1]) / scale.pixelsPerMeter);
        setResult({
          mode,
          quantity: lengthM,
          unit: "m",
          formula: `${formatNumber(distance(candidatePoints[0], candidatePoints[1]))} px / ${formatNumber(scale.pixelsPerMeter)} px_per_m`,
          points: candidatePoints,
        });
      }

      if (mode === "RECTANGLE_AREA") {
        const widthM = Math.abs(candidatePoints[1].x - candidatePoints[0].x) / scale.pixelsPerMeter;
        const heightM = Math.abs(candidatePoints[1].y - candidatePoints[0].y) / scale.pixelsPerMeter;
        setResult({
          mode,
          quantity: round2(widthM * heightM),
          unit: "m2",
          formula: `${formatNumber(widthM)} m * ${formatNumber(heightM)} m`,
          points: candidatePoints,
        });
      }
    } catch (caught) {
      setError(caught);
    }
  }

  function finishPolygon() {
    setError(null);
    if (!scale) {
      setError(new Error("먼저 스케일을 설정해 주세요."));
      return;
    }
    if (points.length < 3) {
      setError(new Error("다각형 면적은 최소 3점을 선택해야 합니다."));
      return;
    }
    const areaM2 = round2(polygonArea(points) / scale.pixelsPerMeter ** 2);
    setResult({
      mode: "POLYGON_AREA",
      quantity: areaM2,
      unit: "m2",
      formula: `${formatNumber(polygonArea(points))} px2 / ${formatNumber(scale.pixelsPerMeter)}^2`,
      points,
    });
  }

  function handleModeChange(nextMode: MeasurementMode) {
    setMode(nextMode);
    if (nextMode === "COUNT_CLICK") {
      const firstCountMeasurement = measurements.find((measurement) => measurement.measurement_type === "COUNT");
      setSelectedMeasurementId(firstCountMeasurement ? String(firstCountMeasurement.id) : "");
    }
    setIsPanMode(false);
    setPoints([]);
    setResult(null);
    if (nextMode !== "DIMENSION_REGION") {
      setDimensionRegion(null);
      setDimensionCandidates([]);
      setDimensionSelections(emptyDimensionSelections());
      setDimensionWarnings([]);
    }
    setError(null);
    setSaveMessage(null);
  }

  function undoPoint() {
    setPoints((current) => {
      const nextPoints = current.slice(0, -1);
      if (mode === "COUNT_CLICK" && nextPoints.length) {
        setResult({
          mode,
          quantity: nextPoints.length,
          unit: "EA",
          formula: `count(${nextPoints.length})`,
          points: nextPoints,
        });
      } else {
        setResult(null);
      }
      return nextPoints;
    });
  }

  function clearMeasurement() {
    setPoints([]);
    setResult(null);
    if (mode === "DIMENSION_REGION") {
      setDimensionRegion(null);
      setDimensionCandidates([]);
      setDimensionSelections(emptyDimensionSelections());
      setDimensionWarnings([]);
    }
    setError(null);
    setSaveMessage(null);
  }

  async function saveMeasurement() {
    setError(null);
    setSaveMessage(null);
    if (!result) {
      setError(new Error("저장할 측정 결과가 없습니다."));
      return;
    }
    if (!selectedMeasurement) {
      setError(new Error("저장할 Measurement 후보를 선택해 주세요."));
      return;
    }

    if (result.mode === "COUNT_CLICK" && selectedMeasurement.measurement_type !== "COUNT") {
      setError(new Error("개수 클릭 결과는 COUNT Measurement 후보에만 저장할 수 있습니다."));
      return;
    }
    if (result.mode !== "COUNT_CLICK" && selectedMeasurement.measurement_type === "COUNT") {
      setError(new Error("COUNT Measurement에는 개수 클릭 모드 결과를 저장해 주세요."));
      return;
    }

    setIsSaving(true);
    try {
      const saved = await updateMeasurement(selectedMeasurement.id, {
        formula: result.formula,
        quantity: result.mode === "COUNT_CLICK" ? String(result.quantity) : result.quantity.toFixed(2),
        unit: result.unit,
        source_sheets: selectedMeasurement.source_sheets || sourceSheetNo || "",
        status: "DRAFT",
        memo: `manual ${modeLabel(result.mode)} measurement`,
        coordinates_json: {
          measurement_mode: result.mode,
          drawing_file_id: drawingFileId,
          page_index: pageIndex,
          image: {
            natural_width: naturalSize.width,
            natural_height: naturalSize.height,
          },
          view_transform: {
            zoom,
            pan,
          },
          scale: scale
            ? {
                reference_length_m: scale.referenceLengthM,
                pixels_per_meter: scale.pixelsPerMeter,
                points: scale.points,
              }
            : null,
          points: result.points,
          point_keys: result.points.map(pointKey),
          result: {
            formula: result.formula,
            quantity: result.mode === "COUNT_CLICK" ? String(result.quantity) : result.quantity.toFixed(2),
            unit: result.unit,
          },
        },
      });
      setMeasurements((current) => current.map((measurement) => (measurement.id === saved.id ? saved : measurement)));
      setSelectedMeasurementId(String(saved.id));
      setSaveMessage(`Measurement ${saved.id}에 ${saved.quantity ?? result.quantity.toFixed(2)} ${saved.unit ?? result.unit} 저장 완료`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="manual-measurement-layout">
      <div
        ref={viewportRef}
        className={`measurement-canvas-panel ${isPanMode ? "pan-mode" : ""}`}
        onPointerDown={handlePanPointerDown}
        onPointerMove={handlePanPointerMove}
        onPointerUp={handlePanPointerUp}
        onPointerCancel={handlePanPointerUp}
      >
        <div
          className="measurement-canvas-content"
          style={{
            width: naturalSize.width || undefined,
            height: naturalSize.height || undefined,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          }}
        >
          <img
            ref={imageRef}
            src={imageUrl}
            alt={`Drawing page ${pageIndex}`}
            style={{
              width: naturalSize.width || undefined,
              height: naturalSize.height || undefined,
            }}
            onLoad={handleImageLoad}
            onError={onImageError}
          />
          <canvas ref={canvasRef} className="measurement-overlay" onClick={handleCanvasClick} />
        </div>
      </div>

      <aside className="measurement-tools">
        <h2>수동 측정</h2>
        <div className="tool-group">
          <span className="tool-label">보기</span>
          <div className="button-row wrap">
            <button type="button" className="button-secondary" onClick={() => zoomBy(1.2)}>
              확대
            </button>
            <button type="button" className="button-secondary" onClick={() => zoomBy(1 / 1.2)}>
              축소
            </button>
            <button type="button" className="button-secondary" onClick={() => fitToScreen()}>
              화면 맞춤
            </button>
            <button type="button" className="button-secondary" onClick={() => fitToWidth()}>
              폭 맞춤
            </button>
            <button type="button" className="button-secondary" onClick={resetZoom}>
              100%
            </button>
            <button type="button" className={isPanMode ? "active" : "button-secondary"} onClick={() => setIsPanMode((value) => !value)}>
              드래그 이동
            </button>
          </div>
          <span className="muted-cell">
            Zoom {formatNumber(zoom * 100)}% / viewport {Math.round(viewportSize.width)} x {Math.round(viewportSize.height)}
          </span>
        </div>

        <div className="tool-group">
          <span className="tool-label">측정 모드</span>
          <div className="segmented-control">
            {measurementModes.map((item) => (
              <button
                key={item}
                type="button"
                className={mode === item ? "active" : "button-secondary"}
                onClick={() => handleModeChange(item)}
              >
                {modeLabel(item)}
              </button>
            ))}
          </div>
        </div>

        <label>
          <span>스케일 실제 길이 (m)</span>
          <input value={scaleLength} inputMode="decimal" onChange={(event) => setScaleLength(event.target.value)} />
        </label>

        <div className="scale-readout">
          {scale ? (
            <>
              <strong>{formatNumber(scale.pixelsPerMeter)} px/m</strong>
              <span>기준 길이 {formatNumber(scale.referenceLengthM)} m</span>
            </>
          ) : (
            <span>스케일 모드에서 두 점을 선택하세요.</span>
          )}
        </div>

        <div className="button-row wrap">
          <button type="button" className="button-secondary" onClick={undoPoint} disabled={!points.length}>
            마지막 점 취소
          </button>
          <button type="button" className="button-secondary" onClick={clearMeasurement}>
            지우기
          </button>
          <button type="button" className="button-secondary" onClick={finishPolygon} disabled={mode !== "POLYGON_AREA"}>
            다각형 완료
          </button>
        </div>

        <div className="measurement-result">
          <span className="tool-label">현재 결과</span>
          {result ? (
            <>
              <strong>
                {formatNumber(result.quantity)} {result.unit}
              </strong>
              <span>{result.formula}</span>
            </>
          ) : (
            <span>
              {mode === "POLYGON_AREA"
                ? "점을 찍은 뒤 다각형 완료를 누르세요."
                : mode === "COUNT_CLICK"
                  ? "개수만큼 위치를 클릭하세요."
                  : "두 점을 선택하세요."}
            </span>
          )}
        </div>

        <label>
          <span>저장할 Measurement 후보</span>
          <select
            value={selectedMeasurementId}
            onChange={(event) => setSelectedMeasurementId(event.target.value)}
            disabled={isLoadingMeasurements || !hasMeasurementCandidates}
          >
            {selectableMeasurements.map((measurement) => (
              <option key={measurement.id} value={measurement.id}>
                {measurementOptionLabel(measurement)}
              </option>
            ))}
          </select>
        </label>

        {mode === "DIMENSION_REGION" ? (
          <div className="dimension-assist-panel">
            <div className="section-heading compact-heading">
              <h3>Dimension candidates</h3>
              <span className="count-label">{dimensionCandidates.length}</span>
            </div>
            {dimensionRegion ? (
              <span className="muted-cell">
                Region {Math.round(dimensionRegion.x)}, {Math.round(dimensionRegion.y)} / {Math.round(dimensionRegion.width)} x{" "}
                {Math.round(dimensionRegion.height)}
              </span>
            ) : null}
            {isLoadingDimensions ? <div className="empty-state compact">Loading candidates...</div> : null}
            {dimensionWarnings.length ? (
              <div className="message message-warning">
                <ul className="message-list">
                  {dimensionWarnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {dimensionCandidates.length ? (
              <div className="dimension-candidate-list">
                {dimensionCandidates.map((candidate) => (
                  <div className="dimension-candidate-card" key={`${candidate.raw_text}-${candidate.page_index}-${candidate.source_sheet ?? ""}`}>
                    <strong>{dimensionCandidateLabel(candidate)}</strong>
                    <span>
                      {candidate.source_sheet ?? "-"} / confidence {candidate.confidence.toFixed(2)}
                    </span>
                    {candidate.warning ? <span className="message-inline-warning">{candidate.warning}</span> : null}
                    <div className="button-row wrap compact-row">
                      {dimensionSlots.map((slot) => (
                        <button
                          key={slot}
                          type="button"
                          className={dimensionSelections[slot]?.raw_text === candidate.raw_text ? "active" : "button-secondary"}
                          disabled={!normalizedDimensionValue(candidate)}
                          onClick={() => assignDimensionCandidate(slot, candidate)}
                        >
                          {dimensionSlotLabels[slot]}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : !isLoadingDimensions && dimensionRegion ? (
              <div className="empty-state compact">No candidates. Use manual calculation input as fallback.</div>
            ) : null}
            <div className="dimension-selection-summary">
              {dimensionSlots.map((slot) => (
                <span key={slot}>
                  {dimensionSlotLabels[slot]}: {dimensionSelections[slot] ? dimensionCandidateLabel(dimensionSelections[slot]) : "-"}
                </span>
              ))}
            </div>
            <button type="button" onClick={saveDimensionAssistEvidence} disabled={isSaving || !selectedMeasurement || !dimensionRegion}>
              {isSaving ? "Saving..." : "Save evidence for calculation"}
            </button>
          </div>
        ) : null}

        {!hasMeasurementCandidates ? (
          <div className="empty-state compact">먼저 Room Finish 후보 추출과 Measurement 후보 생성을 실행하세요.</div>
        ) : null}

        <button type="button" onClick={saveMeasurement} disabled={isSaving || !result || !selectedMeasurement}>
          {isSaving ? "저장 중" : "Measurement에 저장"}
        </button>

        <ErrorMessage error={error} />
        {saveMessage ? <div className="message message-success">{saveMessage}</div> : null}
      </aside>
    </div>
  );
}
