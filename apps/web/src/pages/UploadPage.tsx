import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  classifyDrawingSheets,
  createProject,
  detectDrawingSheets,
  listProjects,
  processDrawingPages,
  uploadDrawingFile,
} from "../api/client";
import { ErrorMessage } from "../components/ApiState";
import { PageHeader } from "../components/PageHeader";
import type { DrawingFile, Project } from "../types/api";

type UploadStep = "upload" | "process" | "detect" | "classify";

const stepLabels: Record<UploadStep, string> = {
  upload: "Upload",
  process: "Process pages",
  detect: "Detect sheets",
  classify: "Classify sheets",
};

function toPositiveInteger(value: string, label: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${label} must be a positive integer.`);
  }
  return parsed;
}

export function UploadPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [drawingFile, setDrawingFile] = useState<DrawingFile | null>(null);
  const [pendingStep, setPendingStep] = useState<UploadStep | "project" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    listProjects()
      .then((loaded) => {
        setProjects(loaded);
        setProjectId((current) => current || (loaded[0] ? String(loaded[0].id) : ""));
      })
      .catch(setError);
  }, []);

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (!newProjectName.trim()) {
      setError(new Error("Project name is required."));
      return;
    }

    setPendingStep("project");
    try {
      const created = await createProject({
        name: newProjectName.trim(),
        description: newProjectDescription.trim() || null,
      });
      setProjects((current) => [...current, created]);
      setProjectId(String(created.id));
      setNewProjectName("");
      setNewProjectDescription("");
      setMessage(`Project created: ${created.name}`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingStep(null);
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    try {
      if (!file) {
        throw new Error("Choose a PDF file to upload.");
      }
      setPendingStep("upload");
      const uploaded = await uploadDrawingFile(toPositiveInteger(projectId, "Project ID"), file);
      setDrawingFile(uploaded);
      setMessage(`Uploaded: ${uploaded.original_filename}`);
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingStep(null);
    }
  }

  async function runStep(step: Exclude<UploadStep, "upload">) {
    if (!drawingFile) {
      return;
    }

    setError(null);
    setMessage(null);
    setPendingStep(step);
    try {
      if (step === "process") {
        const result = await processDrawingPages(drawingFile.id);
        setDrawingFile({ ...drawingFile, page_count: result.page_count });
        setMessage(`Processed ${result.page_count} pages.`);
      }
      if (step === "detect") {
        const result = await detectDrawingSheets(drawingFile.id);
        setMessage(`Detected ${result.sheets.length} sheets.`);
      }
      if (step === "classify") {
        const result = await classifyDrawingSheets(drawingFile.id);
        setMessage(`Classified ${result.sheets.length} sheets.`);
      }
    } catch (caught) {
      setError(caught);
    } finally {
      setPendingStep(null);
    }
  }

  return (
    <>
      <PageHeader
        title="PDF Upload"
        description="Select or create a project, upload a drawing PDF, then process and classify sheets for takeoff."
      />

      <section className="panel">
        <div className="section-heading">
          <h2>Project</h2>
          <span className="count-label">{projects.length} projects</span>
        </div>
        <form className="project-create-grid" onSubmit={handleCreateProject}>
          <label>
            <span>Project</span>
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)} disabled={!projects.length}>
              {projects.length ? (
                projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name} (#{project.id})
                  </option>
                ))
              ) : (
                <option value="">No projects</option>
              )}
            </select>
          </label>
          <label>
            <span>New project name</span>
            <input value={newProjectName} onChange={(event) => setNewProjectName(event.target.value)} />
          </label>
          <label>
            <span>Description</span>
            <input value={newProjectDescription} onChange={(event) => setNewProjectDescription(event.target.value)} />
          </label>
          <button type="submit" className="button-secondary" disabled={pendingStep !== null}>
            {pendingStep === "project" ? "Creating..." : "Create project"}
          </button>
        </form>
      </section>

      <section className="panel">
        <form className="form-grid" onSubmit={handleUpload}>
          <label>
            <span>Project ID</span>
            <input value={projectId} inputMode="numeric" onChange={(event) => setProjectId(event.target.value)} />
          </label>
          <label className="file-input">
            <span>PDF file</span>
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={pendingStep !== null || !projectId}>
              {pendingStep === "upload" ? "Uploading..." : "Upload PDF"}
            </button>
          </div>
        </form>

        <ErrorMessage error={error} />
        {message ? <div className="message message-success">{message}</div> : null}
      </section>

      {drawingFile ? (
        <section className="panel">
          <div className="section-heading">
            <h2>Uploaded drawing</h2>
            <Link className="button button-secondary" to={`/drawings?drawingFileId=${drawingFile.id}`}>
              Open sheets
            </Link>
          </div>
          <dl className="metadata-grid">
            <div>
              <dt>Filename</dt>
              <dd>{drawingFile.original_filename}</dd>
            </div>
            <div>
              <dt>Drawing File ID</dt>
              <dd>{drawingFile.id}</dd>
            </div>
            <div>
              <dt>Pages</dt>
              <dd>{drawingFile.page_count}</dd>
            </div>
            <div>
              <dt>Uploaded</dt>
              <dd>{new Date(drawingFile.created_at).toLocaleString()}</dd>
            </div>
          </dl>
          <div className="button-row">
            {(["process", "detect", "classify"] as const).map((step) => (
              <button
                key={step}
                type="button"
                className="button-secondary"
                disabled={pendingStep !== null}
                onClick={() => runStep(step)}
              >
                {pendingStep === step ? `${stepLabels[step]}...` : stepLabels[step]}
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
