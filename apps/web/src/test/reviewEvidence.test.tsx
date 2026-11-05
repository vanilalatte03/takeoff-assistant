import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { ReviewEvidencePanel } from "../components/ReviewEvidencePanel";
import * as api from "../api/client";
import type { Measurement } from "../types/api";

vi.mock("../api/client", async importOriginal => ({
  ...await importOriginal<typeof import("../api/client")>(),
  getReviewEvidence: vi.fn(), updateMeasurement: vi.fn(),
}));
const row = {id:1,formula:"4.2 * 2.7",quantity:"11.34",unit:"m2",status:"DRAFT"} as Measurement;
beforeEach(()=>vi.clearAllMocks());

it("shows the stored conversion and switches source pages without changing the measurement", async()=>{
  vi.mocked(api.getReviewEvidence).mockResolvedValue({
    measurement_id:1,room_no:"110",finish_code:"ACST",formula:row.formula,quantity:"11.34",unit:"m2",status:"DRAFT",
    inputs:[{name:"width",raw_value:"4200",unit:"mm",normalized_value:"4.2",normalized_unit:"m",source_sheet_id:2,note:"Verified source",method:"manual"}],
    sources:[1,2].map(id=>({sheet_id:id,drawing_file_id:9,page_index:id-1,sheet_no:`ZX${id}`,sheet_title:"Synthetic",quote:"",method:"text",changed_since_saved:false})),
    side_multiplier:null,deductions:[],deductions_reviewed:true,warnings:[],
  });
  render(<MemoryRouter><ReviewEvidencePanel measurement={row}/></MemoryRouter>);
  expect(await screen.findByText("4.2 m")).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"가로 출처 보기"}));
  expect(screen.getByRole("img").getAttribute("src")).toContain("/drawing-files/9/pages/1/image");
  expect(api.updateMeasurement).not.toHaveBeenCalled();
});

it("reports a failed evidence request without inventing inputs", async()=>{
  vi.mocked(api.getReviewEvidence).mockRejectedValue(new Error("Evidence unavailable"));
  render(<MemoryRouter><ReviewEvidencePanel measurement={row}/></MemoryRouter>);
  expect((await screen.findByRole("alert")).textContent).toContain("Evidence unavailable");
  expect(screen.queryByRole("img")).toBeNull();
  expect(api.updateMeasurement).not.toHaveBeenCalled();
});
