import type { ReviewStatus } from "../types/api";

const statusLabels: Record<ReviewStatus, string> = {
  DRAFT: "Draft",
  NEEDS_REVIEW: "Needs review",
  CONFIRMED: "Confirmed",
  REJECTED: "Rejected",
};

export function StatusBadge({ status }: { status: ReviewStatus }) {
  return <span className={`status-badge status-${status.toLowerCase().replace("_", "-")}`}>{statusLabels[status]}</span>;
}
