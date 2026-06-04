import type { SelectedTag } from "../components/TagPicker";
import type { ProblemDraft } from "../components/ProblemDraftEditor";

export interface SourceOption {
  id: number;
  slug: string;
  name: string;
  parentId?: number | null;
  order?: number;
  depth?: number;
}

export interface CreateSourceResponse {
  source?: SourceOption;
  error?: string;
}

export interface TranscribedProblem {
  source_md: string;
  source_key?: string;
  problem_label?: string;
}

export type Step =
  | "upload"
  | "pages"
  | "transcribing"
  | "review"
  | "confirm"
  | "saving";

export type JobStatus = "pending" | "running" | "done" | "failed" | "cancelled";
export type ProgressStepStatus = "pending" | "running" | "done" | "failed";

export interface JobProgressStep {
  key: string;
  label: string;
  status: ProgressStepStatus;
}

export interface JobProgress {
  current?: string | null;
  steps: JobProgressStep[];
}

export interface JobResponse {
  id: string;
  status: JobStatus;
  created_at?: string;
  updated_at?: string;
  error?: string;
  progress?: JobProgress;
  has_original_pdf?: boolean;
  year?: number | null;
  language?: string | null;
  problems?: TranscribedProblem[];
  images?: Record<string, string>;
}

export interface WizardDraft {
  problems: ProblemDraft[];
  /** 1-based page numbers. */
  pages: number[];
  sourceId: string;
  year: string;
  language: string;
  globalTags: SelectedTag[];
  documentSourceUrl: string;
}
