import { OrderPayload } from '../../core/models';
import { BRAZIL_STATES, isCnpj, isCpf, isEmail, isPhone, onlyDigits } from './br-docs';
import { isPlanId } from './plans';

const DRAFT_KEY = 'stephan-billing-draft';
const RECEIPT_KEY = 'stephan-billing-receipt';

export interface BillingDraft {
  legalName: string;
  tradeName: string;
  cnpj: string;
  municipalRegistration: string;
  nfeEmail: string;
  phone: string;
  postalCode: string;
  street: string;
  number: string;
  complement: string;
  district: string;
  city: string;
  state: string;
  headcount: string;
  sites: string;
  activity: string;
  repName: string;
  repCpf: string;
  repRole: string;
  repEmail: string;
  repPhone: string;
  sameContact: boolean;
  contactName: string;
  contactRole: string;
  contactEmail: string;
  contactPhone: string;
  acceptContract: boolean;
  privacyAck: boolean;
  marketing: boolean;
  method: '' | 'pix' | 'boleto' | 'card';
  installments: number;
  summaryAck: boolean;
  plan: '' | 'hse' | 'analise';
}

export interface BillingReceipt {
  reference: string;
  company: string;
  quotedCents: number | null;
  plan: string;
}

export type DraftErrors = Partial<Record<keyof BillingDraft, string>>;

export function emptyDraft(): BillingDraft {
  return {
    legalName: '',
    tradeName: '',
    cnpj: '',
    municipalRegistration: '',
    nfeEmail: '',
    phone: '',
    postalCode: '',
    street: '',
    number: '',
    complement: '',
    district: '',
    city: '',
    state: '',
    headcount: '',
    sites: '',
    activity: '',
    repName: '',
    repCpf: '',
    repRole: '',
    repEmail: '',
    repPhone: '',
    sameContact: true,
    contactName: '',
    contactRole: '',
    contactEmail: '',
    contactPhone: '',
    acceptContract: false,
    privacyAck: false,
    marketing: false,
    method: '',
    installments: 1,
    summaryAck: false,
    plan: '',
  };
}

