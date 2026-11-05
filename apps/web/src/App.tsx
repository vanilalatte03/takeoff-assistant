import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { DrawingDetailPage } from "./pages/DrawingDetailPage";
import { MeasurementsPage } from "./pages/MeasurementsPage";
import { RoomFinishesPage } from "./pages/RoomFinishesPage";
import { SheetsPage } from "./pages/SheetsPage";
import { UploadPage } from "./pages/UploadPage";
import { AssistPage } from "./pages/AssistPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/upload" replace />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/assist" element={<AssistPage />} />
        <Route path="/drawings" element={<SheetsPage />} />
        <Route path="/drawings/:drawingFileId/pages/:pageIndex" element={<DrawingDetailPage />} />
        <Route path="/room-finishes" element={<RoomFinishesPage />} />
        <Route path="/measurements" element={<MeasurementsPage />} />
        <Route path="*" element={<Navigate to="/upload" replace />} />
      </Route>
    </Routes>
  );
}
