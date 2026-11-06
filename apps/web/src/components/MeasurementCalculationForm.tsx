import { FormEvent, useEffect, useMemo, useState } from "react";

import { calculateMeasurement, updateMeasurement } from "../api/client";
import { hasInvalidStoredQuantity, measurementUnits, mergeSourceSheets } from "../measurementIntegrity";
import type {
  CalculationType,
  DimensionAssistSelectedCandidate,
  DimensionCandidateSlot,
  Measurement,
  MeasurementCalculationInput,
  MeasurementType,
} from "../types/api";
import { ErrorMessage } from "./ApiState";
import { ReviewEvidencePanel } from "./ReviewEvidencePanel";
import { StatusBadge } from "./StatusBadge";

type DeductionDraft = {
  id: string;
  label: string;
  amount: string;
  formula: string;
};

type CalculationDraft = {
  calculationType: CalculationType;
  width: string;
  height: string;
  length: string;
  sideCount: string;
  count: string;
  customFormula: string;
  customQuantity: string;
  customUnit: string;
  sourceSheets: string;
  deductions: DeductionDraft[];
};

type MetadataDraft = {
  category: string;
  finishCode: string;
  measurementType: MeasurementType;
  unit: string;
  memo: string;
};

type PreviewResult =
  | {
      ready: true;
      formula: string;
      quantity: number;
      unit: string;
    }
  | {
      ready: false;
      message: string;
    };

const allowedCalculationTypesByMeasurementType: Record<MeasurementType, CalculationType[]> = {
  FLOOR_AREA: ["AREA_RECTANGLE", "CUSTOM"],
  CEILING_AREA: ["AREA_RECTANGLE", "CUSTOM"],
  PERIMETER_LENGTH: ["PERIMETER_RECTANGLE", "CUSTOM"],
  WALL_AREA: ["WALL_AREA", "CUSTOM"],
  PARTITION_AREA: ["PARTITION_AREA", "CUSTOM"],
  COUNT: ["COUNT", "CUSTOM"],
};

const calculationTypeLabels: Record<CalculationType, string> = {
  AREA_RECTANGLE: "사각형 면적",
  PERIMETER_RECTANGLE: "사각형 둘레",
  WALL_AREA: "벽체 면적",
  PARTITION_AREA: "파티션 면적",
  COUNT: "개수",
  CUSTOM: "직접 입력",
};

const measurementTypes: MeasurementType[] = [
  "FLOOR_AREA",
  "CEILING_AREA",
  "PERIMETER_LENGTH",
  "WALL_AREA",
  "PARTITION_AREA",
  "COUNT",
];

interface MeasurementCalculationFormProps {
  measurement: Measurement | null;
  onSaved: (measurement: Measurement) => void;
  showEvidence?: boolean;
}

function defaultCalculationType(measurement: Measurement): CalculationType {
  return allowedCalculationTypesByMeasurementType[measurement.measurement_type][0];
}

function createDraft(measurement: Measurement): CalculationDraft {
  const prefill = dimensionAssistPrefill(measurement);
  const stored = measurement.coordinates_json?.calculation_inputs;
  const inputs = stored && typeof stored === "object" ? stored as Record<string, unknown> : {};
  const inputString = (field: string, fallback = "") => {
    const value = inputs[field];
    return typeof value === "string" || typeof value === "number" ? String(value) : fallback;
  };
  const allowedTypes = allowedCalculationTypesByMeasurementType[measurement.measurement_type];
  const manualResultIsCurrent = !stored && measurement.coordinates_json?.active_input_source !== "dimension_assist"
    && measurement.coordinates_json?.measurement_mode && measurement.coordinates_json?.result;
  const calculationType = allowedTypes.includes(inputs.calculation_type as CalculationType)
    ? inputs.calculation_type as CalculationType : manualResultIsCurrent ? "CUSTOM" : defaultCalculationType(measurement);
  const storedDeductions = inputs.deductions ?? measurement.deductions_json?.items;
  const deductions: DeductionDraft[] = Array.isArray(storedDeductions)
    ? storedDeductions.flatMap((item, index) => {
      if (!item || typeof item !== "object" || item.amount === null || item.amount === undefined) return [];
      return [{ id: `stored-${index}`, amount: String(item.amount), label: String(item.label ?? ""), formula: String(item.formula ?? "") }];
    }) : [];
  const isWall = measurement.measurement_type === "WALL_AREA" || measurement.measurement_type === "PARTITION_AREA";
  return {
    calculationType,
    width: inputString("width", prefill.width),
    height: isWall ? inputString("wall_height", prefill.wall_height) : inputString("height", prefill.height),
    length: inputString("wall_length", prefill.wall_length),
    sideCount: inputString("side_multiplier", prefill.side_multiplier ?? "1"),
    count: inputString("count"),
    customFormula: inputString("custom_formula", measurement.formula ?? ""),
    customQuantity: inputString("custom_quantity", measurement.quantity === null ? "" : String(measurement.quantity)),
    customUnit: measurementUnits[measurement.measurement_type],
    sourceSheets: mergeSourceSheets(measurement.source_sheets, prefill.sourceSheets, inputString("source_sheets")),
    deductions,
  };
}

