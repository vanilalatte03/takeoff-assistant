import { FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createProject, listProjects, uploadDrawingFile } from "../api/client";
import { ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import type { Project } from "../types/api";

export function UploadPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<unknown>(null);
  const active = useRef(false);
  const running = useRef(false);
  useEffect(() => {
    let cancelled = false;
    active.current = true;
    listProjects().then(loaded => {
      if (!cancelled) {
        // A project can be created while this initial request is still in flight.
        setProjects(current => [...new Map([...loaded, ...current].map(p => [p.id, p])).values()]);
        setProjectId(old => old || String(loaded[0]?.id ?? ""));
      }
    }).catch(e => { if (!cancelled) setError(e); });
    return () => { cancelled = true; active.current = false; };
  }, []);
  async function run(label: string, action: () => Promise<void>) {
    if (running.current) return;
    running.current = true; setBusy(label); setError(null);
    try { await action(); } catch(e) { if (active.current) setError(e); }
    finally { running.current = false; if (active.current) setBusy(""); }
  }
  async function create(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    await run("프로젝트 생성", async () => {
      const created = await createProject({name: name.trim()});
      if (active.current) { setProjects(old => [...old, created]); setProjectId(String(created.id)); setName(""); }
    });
  }
  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || !projectId) return;
    await run("PDF 업로드", async () => {
      const uploaded = await uploadDrawingFile(Number(projectId), file);
      if (active.current) {
        sessionStorage.setItem("takeoff.drawingFileId", String(uploaded.id));
        navigate(`/workflow?drawingFileId=${uploaded.id}`);
      }
    });
  }
  return <>
    <PageHeader title="PDF 업로드" description="프로젝트를 고르고 PDF를 올리면 도면 준비부터 Excel까지 이어서 진행합니다." />
    <p><Link to="/workflow">이미 올린 PDF로 이어서 작업하기</Link></p>
    <section className="panel"><h2>프로젝트 선택 또는 만들기</h2>
      <label><span>프로젝트</span><select value={projectId} disabled={!!busy || !projects.length} onChange={e => {setProjectId(e.target.value);setError(null);}}>
        {!projects.length && <option value="">프로젝트를 먼저 만드세요</option>}
        {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select></label>
      <form className="toolbar-form" onSubmit={create}><label><span>새 프로젝트 이름</span><input value={name} disabled={!!busy} onChange={e => setName(e.target.value)} required /></label><button disabled={!!busy || !name.trim()}>프로젝트 만들기</button></form>
    </section>
    <section className="panel"><h2>작업할 PDF 올리기</h2>
      <form className="form-grid" onSubmit={upload}><label><span>PDF 파일</span><input type="file" accept="application/pdf,.pdf" disabled={!!busy} onChange={e => {setFile(e.target.files?.[0] ?? null);setError(null);}} /></label>
        <button disabled={!!busy || !file || !projectId}>{busy || "PDF 올리고 작업 시작"}</button>
      </form><ErrorMessage error={error} />
      {!!error && <p>원인을 확인한 뒤 같은 버튼으로 재시도하세요. 이미 업로드된 PDF는 작업 시작 화면에서 재개할 수 있습니다.</p>}
    </section>
  </>;
}
