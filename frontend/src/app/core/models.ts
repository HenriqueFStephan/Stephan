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

export interface ContactPayload {
  name: string;
  organization?: string;
  email: string;
  message: string;
}

export interface ContactResponse {
  success: boolean;
  message: string;
}

export interface OrderPayload {
  legal_name: string;
  trade_name: string;
  cnpj: string;
  municipal_registration: string;
  nfe_email: string;
  phone: string;
  postal_code: string;
  street: string;
  number: string;
  complement: string;
  district: string;
  city: string;
  state: string;
  headcount: number;
  sites: number;
  activity: string;
  rep_name: string;
  rep_cpf: string;
  rep_role: string;
  rep_email: string;
  rep_phone: string;
  contact_name: string;
  contact_role: string;
  contact_email: string;
  contact_phone: string;
  accept_contract: boolean;
  privacy_ack: boolean;
  marketing: boolean;
  method: 'pix' | 'boleto' | 'card';
  installments: number;
  summary_ack: boolean;
  quoted_price_cents: number | null;
}

export interface OrderResponse {
  success: boolean;
  reference: string;
  charged: boolean;
}

export interface BlockwallStatus {
  enabled: boolean;
}

export interface BlockwallUnlockResponse {
  success: boolean;
  passage: string;
}

export interface CompanyLoginResponse {
  success: boolean;
  passage: string;
  company_slug: string;
  company_name: string;
}

export interface ToolDraft {
  place: 'profile' | 'ask';
  index: number;
  demographics: Record<string, string>;
  answers: (number | null)[];
}

export interface ToolAccessResult {
  state: string;
  draft: ToolDraft | null;
}

export interface ToolSubmitResult {
  saved: boolean;
}

export interface CompanyAlphaRow {
  id: string;
  alpha: number | null;
  items: number;
  n: number;
  reading: string;
  mean: number | null;
}

export interface CompanyDimensionRow {
  id: string;
  mean: number;
}

export interface CompanySectorRow {
  id: string;
  count: number;
  means: { id: string; mean: number }[];
}

export interface CompanyWeekRow {
  week: string;
  count: number;
}

export interface CompanyBandRow {
  id: string;
  urgent: number;
  improve: number;
  good: number;
  maintain: number;
}

export interface InvitationUploadResult {
  round_label: string;
  accepted: number;
  ignored_empty: number;
  duplicates_in_file: string[];
  already_invited: string[];
  invalid: string[];
  not_sent: string[];
}

export interface InvitationRoster {
  round_label: string;
  invited: number;
  responded_percent: number | null;
  waiting_percent: number | null;
}

export interface CompanyOverview {
  source: string;
  company_id: string;
  respondent_count: number;
  first_response_on: string;
  latest_response_on: string;
  alpha: CompanyAlphaRow[];
  dimensions: CompanyDimensionRow[];
  sectors: CompanySectorRow[];
  weeks: CompanyWeekRow[];
  bands: CompanyBandRow[];
}

export interface ApiStatus {
  status: string;
  version: string;
  environment: string;
  smtp_configured: boolean;
  studio_configured: boolean;
}
