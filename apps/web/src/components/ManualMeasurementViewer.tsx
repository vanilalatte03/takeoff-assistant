import { MouseEvent, PointerEvent, useEffect, useMemo, useRef, useState } from "react";

import { listMeasurements, updateMeasurement } from "../api/client";
import type { Measurement } from "../types/api";
import { ErrorMessage } from "./ApiState";

type Point = {
  x: number;
  y: number;
};

type Size = {
  width: number;
  height: number;
};

type MeasurementMode = "SCALE" | "LINE_LENGTH" | "RECTANGLE_AREA" | "POLYGON_AREA" | "COUNT_CLICK";

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
};

const measurementModes: MeasurementMode[] = ["SCALE", "LINE_LENGTH", "RECTANGLE_AREA", "POLYGON_AREA", "COUNT_CLICK"];

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

  const selectedMeasurement = useMemo(
    () => measurements.find((measurement) => String(measurement.id) === selectedMeasurementId) ?? null,
    [measurements, selectedMeasurementId],
  );
  const selectableMeasurements = useMemo(
    () => (mode === "COUNT_CLICK" ? measurements.filter((measurement) => measurement.measurement_type === "COUNT") : measurements),
    [measurements, mode],
  );
  const canMeasure = scale !== null || mode === "SCALE" || mode === "COUNT_CLICK";
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
  }, [points, result, scale, mode, naturalSize, zoom]);

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

    if (mode === "RECTANGLE_AREA" && points.length === 2) {
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
