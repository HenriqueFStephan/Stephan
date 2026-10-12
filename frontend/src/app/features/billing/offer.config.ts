import { isCnpj, isEmail, isPhone, onlyDigits } from './br-docs';

/**
 * Public facts of the supplier. Monthly fees by company size live in plans.ts.
 * Leave a supplier value empty until it is the real one. The payment page lists what is still blank.
 *
 * Do not put a gateway token, a Pix credential, or a card secret here.
 * Those belong in debt.txt and on Render, and only after a payment institution is connected.
 * The API stores the order and does not charge.
 */
export interface OfferConfig {
  supplier: {
    /** Razão social, exactly as on the CNPJ card. */
    legalName: string;
    /** CNPJ of the practice, with or without punctuation. */
    cnpj: string;
    /** Inscrição municipal of the supplier. Required to issue NFS-e. */
    municipalRegistration: string;
    street: string;
    number: string;
    complement: string;
    district: string;
    city: string;
    /** Two-letter state, such as SP. */
    state: string;
    postalCode: string;
    /** Email that appears as the supplier contact. */
    email: string;
    phone: string;
    /** Channel for service, withdrawal, and complaints. Can repeat email. */
    sacEmail: string;
    /** Privacy contact (encarregado, or the channel that receives LGPD requests). */
    privacyEmail: string;
    /** Optional. CRP or other council id. Empty hides the line. */
    councilRegistration: string;
  };
  service: {
    /** Business days to carry out the cycle after payment is confirmed. */
    executionBusinessDays: number | null;
  };
  price: {
    /** Full service amount in cents (R$ 10,00 is 1000). Null until you publish a price. */
    cents: number | null;
    /** True when cents already contains ISS. False when ISS is added on top. */
    issIncluded: boolean;
    /** Municipal ISS rate, for example 2 or 5. Null until the accountant confirms it. At most 5. */
    issRatePercent: number | null;
  };
  card: {
    /** 1 means cash only. Do not raise this without filling totalsCents. */
    maxInstallments: number;
    /**
     * Total the buyer pays for that many installments, in cents.
     * Index 0 is unused. An interest-free plan repeats the cash total.
     * A missing entry is not offered. The page does not calculate interest.
     */
    totalsCents: Array<number | undefined>;
  };
}

export const offer: OfferConfig = {
  supplier: {
    legalName: '',
    cnpj: '',
    municipalRegistration: '',
    street: '',
    number: '',
    complement: '',
    district: '',
    city: '',
    state: '',
    postalCode: '',
    email: '',
    phone: '',
    sacEmail: '',
    privacyEmail: '',
    councilRegistration: '',
  },
  service: {
    executionBusinessDays: null,
  },
  price: {
    cents: null,
    issIncluded: true,
    issRatePercent: null,
  },
  card: {
    maxInstallments: 1,
    totalsCents: [],
  },
};

export type OfferGap =
  | 'legalName'
  | 'cnpj'
  | 'municipal'
  | 'address'
  | 'email'
  | 'phone'
  | 'sac'
  | 'privacy'
  | 'iss';

export function offerGaps(config: OfferConfig = offer): OfferGap[] {
  const supplier = config.supplier;
  const gaps: OfferGap[] = [];
  if (!supplier.legalName.trim()) gaps.push('legalName');
  if (!isCnpj(supplier.cnpj)) gaps.push('cnpj');
  if (!supplier.municipalRegistration.trim()) gaps.push('municipal');
  const addressReady =
    supplier.street.trim() &&
    supplier.number.trim() &&
    supplier.district.trim() &&
    supplier.city.trim() &&
    supplier.state.trim().length === 2 &&
    onlyDigits(supplier.postalCode).length === 8;
  if (!addressReady) gaps.push('address');
  if (!isEmail(supplier.email)) gaps.push('email');
  if (!isPhone(supplier.phone)) gaps.push('phone');
  if (!isEmail(supplier.sacEmail)) gaps.push('sac');
  if (!isEmail(supplier.privacyEmail)) gaps.push('privacy');
  const rate = config.price.issRatePercent;
  if (rate == null || rate < 0 || rate > 5) gaps.push('iss');
  return gaps;
}

export function formatBrl(cents: number): string {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(cents / 100);
}

export function formatRate(rate: number): string {
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(rate);
}

/** Null until both the price and the ISS rate are published, so the total is never a guess. */
export function totalCents(config: OfferConfig = offer): number | null {
  const price = config.price.cents;
  const rate = config.price.issRatePercent;
  if (price == null || price <= 0 || rate == null || rate < 0 || rate > 5) return null;
  if (config.price.issIncluded) return price;
  return price + Math.round((price * rate) / 100);
}

export function issAmountCents(config: OfferConfig = offer): number | null {
  const price = config.price.cents;
  const rate = config.price.issRatePercent;
  if (price == null || price <= 0 || rate == null || rate < 0 || rate > 5) return null;
  if (config.price.issIncluded) return Math.round((price * rate) / (100 + rate));
  return Math.round((price * rate) / 100);
}

export interface CardPlan {
  count: number;
  totalCents: number;
  evenSlice: boolean;
}

export function cardPlans(config: OfferConfig = offer): CardPlan[] {
  const cash = totalCents(config);
  if (cash == null) return [];
  const plans: CardPlan[] = [{ count: 1, totalCents: cash, evenSlice: true }];
  const max = Math.max(1, config.card.maxInstallments);
  for (let count = 2; count <= max; count += 1) {
    const listed = config.card.totalsCents[count];
    if (listed == null || listed < cash) continue;
    plans.push({ count, totalCents: listed, evenSlice: listed % count === 0 });
  }
  return plans;
}

export function supplierAddress(config: OfferConfig = offer): string {
  const supplier = config.supplier;
  const place = [supplier.street, supplier.number, supplier.complement].filter((part) => part.trim()).join(', ');
  const city = supplier.city && supplier.state ? `${supplier.city}/${supplier.state}` : supplier.city || supplier.state;
  const region = [supplier.district, city, supplier.postalCode.trim()].filter((part) => part.trim()).join(' · ');
  return [place, region].filter((part) => part.trim()).join(' — ');
}
