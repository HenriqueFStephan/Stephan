export interface StudioApiBlock {
  type: 'text' | 'image';
  text?: string;
  name?: string;
  mime?: string;
  data_base64?: string;
}

export interface StudioIssuePayload {
  title: string;
  blocks: StudioApiBlock[];
}

export interface StudioIssueResponse {
  success: boolean;
  issue_url: string;
  issue_number: number;
  message: string;
}

export interface StudioStatusResponse {
  configured: boolean;
  missing: string[];
}

export interface StudioUnlockResponse {
  success: boolean;
  message: string;
}

export interface ApiStatus {
  status: string;
  version: string;
  environment: string;
  smtp_configured: boolean;
  studio_configured: boolean;
}
