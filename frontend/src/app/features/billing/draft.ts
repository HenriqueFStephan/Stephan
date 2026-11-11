import { OrderPayload } from '../../core/models';
import { BRAZIL_STATES, isCnpj, isEmail, isPhone, onlyDigits } from './br-docs';
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
  cnae: string;
  activity: string;
  accessEmail: string;
  accessEmailConfirm: string;
  password: string;
  passwordConfirm: string;
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
  email?: string;
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
    cnae: '',
    activity: '',
    accessEmail: '',
    accessEmailConfirm: '',
    password: '',
    passwordConfirm: '',
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
  merged.password = '';
  merged.passwordConfirm = '';
  return merged;
}

export function saveDraft(draft: BillingDraft): void {
  const stored = { ...draft, password: '', passwordConfirm: '' };
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(stored));
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

export function validateCadastro(draft: BillingDraft): DraftErrors {
  const errors: DraftErrors = {};
  const required: (keyof BillingDraft)[] = [
    'legalName', 'cnpj', 'postalCode', 'street', 'number',
    'district', 'city', 'state', 'activity', 'accessEmail', 'accessEmailConfirm',
    'password', 'passwordConfirm',
  ];
  for (const key of required) {
    if (!String(draft[key]).trim()) errors[key] = 'bill.err.required';
  }
  if (!errors.cnpj && !isCnpj(draft.cnpj)) errors.cnpj = 'bill.err.cnpj';
  if (draft.nfeEmail.trim() && !isEmail(draft.nfeEmail)) errors.nfeEmail = 'bill.err.email';
  if (!errors.accessEmail && !isEmail(draft.accessEmail)) errors.accessEmail = 'bill.err.email';
  if (
    !errors.accessEmail &&
    !errors.accessEmailConfirm &&
    draft.accessEmail.trim().toLowerCase() !== draft.accessEmailConfirm.trim().toLowerCase()
  ) {
    errors.accessEmailConfirm = 'bill.err.emailMatch';
  }
  if (draft.phone.trim() && !isPhone(draft.phone)) errors.phone = 'bill.err.phone';
  if (!errors.postalCode && onlyDigits(draft.postalCode).length !== 8) errors.postalCode = 'bill.err.cep';
  if (!errors.state && !BRAZIL_STATES.includes(draft.state as (typeof BRAZIL_STATES)[number])) {
    errors.state = 'bill.err.required';
  }
  if (!errors.password && draft.password.length < 8) errors.password = 'bill.err.password';
  if (!errors.passwordConfirm && draft.password !== draft.passwordConfirm) {
    errors.passwordConfirm = 'bill.err.passwordMatch';
  }
  return errors;
}

export function toOrderPayload(draft: BillingDraft): OrderPayload {
  return {
    legal_name: draft.legalName.trim(),
    trade_name: draft.tradeName.trim(),
    cnpj: draft.cnpj.trim(),
    municipal_registration: draft.municipalRegistration.trim(),
    nfe_email: draft.nfeEmail.trim() || draft.accessEmail.trim(),
    phone: draft.phone.trim(),
    postal_code: draft.postalCode.trim(),
    street: draft.street.trim(),
    number: draft.number.trim(),
    complement: draft.complement.trim(),
    district: draft.district.trim(),
    city: draft.city.trim(),
    state: draft.state.trim(),
    cnae: draft.cnae.trim(),
    activity: draft.activity.trim(),
    access_email: draft.accessEmail.trim(),
    password: draft.password,
    accept_contract: false,
    privacy_ack: false,
    marketing: false,
    method: null,
    installments: 1,
    summary_ack: false,
    plan: null,
    quoted_price_cents: null,
  };
}
