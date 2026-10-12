import { MsgKey } from '../../core/i18n';

/**
 * Public monthly fees, in cents, by how many people the plan covers.
 * The same table lives in backend/app/services/plans.py. The API rejects a quote that does not match.
 * Bands run from smaller companies to larger ones.
 */
export type PlanId = 'hse' | 'analise';

export interface SizeBand {
  id: 'xs' | 's' | 'm' | 'l';
  /** Inclusive upper bound. Null means there is no ceiling. */
  maxHeadcount: number | null;
  labelKey: MsgKey;
  monthlyCents: Record<PlanId, number>;
}

export interface PlanOffer {
  id: PlanId;
  titleKey: MsgKey;
  shortKey: MsgKey;
  /** Tools shared with the smaller plan. The smaller plan has only these. */
  featureKeys: readonly MsgKey[];
  /** Depth work added on the larger plan. Empty on the smaller plan. */
  extraKeys: readonly MsgKey[];
}

export const sizeBands: readonly SizeBand[] = [
  {
    id: 'xs',
    maxHeadcount: 49,
    labelKey: 'plan.band.xs',
    monthlyCents: { hse: 69_000, analise: 149_000 },
  },
  {
    id: 's',
    maxHeadcount: 199,
    labelKey: 'plan.band.s',
    monthlyCents: { hse: 129_000, analise: 279_000 },
  },
  {
    id: 'm',
    maxHeadcount: 499,
    labelKey: 'plan.band.m',
    monthlyCents: { hse: 219_000, analise: 469_000 },
  },
  {
    id: 'l',
    maxHeadcount: null,
    labelKey: 'plan.band.l',
    monthlyCents: { hse: 349_000, analise: 749_000 },
  },
];

export const plans: readonly PlanOffer[] = [
  {
    id: 'hse',
    titleKey: 'plan.hse.title',
    shortKey: 'plan.hse.short',
    featureKeys: ['plan.hse.f1', 'plan.hse.f2', 'plan.hse.f3'],
    extraKeys: [],
  },
  {
    id: 'analise',
    titleKey: 'plan.analise.title',
    shortKey: 'plan.analise.short',
    featureKeys: ['plan.hse.f1', 'plan.hse.f2', 'plan.hse.f3'],
    extraKeys: ['plan.analise.f1', 'plan.analise.f2', 'plan.analise.f3', 'plan.analise.f4'],
  },
];

export function isPlanId(value: string): value is PlanId {
  return value === 'hse' || value === 'analise';
}

export function planById(id: string): PlanOffer | null {
  return plans.find((plan) => plan.id === id) ?? null;
}

export function bandForHeadcount(headcount: number): SizeBand | null {
  if (!Number.isInteger(headcount) || headcount < 1) return null;
  for (const band of sizeBands) {
    if (band.maxHeadcount == null || headcount <= band.maxHeadcount) return band;
  }
  return null;
}

export function monthlyCents(plan: PlanId, headcount: number): number | null {
  const band = bandForHeadcount(headcount);
  return band ? band.monthlyCents[plan] : null;
}
