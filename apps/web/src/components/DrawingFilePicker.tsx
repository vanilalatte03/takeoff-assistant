import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { listProjects, listProjectDrawingFiles } from "../api/client";
import type { DrawingFile, Project } from "../types/api";
import { ErrorMessage } from "./ApiState";

const selectionKey = "takeoff.drawingFileId";

export function useDrawingFileSelection(): [string, (value: string) => void] {
  const [params, setParams] = useSearchParams();
  const value = params.get("drawingFileId") ?? sessionStorage.getItem(selectionKey) ?? "";
  function select(next: string) {
    sessionStorage.setItem(selectionKey, next);
    const updated = new URLSearchParams(params);
    if (next) updated.set("drawingFileId", next);
    else updated.delete("drawingFileId");
    setParams(updated, { replace: true });
  }
  useEffect(() => { sessionStorage.setItem(selectionKey, value); }, [value]);
  return [value, select];
}

export function DrawingFilePicker({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [files, setFiles] = useState<DrawingFile[]>([]);
  const [projectId, setProjectId] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const loadedProjects = await listProjects();
        const loadedFiles = (await Promise.all(loadedProjects.map(p => listProjectDrawingFiles(p.id)))).flat();
        if (!active) return;
        setProjects(loadedProjects);
        setFiles(loadedFiles);
        setProjectId(String(loadedProjects[0]?.id ?? ""));
      } catch (e) {
        if (active) setError(e);
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (loading || error) return;
    const selected = files.find(f => String(f.id) === value);
    if (selected) setProjectId(String(selected.project_id));
    else if (value) onChange("");
  }, [value, files, loading, error, onChange]);
  return <>
    <label><span>프로젝트</span><select aria-label="프로젝트" value={projectId} disabled={loading} onChange={e => {
      setProjectId(e.target.value);
      onChange("");
    }}>
      {!projects.length && <option value="">프로젝트가 없습니다</option>}
      {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
    </select></label>
    <label><span>도면 PDF</span><select aria-label="도면 PDF" value={value} disabled={loading || !!error} onChange={e => onChange(e.target.value)}>
      <option value="">{loading ? "도면 불러오는 중…" : "도면을 선택하세요"}</option>
      {files.filter(f => String(f.project_id) === projectId).map(f => <option key={f.id} value={f.id}>{f.original_filename} · {f.page_count}쪽 · {new Date(f.created_at).toLocaleString()}</option>)}
    </select></label>
    <ErrorMessage error={error} />
  </>;
}
