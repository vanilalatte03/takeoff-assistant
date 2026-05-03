import type { ReactNode } from "react";

import { ApiError } from "../api/client";

export function ErrorMessage({ error }: { error: unknown }) {
  if (!error) {
    return null;
  }

  const message = error instanceof ApiError ? `${error.status}: ${error.message}` : String(error);
  return (
    <div className="message message-error" role="alert">
      {message}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}