function createMetadataDraft(measurement: Measurement): MetadataDraft {
  return {
    category: measurement.category,
    finishCode: measurement.finish_code,
    measurementType: measurement.measurement_type,
    unit: measurementUnits[measurement.measurement_type],
    memo: measurement.memo ?? "",
  };
}

function parseNumber(value: string) {
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function parseRequiredPositive(value: string, label: string) {
  const parsed = parseNumber(value);
  if (parsed === null) {
    throw new Error(`${label} 값을 입력해 주세요.`);
  }
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${label}는 0보다 큰 숫자여야 합니다.`);
  }
  return parsed;
}

function parseRequiredNonNegative(value: string, label: string) {
  const parsed = parseNumber(value);
  if (parsed === null) {
    throw new Error(`${label} 값을 입력해 주세요.`);
  }
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`${label}는 0 이상의 숫자여야 합니다.`);
  }
  return parsed;
}

function round2(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function displayNumber(value: number) {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formulaNumber(value: string) {
  return String(Number(value));
}

function dimensionAssistPrefill(measurement: Measurement) {
  const selectedCandidates = readSelectedDimensionCandidates(measurement);
  const values: Partial<Record<DimensionCandidateSlot, string>> = {};
  const sourceSheets: string[] = [];

  selectedCandidates.forEach((candidate) => {
    if (candidate.normalized_value !== null && candidate.normalized_value !== undefined) {
      values[candidate.slot] = String(candidate.normalized_value);
    }
    if (candidate.source_sheet && !sourceSheets.includes(candidate.source_sheet)) {
      sourceSheets.push(candidate.source_sheet);
    }
  });

  return {
    ...values,
    sourceSheets: sourceSheets.length ? sourceSheets.join(", ") : undefined,
  };
}

function readSelectedDimensionCandidates(measurement: Measurement): DimensionAssistSelectedCandidate[] {
  const dimensionAssist = measurement.coordinates_json?.dimension_assist;
  if (!dimensionAssist || typeof dimensionAssist !== "object" || !("selected_candidates" in dimensionAssist)) {
    return [];
  }
  const selectedCandidates = (dimensionAssist as { selected_candidates?: unknown }).selected_candidates;
  if (!Array.isArray(selectedCandidates)) {
    return [];
  }
  return selectedCandidates.filter(isSelectedDimensionCandidate);
}

function isSelectedDimensionCandidate(value: unknown): value is DimensionAssistSelectedCandidate {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as { slot?: unknown; raw_text?: unknown };
  return typeof candidate.slot === "string" && typeof candidate.raw_text === "string";
}

function deductionTotal(deductions: DeductionDraft[]) {
  return deductions.reduce((total, deduction) => {
    if (!deduction.amount.trim()) {
      return total;
    }
    const parsed = Number(deduction.amount);
    return Number.isFinite(parsed) ? total + parsed : Number.NaN;
  }, 0);
}

function deductionFormula(deductions: DeductionDraft[]) {
  const terms = deductions
    .filter((deduction) => deduction.amount.trim())
    .map((deduction) => deduction.formula.trim() || formulaNumber(deduction.amount));
  if (!terms.length) {
    return "";
  }
  return terms.length === 1 ? terms[0] : `(${terms.join(" + ")})`;
}

function computePreview(draft: CalculationDraft): PreviewResult {
  try {
    const deductions = deductionTotal(draft.deductions);
    if (!Number.isFinite(deductions) || deductions < 0) {
      return { ready: false, message: "공제 수량은 0 이상의 숫자여야 합니다." };
    }

    if (draft.calculationType === "AREA_RECTANGLE") {
      const width = parseRequiredPositive(draft.width, "Width");
      const height = parseRequiredPositive(draft.height, "Height");
      return {
        ready: true,
        formula: `${formulaNumber(draft.width)} * ${formulaNumber(draft.height)}${deductions ? ` - ${deductionFormula(draft.deductions)}` : ""}`,
        quantity: round2(width * height - deductions),
        unit: "m2",
      };
    }

    if (draft.calculationType === "PERIMETER_RECTANGLE") {
      const width = parseRequiredPositive(draft.width, "Width");
      const height = parseRequiredPositive(draft.height, "Height");
      const baseFormula = `(${formulaNumber(draft.width)} + ${formulaNumber(draft.height)}) * 2`;
      return {
        ready: true,
        formula: deductions ? `${baseFormula} - ${deductionFormula(draft.deductions)}` : baseFormula,
        quantity: round2((width + height) * 2 - deductions),
        unit: "m",
      };
    }

    if (draft.calculationType === "WALL_AREA") {
      const length = parseRequiredPositive(draft.length, "Length");
      const height = parseRequiredPositive(draft.height, "Height");
      const baseFormula = `${formulaNumber(draft.length)} * ${formulaNumber(draft.height)}`;
      return {
        ready: true,
        formula: deductions ? `${baseFormula} - ${deductionFormula(draft.deductions)}` : baseFormula,
        quantity: round2(length * height - deductions),
        unit: "m2",
      };
    }

    if (draft.calculationType === "PARTITION_AREA") {
      const length = parseRequiredPositive(draft.length, "Length");
      const height = parseRequiredPositive(draft.height, "Height");
      const sideCount = parseRequiredPositive(draft.sideCount, "Side count");
      const baseFormula = `${formulaNumber(draft.length)} * ${formulaNumber(draft.height)} * ${formulaNumber(draft.sideCount)}`;
      return {
        ready: true,
        formula: deductions ? `${baseFormula} - ${deductionFormula(draft.deductions)}` : baseFormula,
        quantity: round2(length * height * sideCount - deductions),
        unit: "m2",
      };
    }

    if (draft.calculationType === "COUNT") {
      const count = parseRequiredNonNegative(draft.count, "Count");
      if (!Number.isInteger(count)) {
        return { ready: false, message: "Count는 정수여야 합니다." };
      }
      return {
        ready: true,
        formula: formulaNumber(draft.count),
        quantity: round2(count),
        unit: "EA",
      };
    }

    if (!draft.customFormula.trim()) {
      return { ready: false, message: "Custom formula를 입력해 주세요." };
    }
    if (!draft.customUnit.trim()) {
      return { ready: false, message: "Custom unit을 입력해 주세요." };
    }
    const customQuantity = parseRequiredNonNegative(draft.customQuantity, "Custom quantity");
    if (draft.customUnit === "EA" && !Number.isInteger(customQuantity)) {
      return { ready: false, message: "EA 수량은 정수여야 합니다." };
    }
    return {
      ready: true,
      formula: draft.customFormula.trim(),
      quantity: round2(customQuantity),
      unit: draft.customUnit.trim(),
    };
  } catch (error) {
    return {
      ready: false,
      message: error instanceof Error ? error.message : String(error),
    };
  }
}

function buildCalculationPayload(draft: CalculationDraft): MeasurementCalculationInput {
  const common = {
    calculation_type: draft.calculationType,
    source_sheets: draft.sourceSheets.trim() || null,
  };
  const deductions = draft.deductions
    .filter((deduction) => deduction.amount.trim())
    .map((deduction) => ({
      amount: deduction.amount.trim(),
      label: deduction.label.trim() || null,
      formula: deduction.formula.trim() || null,
    }));

  if (draft.calculationType === "AREA_RECTANGLE") {
    return {
      ...common,
      width: draft.width,
      height: draft.height,
      deductions,
    };
  }
  if (draft.calculationType === "PERIMETER_RECTANGLE") {
    return {
      ...common,
      width: draft.width,
      height: draft.height,
      deductions,
    };
  }
  if (draft.calculationType === "WALL_AREA") {
    return {
      ...common,
      wall_length: draft.length,
      wall_height: draft.height,
      deductions,
    };
  }
  if (draft.calculationType === "PARTITION_AREA") {
    return {
      ...common,
      wall_length: draft.length,
      wall_height: draft.height,
      side_multiplier: draft.sideCount,
      deductions,
    };
  }
  if (draft.calculationType === "COUNT") {
    return {
      ...common,
      count: draft.count,
    };
  }
  return {
    ...common,
    custom_formula: draft.customFormula,
    custom_quantity: draft.customQuantity,
    unit: draft.customUnit,
  };
}

export function MeasurementCalculationForm({ measurement, onSaved, showEvidence = true }: MeasurementCalculationFormProps) {
  const [draft, setDraft] = useState<CalculationDraft | null>(measurement ? createDraft(measurement) : null);
  const [metadataDraft, setMetadataDraft] = useState<MetadataDraft | null>(measurement ? createMetadataDraft(measurement) : null);
  const [confirmAfterSave, setConfirmAfterSave] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingMetadata, setIsSavingMetadata] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setDraft(measurement ? createDraft(measurement) : null);
    setMetadataDraft(measurement ? createMetadataDraft(measurement) : null);
    setConfirmAfterSave(false);
    setMessage(null);
    setError(null);
  }, [measurement?.id, measurement?.coordinates_json, measurement?.deductions_json, measurement?.status]);

  const preview = useMemo(() => (draft ? computePreview(draft) : null), [draft]);

  if (!measurement || !draft || !metadataDraft) {
    return (
      <section className="panel calculation-panel">
        <h2>계산 입력</h2>
        <div className="empty-state compact">계산할 Measurement 후보를 선택하세요.</div>
      </section>
    );
  }
  const currentMeasurement = measurement;
  const currentDraft = draft;
  const currentMetadataDraft = metadataDraft;
  const isReadOnly = currentMeasurement.status === "CONFIRMED" || currentMeasurement.status === "REJECTED";
  const allowedCalculationTypes = allowedCalculationTypesByMeasurementType[currentMetadataDraft.measurementType];

  function updateDraft(patch: Partial<CalculationDraft>) {
    setDraft((current) => (current ? { ...current, ...patch } : current));
    setMessage(null);
    setError(null);
  }

  function updateMetadataDraft(patch: Partial<MetadataDraft>) {
    setMetadataDraft((current) => (current ? { ...current, ...patch } : current));
    setMessage(null);
    setError(null);
  }

  function handleMeasurementTypeChange(nextType: MeasurementType) {
    const nextAllowedTypes = allowedCalculationTypesByMeasurementType[nextType];
    updateMetadataDraft({ measurementType: nextType, unit: measurementUnits[nextType] });
    updateDraft({ customUnit: measurementUnits[nextType] });
    if (!nextAllowedTypes.includes(currentDraft.calculationType)) {
      updateDraft({
        calculationType: nextAllowedTypes[0],
        deductions: [],
        sideCount: "1",
      });
    }
  }

  async function saveMetadataDraft() {
    if (isReadOnly) throw new Error("확정된 행은 재검토 시작 후 수정할 수 있습니다.");
    if (!currentMetadataDraft.category.trim()) {
      throw new Error("Category를 입력해 주세요.");
    }
    if (!currentMetadataDraft.finishCode.trim()) {
      throw new Error("Code를 입력해 주세요.");
    }
    const invalidatesCalculation = hasInvalidStoredQuantity(currentMeasurement)
      || currentMetadataDraft.measurementType !== currentMeasurement.measurement_type
      || currentMetadataDraft.unit.trim() !== currentMeasurement.unit;
    const saved = await updateMeasurement(currentMeasurement.id, {
      category: currentMetadataDraft.category.trim(),
      finish_code: currentMetadataDraft.finishCode.trim(),
      measurement_type: currentMetadataDraft.measurementType,
      unit: currentMetadataDraft.unit.trim() || null,
      memo: currentMetadataDraft.memo.trim() || null,
      ...(invalidatesCalculation ? { quantity: null, formula: null } : {}),
    });
    onSaved(saved);
    return saved;
  }

  async function handleMetadataSave() {
    setIsSavingMetadata(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await saveMetadataDraft();
      setMessage(`Measurement ${saved.id} 후보 정보 저장 완료`);
    } catch (caught) {
      setError(caught);
    } finally {
      setIsSavingMetadata(false);
    }
  }

  function updateDeduction(id: string, patch: Partial<DeductionDraft>) {
    updateDraft({
      deductions: currentDraft.deductions.map((deduction) => (deduction.id === id ? { ...deduction, ...patch } : deduction)),
    });
  }

  async function startReview() {
    setIsSaving(true);
    setError(null);
    try {
      onSaved(await updateMeasurement(currentMeasurement.id, { status: "DRAFT" }));
    } catch (caught) {
      setError(caught);
    } finally {
      setIsSaving(false);
    }
  }

  function addDeduction() {
    updateDraft({
      deductions: [
        ...currentDraft.deductions,
        {
          id: crypto.randomUUID(),
          label: "",
          amount: "",
          formula: "",
        },
      ],
    });
  }

  function removeDeduction(id: string) {
    updateDraft({
      deductions: currentDraft.deductions.filter((deduction) => deduction.id !== id),
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const currentPreview = computePreview(currentDraft);
    if (!currentPreview.ready) {
      setError(new Error(currentPreview.message));
      return;
    }

    setIsSaving(true);
    try {
      const metadataSaved = await saveMetadataDraft();
      const calculated = await calculateMeasurement(metadataSaved.id, buildCalculationPayload(currentDraft));
      const saved = confirmAfterSave ? await updateMeasurement(calculated.id, { status: "CONFIRMED" }) : calculated;
      onSaved(saved);
      setMessage(
        `Measurement ${saved.id} 저장 완료: ${displayNumber(Number(saved.quantity ?? currentPreview.quantity))} ${saved.unit ?? currentPreview.unit}`,
      );
    } catch (caught) {
      setError(caught);
    } finally {
      setIsSaving(false);
    }
  }

  const showWidthHeight = currentDraft.calculationType === "AREA_RECTANGLE" || currentDraft.calculationType === "PERIMETER_RECTANGLE";
  const showLengthHeight = currentDraft.calculationType === "WALL_AREA" || currentDraft.calculationType === "PARTITION_AREA";
  const showDeductions = currentDraft.calculationType === "AREA_RECTANGLE" ||
    currentDraft.calculationType === "PERIMETER_RECTANGLE" ||
    currentDraft.calculationType === "WALL_AREA" ||
    currentDraft.calculationType === "PARTITION_AREA";

  return (
    <section className="panel calculation-panel">
      <div className="section-heading">
        <div>
          <h2>계산 입력</h2>
          <p className="section-note">
            #{currentMeasurement.id} {currentMeasurement.room_no ?? "-"} {currentMeasurement.category} / {currentMeasurement.finish_code}
          </p>
        </div>
        <StatusBadge status={currentMeasurement.status} />
      </div>

      {currentMeasurement.status === "CONFIRMED" ? (
        <div className="message message-warning">
          확정된 행은 읽기 전용입니다. 수정하려면 재검토를 시작하세요.
          <button type="button" onClick={startReview} disabled={isSaving}>재검토 시작</button>
        </div>
      ) : currentMeasurement.status === "REJECTED" ? <p>거절된 행은 읽기 전용입니다.</p> : null}

      {showEvidence && <ReviewEvidencePanel measurement={currentMeasurement}/>}

      <fieldset disabled={isReadOnly || isSaving || isSavingMetadata} className="integrity-fieldset">
      <div className="metadata-editor">
        <div className="section-heading compact-heading">
          <h3>후보 정보</h3>
          <button type="button" className="button-secondary" disabled={isSavingMetadata || isSaving} onClick={handleMetadataSave}>
            {isSavingMetadata ? "저장 중" : "후보 정보 저장"}
          </button>
        </div>
        <div className="field-row two">
          <label>
            <span>Category</span>
            <input value={currentMetadataDraft.category} onChange={(event) => updateMetadataDraft({ category: event.target.value })} />
          </label>
          <label>
            <span>Code</span>
            <input value={currentMetadataDraft.finishCode} onChange={(event) => updateMetadataDraft({ finishCode: event.target.value })} />
          </label>
        </div>
        <div className="field-row two">
          <label>
            <span>Measurement Type</span>
            <select value={currentMetadataDraft.measurementType} onChange={(event) => handleMeasurementTypeChange(event.target.value as MeasurementType)}>
              {measurementTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Unit</span>
            <input value={currentMetadataDraft.unit} readOnly />
          </label>
        </div>
        <label>
          <span>Memo</span>
          <input value={currentMetadataDraft.memo} onChange={(event) => updateMetadataDraft({ memo: event.target.value })} />
        </label>
      </div>

      <form className="calculation-form" onSubmit={handleSubmit}>
        <label>
          <span>Calculation Type</span>
          <select
            value={currentDraft.calculationType}
            onChange={(event) =>
              updateDraft({
                calculationType: event.target.value as CalculationType,
                deductions: [],
              })
            }
          >
            {allowedCalculationTypes.map((type) => (
              <option key={type} value={type}>
                {calculationTypeLabels[type]}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Source Sheets</span>
          <input value={currentDraft.sourceSheets} onChange={(event) => updateDraft({ sourceSheets: event.target.value })} />
        </label>

        {showWidthHeight ? (
          <div className="field-row two">
            <label>
              <span>Width (m)</span>
              <input value={currentDraft.width} inputMode="decimal" onChange={(event) => updateDraft({ width: event.target.value })} />
            </label>
            <label>
              <span>Height (m)</span>
              <input value={currentDraft.height} inputMode="decimal" onChange={(event) => updateDraft({ height: event.target.value })} />
            </label>
          </div>
        ) : null}

        {showLengthHeight ? (
          <div className="field-row two">
            <label>
              <span>Length (m)</span>
              <input value={currentDraft.length} inputMode="decimal" onChange={(event) => updateDraft({ length: event.target.value })} />
            </label>
            <label>
              <span>Height (m)</span>
              <input value={currentDraft.height} inputMode="decimal" onChange={(event) => updateDraft({ height: event.target.value })} />
            </label>
          </div>
        ) : null}

        {currentDraft.calculationType === "PARTITION_AREA" ? (
          <label>
            <span>Side Count</span>
            <input value={currentDraft.sideCount} inputMode="decimal" onChange={(event) => updateDraft({ sideCount: event.target.value })} />
          </label>
        ) : null}

        {currentDraft.calculationType === "COUNT" ? (
          <label>
            <span>Count</span>
            <input value={currentDraft.count} inputMode="decimal" onChange={(event) => updateDraft({ count: event.target.value })} />
          </label>
        ) : null}

        {currentDraft.calculationType === "CUSTOM" ? (
          <>
            <label>
              <span>Formula</span>
              <input value={currentDraft.customFormula} onChange={(event) => updateDraft({ customFormula: event.target.value })} />
            </label>
            <div className="field-row two">
              <label>
                <span>Quantity</span>
                <input
                  value={currentDraft.customQuantity}
                  inputMode="decimal"
                  onChange={(event) => updateDraft({ customQuantity: event.target.value })}
                />
              </label>
              <label>
                <span>Unit</span>
                  <input value={currentDraft.customUnit} readOnly />
              </label>
            </div>
          </>
        ) : null}

        {showDeductions ? (
          <div className="deduction-editor">
            <div className="section-heading compact-heading">
              <h3>Deductions</h3>
              <button type="button" className="button-secondary" onClick={addDeduction}>
                공제 추가
              </button>
            </div>
            {currentDraft.deductions.length ? (
              <div className="deduction-list">
                {currentDraft.deductions.map((deduction) => (
                  <div className="deduction-row" key={deduction.id}>
                    <input
                      aria-label="Deduction label"
                      placeholder="label"
                      value={deduction.label}
                      onChange={(event) => updateDeduction(deduction.id, { label: event.target.value })}
                    />
                    <input
                      aria-label="Deduction amount"
                      placeholder="amount"
                      inputMode="decimal"
                      value={deduction.amount}
                      onChange={(event) => updateDeduction(deduction.id, { amount: event.target.value })}
                    />
                    <input
                      aria-label="Deduction formula"
                      placeholder="formula"
                      value={deduction.formula}
                      onChange={(event) => updateDeduction(deduction.id, { formula: event.target.value })}
                    />
                    <button type="button" className="button-secondary" onClick={() => removeDeduction(deduction.id)}>
                      삭제
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state compact">공제가 없으면 추가하지 않아도 됩니다.</div>
            )}
          </div>
        ) : null}

        <div className="calculation-preview">
          <span className="tool-label">미리보기</span>
          {preview?.ready ? (
            <>
              <strong>
                {displayNumber(preview.quantity)} {preview.unit}
              </strong>
              <span>{preview.formula}</span>
            </>
          ) : (
            <span>{preview?.message ?? "입력값을 넣으면 계산 결과가 표시됩니다."}</span>
          )}
        </div>

        <label className="checkbox-label">
          <input type="checkbox" checked={confirmAfterSave} onChange={(event) => setConfirmAfterSave(event.target.checked)} />
          <span>저장 후 CONFIRMED로 확정</span>
        </label>

        <div className="button-row">
          <button type="submit" disabled={isSaving || !preview?.ready}>
            {isSaving ? "저장 중" : "계산 저장"}
          </button>
        </div>
      </form>
      </fieldset>

      <ErrorMessage error={error} />
      {message ? <div className="message message-success">{message}</div> : null}
    </section>
  );
}
