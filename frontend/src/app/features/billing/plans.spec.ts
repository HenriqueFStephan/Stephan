import { monthlyCents } from './plans';

describe('monthly plans', () => {
  it('prices the smaller plan by headcount band', () => {
    expect(monthlyCents('hse', 1)).toBe(69000);
    expect(monthlyCents('hse', 49)).toBe(69000);
    expect(monthlyCents('hse', 50)).toBe(129000);
    expect(monthlyCents('hse', 499)).toBe(219000);
    expect(monthlyCents('hse', 500)).toBe(349000);
  });

  it('prices the larger plan above the smaller one in every band', () => {
    expect(monthlyCents('analise', 49)).toBe(149000);
    expect(monthlyCents('analise', 199)).toBe(279000);
    expect(monthlyCents('analise', 200)).toBe(469000);
    expect(monthlyCents('analise', 5000)).toBe(749000);
    expect(monthlyCents('analise', 49)).toBeGreaterThan(monthlyCents('hse', 49) ?? 0);
    expect(monthlyCents('analise', 500)).toBeGreaterThan(monthlyCents('hse', 500) ?? 0);
  });

  it('does not price an empty headcount', () => {
    expect(monthlyCents('hse', 0)).toBeNull();
    expect(monthlyCents('hse', Number.NaN)).toBeNull();
  });
});