function readJson<T>(key: string): T | null {
  if (typeof sessionStorage === 'undefined') return null;
  const raw = sessionStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function loadDraft(): BillingDraft | null {
  const stored = readJson<Partial<BillingDraft>>(DRAFT_KEY);
  if (!stored) return null;
  const merged = { ...emptyDraft(), ...stored, marketing: stored.marketing === true };
  if (!isPlanId(merged.plan)) merged.plan = '';
  return merged;
}

export function saveDraft(draft: BillingDraft): void {
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

export function clearDraft(): void {
  sessionStorage.removeItem(DRAFT_KEY);
}

export function loadReceipt(): BillingReceipt | null {
  return readJson<BillingReceipt>(RECEIPT_KEY);
}

export function saveReceipt(receipt: BillingReceipt): void {
  sessionStorage.setItem(RECEIPT_KEY, JSON.stringify(receipt));
}

export function clearReceipt(): void {
  sessionStorage.removeItem(RECEIPT_KEY);
}

function countOk(value: string, max: number): boolean {
  if (!/^\d+$/.test(value.trim())) return false;
  const parsed = Number(value);
  return parsed >= 1 && parsed <= max;
}

/** Copies the signer onto the operational contact when they are the same person. */
export function applySameContact(draft: BillingDraft): void {
  if (!draft.sameContact) return;
  draft.contactName = draft.repName;
  draft.contactRole = draft.repRole;
  draft.contactEmail = draft.repEmail;
  draft.contactPhone = draft.repPhone;
}

export function validateCadastro(draft: BillingDraft): DraftErrors {
  const errors: DraftErrors = {};
  const required: (keyof BillingDraft)[] = [
    'legalName', 'cnpj', 'nfeEmail', 'phone', 'postalCode', 'street', 'number',
    'district', 'city', 'state', 'headcount', 'sites', 'activity', 'repName',
    'repCpf', 'repRole', 'repEmail', 'repPhone',
  ];
  for (const key of required) {
    if (!String(draft[key]).trim()) errors[key] = 'bill.err.required';
  }
  if (!errors.cnpj && !isCnpj(draft.cnpj)) errors.cnpj = 'bill.err.cnpj';
  if (!errors.nfeEmail && !isEmail(draft.nfeEmail)) errors.nfeEmail = 'bill.err.email';
  if (!errors.phone && !isPhone(draft.phone)) errors.phone = 'bill.err.phone';
  if (!errors.postalCode && onlyDigits(draft.postalCode).length !== 8) errors.postalCode = 'bill.err.cep';
  if (!errors.state && !BRAZIL_STATES.includes(draft.state as (typeof BRAZIL_STATES)[number])) {
    errors.state = 'bill.err.required';
  }
  if (!errors.headcount && !countOk(draft.headcount, 1_000_000)) errors.headcount = 'bill.err.count';
  if (!errors.sites && !countOk(draft.sites, 10_000)) errors.sites = 'bill.err.count';
  if (!errors.repCpf && !isCpf(draft.repCpf)) errors.repCpf = 'bill.err.cpf';
  if (!errors.repEmail && !isEmail(draft.repEmail)) errors.repEmail = 'bill.err.email';
  if (!errors.repPhone && !isPhone(draft.repPhone)) errors.repPhone = 'bill.err.phone';
  if (!isPlanId(draft.plan)) errors.plan = 'bill.err.required';
  if (!draft.sameContact) {
    if (!draft.contactName.trim()) errors.contactName = 'bill.err.required';
    if (!draft.contactRole.trim()) errors.contactRole = 'bill.err.required';
    if (!draft.contactEmail.trim()) errors.contactEmail = 'bill.err.required';
    else if (!isEmail(draft.contactEmail)) errors.contactEmail = 'bill.err.email';
    if (!draft.contactPhone.trim()) errors.contactPhone = 'bill.err.required';
    else if (!isPhone(draft.contactPhone)) errors.contactPhone = 'bill.err.phone';
  }
  return errors;
}

export function validatePayment(draft: BillingDraft, plans: number[]): DraftErrors {
  const errors: DraftErrors = {};
  if (!draft.method) errors.method = 'bill.err.required';
  if (!draft.summaryAck) errors.summaryAck = 'bill.err.consent';
  if (!draft.acceptContract) errors.acceptContract = 'bill.err.consent';
  if (!draft.privacyAck) errors.privacyAck = 'bill.err.consent';
  if (draft.method === 'card' && plans.length > 1 && !plans.includes(draft.installments)) {
    errors.installments = 'bill.err.required';
  }
  return errors;
}

export function toOrderPayload(draft: BillingDraft, quotedCents: number): OrderPayload {
  applySameContact(draft);
  if (!isPlanId(draft.plan)) {
    throw new Error('plan required');
  }
  return {
    legal_name: draft.legalName.trim(),
    trade_name: draft.tradeName.trim(),
    cnpj: draft.cnpj.trim(),
    municipal_registration: draft.municipalRegistration.trim(),
    nfe_email: draft.nfeEmail.trim(),
    phone: draft.phone.trim(),
    postal_code: draft.postalCode.trim(),
    street: draft.street.trim(),
    number: draft.number.trim(),
    complement: draft.complement.trim(),
    district: draft.district.trim(),
    city: draft.city.trim(),
    state: draft.state.trim(),
    headcount: Number(draft.headcount),
    sites: Number(draft.sites),
    activity: draft.activity.trim(),
    rep_name: draft.repName.trim(),
    rep_cpf: draft.repCpf.trim(),
    rep_role: draft.repRole.trim(),
    rep_email: draft.repEmail.trim(),
    rep_phone: draft.repPhone.trim(),
    contact_name: draft.contactName.trim(),
    contact_role: draft.contactRole.trim(),
    contact_email: draft.contactEmail.trim(),
    contact_phone: draft.contactPhone.trim(),
    accept_contract: draft.acceptContract,
    privacy_ack: draft.privacyAck,
    marketing: draft.marketing,
    method: draft.method as 'pix' | 'boleto' | 'card',
    installments: 1,
    summary_ack: draft.summaryAck,
    plan: draft.plan,
    quoted_price_cents: quotedCents,
  };
}
