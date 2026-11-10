import type { ReviewStatus } from "../types/api";

export const statusLabels: Record<ReviewStatus, string> = {
  DRAFT: "초안",
  NEEDS_REVIEW: "검토 필요",
  CONFIRMED: "확정",
  REJECTED: "거절",
};

export function StatusBadge({ status }: { status: ReviewStatus }) {
  return <span className={`status-badge status-${status.toLowerCase().replace("_", "-")}`}>{statusLabels[status]}</span>;
}
