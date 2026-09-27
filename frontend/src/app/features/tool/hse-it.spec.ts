import {
  BAND_COPY,
  DIMENSION_ORDER,
  DIMENSIONS,
  HSE_ITEMS,
  bandFor,
  favourableScore,
  hseSummary,
  scoreHse,
} from './hse-it';

describe('HSE-IT', () => {
  it('keeps the official 35 items, each once, in order', () => {
    expect(HSE_ITEMS.map((item) => item.n)).toEqual(
      Array.from({ length: 35 }, (_, index) => index + 1),
    );
    const counts = Object.fromEntries(DIMENSION_ORDER.map((id) => [id, 0])) as Record<
      string,
      number
    >;
    for (const item of HSE_ITEMS) {
      counts[item.dimension] += 1;
      if (item.n <= 23) {
        expect(item.scale).toBe('frequency');
      } else {
        expect(item.scale).toBe('agreement');
      }
    }
    expect(counts).toEqual({
      demands: 8,
      control: 6,
      manager: 5,
      peer: 4,
      relationships: 4,
      role: 5,
      change: 3,
    });
  });

  it('reverses only the negatively worded items', () => {
    const reversed = HSE_ITEMS.filter((item) => item.reverse).map((item) => item.n);
    expect(reversed).toEqual([3, 5, 6, 9, 12, 14, 16, 18, 20, 21, 22, 34]);
    expect(favourableScore(5, false)).toBe(5);
    expect(favourableScore(5, true)).toBe(1);
    expect(favourableScore(1, true)).toBe(5);
  });

  it('scores a fully favourable pattern at the top of every dimension', () => {
    const answers = HSE_ITEMS.map((item) => (item.reverse ? 1 : 5));
    const scores = scoreHse(answers);
    expect(scores.map((score) => score.id)).toEqual(DIMENSION_ORDER);
    for (const score of scores) {
      expect(score.mean).toBe(5);
      expect(score.band).toBe('maintain');
    }
  });

  it('treats “always” on a negative demand item as a low score', () => {
    const answers = HSE_ITEMS.map(() => 3);
    for (const item of HSE_ITEMS.filter((entry) => entry.dimension === 'demands')) {
      answers[item.n - 1] = 5;
    }
    const demands = scoreHse(answers).find((score) => score.id === 'demands');
    expect(demands?.mean).toBe(1);
    expect(demands?.band).toBe('urgent');
  });

  it('places scores on the HSE side of each percentile cut', () => {
    expect(bandFor(DIMENSIONS.role.p20 - 0.0001, 'role')).toBe('urgent');
    expect(bandFor(DIMENSIONS.role.p20, 'role')).toBe('improve');
    expect(bandFor(DIMENSIONS.role.p50, 'role')).toBe('good');
    expect(bandFor(DIMENSIONS.role.p80, 'role')).toBe('maintain');
    expect(bandFor(DIMENSIONS.demands.p50 - 0.0001, 'demands')).toBe('improve');
    expect(bandFor(DIMENSIONS.change.p80, 'change')).toBe('maintain');
  });

  it('writes a local summary without treating one answer as a group result', () => {
    const scores = scoreHse(HSE_ITEMS.map((item) => (item.reverse ? 1 : 5)));
    const text = hseSummary(scores, '  Expedição ', 'pt-BR');
    expect(text).toContain('Setor: Expedição');
    expect(text).toContain(`Papel: 5,00 — ${BAND_COPY.maintain['pt-BR']}`);
    expect(text).toContain('não é o resultado de um grupo');
  });
});
