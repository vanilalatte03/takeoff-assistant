import { FormEvent, useEffect, useMemo, useState } from "react";

import { calculateMeasurement, updateMeasurement } from "../api/client";
import type { CalculationType, Measurement, MeasurementCalculationInput } from "../types/api";
import { ErrorMessage } from "./ApiState";
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

const calculationTypes: CalculationType[] = [
  "AREA_RECTANGLE",
  "PERIMETER_RECTANGLE",
  "WALL_AREA",
  "PARTITION_AREA",
  "COUNT",
  "CUSTOM",
];

const calculationTypeLabels: Record<CalculationType, string> = {
  AREA_RECTANGLE: "사각형 면적",
  PERIMETER_RECTANGLE: "사각형 둘레",
  WALL_AREA: "벽체 면적",
  PARTITION_AREA: "파티션 면적",
  COUNT: "개수",
  CUSTOM: "직접 입력",
};

interface MeasurementCalculationFormProps {
  measurement: Measurement | null;
  onSaved: (measurement: Measurement) => void;
}

function defaultCalculationType(measurement: Measurement): CalculationType {
  if (measurement.measurement_type === "PERIMETER_LENGTH") {
    return "PERIMETER_RECTANGLE";
  }
  if (measurement.measurement_type === "WALL_AREA") {
    return "WALL_AREA";
  }
  if (measurement.measurement_type === "PARTITION_AREA") {
    return "PARTITION_AREA";
  }
  if (measurement.measurement_type === "COUNT") {
    return "COUNT";
  }
  return "AREA_RECTANGLE";
}

function createDraft(measurement: Measurement): CalculationDraft {
  return {
    calculationType: defaultCalculationType(measurement),
    width: "",
    height: "",
    length: "",
    sideCount: measurement.measurement_type === "PARTITION_AREA" ? "2" : "1",
    count: "",
    customFormula: measurement.formula ?? "",
    customQuantity: measurement.quantity === null ? "" : String(measurement.quantity),
    customUnit: measurement.unit ?? "",
    sourceSheets: measurement.source_sheets,
    deductions: [],
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
        formula: `${formulaNumber(draft.width)} * ${formulaNumber(draft.height)}`,
        quantity: round2(width * height),
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

export function MeasurementCalculationForm({ measurement, onSaved }: MeasurementCalculationFormProps) {
  const [draft, setDraft] = useState<CalculationDraft | null>(measurement ? createDraft(measurement) : null);
  const [confirmAfterSave, setConfirmAfterSave] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setDraft(measurement ? createDraft(measurement) : null);
    setConfirmAfterSave(false);
    setMessage(null);
    setError(null);
  }, [measurement?.id]);

  const preview = useMemo(() => (draft ? computePreview(draft) : null), [draft]);

  if (!measurement || !draft) {
    return (
      <section className="panel calculation-panel">
        <h2>계산 입력</h2>
        <div className="empty-state compact">계산할 Measurement 후보를 선택하세요.</div>
      </section>
    );
  }
  const currentMeasurement = measurement;
  const currentDraft = draft;

  function updateDraft(patch: Partial<CalculationDraft>) {
    setDraft((current) => (current ? { ...current, ...patch } : current));
    setMessage(null);
    setError(null);
  }

  function updateDeduction(id: string, patch: Partial<DeductionDraft>) {
    updateDraft({
      deductions: currentDraft.deductions.map((deduction) => (deduction.id === id ? { ...deduction, ...patch } : deduction)),
    });
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
      const calculated = await calculateMeasurement(currentMeasurement.id, buildCalculationPayload(currentDraft));
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
  const showDeductions =
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
            {calculationTypes.map((type) => (
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
                <input value={currentDraft.customUnit} onChange={(event) => updateDraft({ customUnit: event.target.value })} />
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

      <ErrorMessage error={error} />
      {message ? <div className="message message-success">{message}</div> : null}
    </section>
  );
}
