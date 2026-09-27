import { Lang } from '../../core/i18n';

/**
 * HSE Management Standards Indicator Tool (35 items).
 * Item order, scales, and reverse scoring follow the HSE questionnaire.
 * Bands follow the HSE Analysis Tool organisational benchmark
 * (136 organisations): below the 20th percentile, 20th to 50th,
 * 50th to 80th, and at or above the 80th.
 * A higher score is always the more favourable condition.
 */

export type DimensionId =
  | 'demands'
  | 'control'
  | 'manager'
  | 'peer'
  | 'relationships'
  | 'role'
  | 'change';

export type ScaleKind = 'frequency' | 'agreement';
export type Band = 'urgent' | 'improve' | 'good' | 'maintain';

export interface HseItem {
  n: number;
  dimension: DimensionId;
  reverse: boolean;
  scale: ScaleKind;
  pt: string;
  en: string;
}

export interface DimensionScore {
  id: DimensionId;
  mean: number;
  band: Band;
}

interface DimensionCopy {
  pt: string;
  en: string;
  aboutPt: string;
  aboutEn: string;
  p20: number;
  p50: number;
  p80: number;
}

export const DIMENSION_ORDER: DimensionId[] = [
  'demands',
  'control',
  'manager',
  'peer',
  'relationships',
  'role',
  'change',
];

export const DIMENSIONS: Record<DimensionId, DimensionCopy> = {
  demands: {
    pt: 'Demandas',
    en: 'Demands',
    aboutPt: 'Volume, ritmo, prazos e horas.',
    aboutEn: 'Workload, pace, deadlines, and hours.',
    p20: 2.9387,
    p50: 3.1024,
    p80: 3.2937,
  },
  control: {
    pt: 'Controle',
    en: 'Control',
    aboutPt: 'Margem para decidir o ritmo, o modo e o horário.',
    aboutEn: 'Say over pace, method, and working time.',
    p20: 3.224,
    p50: 3.4741,
    p80: 3.7208,
  },
  manager: {
    pt: 'Apoio da chefia',
    en: 'Manager support',
    aboutPt: 'Ajuda, retorno e encorajamento de quem coordena.',
    aboutEn: 'Help, feedback, and encouragement from the line manager.',
    p20: 3.272,
    p50: 3.4603,
    p80: 3.65,
  },
  peer: {
    pt: 'Apoio dos colegas',
    en: 'Peer support',
    aboutPt: 'Ajuda, escuta e respeito entre colegas.',
    aboutEn: 'Help, listening, and respect among colleagues.',
    p20: 3.627,
    p50: 3.78,
    p80: 3.8892,
  },
  relationships: {
    pt: 'Relacionamentos',
    en: 'Relationships',
    aboutPt: 'Atrito, assédio e intimidação.',
    aboutEn: 'Friction, harassment, and bullying.',
    p20: 3.6115,
    p50: 3.8499,
    p80: 4.0381,
  },
  role: {
    pt: 'Papel',
    en: 'Role',
    aboutPt: 'Clareza do que se espera e de como o trabalho se encaixa.',
    aboutEn: 'Clarity about what is expected, and how the work fits.',
    p20: 4.0356,
    p50: 4.1803,
    p80: 4.3117,
  },
  change: {
    pt: 'Mudança',
    en: 'Change',
    aboutPt: 'Consulta e clareza quando o trabalho muda.',
    aboutEn: 'Consultation and clarity when work changes.',
    p20: 2.791,
    p50: 3.0428,
    p80: 3.24,
  },
};

export const BAND_COPY: Record<Band, Record<Lang, string>> = {
  urgent: {
    'pt-BR': 'Abaixo do percentil 20 da referência. Pede atenção.',
    en: 'Below the 20th percentile of the reference. Needs attention.',
  },
  improve: {
    'pt-BR': 'Entre os percentis 20 e 50. Há o que melhorar.',
    en: 'Between the 20th and 50th percentiles. Room to improve.',
  },
  good: {
    'pt-BR': 'Entre os percentis 50 e 80. Favorável, com margem.',
    en: 'Between the 50th and 80th percentiles. Favorable, with room left.',
  },
  maintain: {
    'pt-BR': 'No percentil 80 ou acima. Condição a manter.',
    en: 'At or above the 80th percentile. A condition to keep.',
  },
};

export const SCALE_LABELS: Record<ScaleKind, Record<Lang, readonly string[]>> = {
  frequency: {
    'pt-BR': ['Nunca', 'Raramente', 'Às vezes', 'Frequentemente', 'Sempre'],
    en: ['Never', 'Seldom', 'Sometimes', 'Often', 'Always'],
  },
  agreement: {
    'pt-BR': ['Discordo totalmente', 'Discordo', 'Neutro', 'Concordo', 'Concordo totalmente'],
    en: ['Strongly disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly agree'],
  },
};

export const HSE_ITEMS: readonly HseItem[] = [
  { n: 1, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Sei com clareza o que esperam de mim no trabalho.', en: 'I am clear what is expected of me at work.' },
  { n: 2, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Posso decidir quando fazer uma pausa.', en: 'I can decide when to take a break.' },
  { n: 3, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Grupos diferentes no trabalho me pedem coisas difíceis de conciliar.', en: 'Different groups at work demand things from me that are hard to combine.' },
  { n: 4, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Sei como conduzir o meu trabalho.', en: 'I know how to go about getting my job done.' },
  { n: 5, dimension: 'relationships', reverse: true, scale: 'frequency', pt: 'Sofro assédio pessoal, na forma de palavras ou comportamentos hostis.', en: 'I am subject to personal harassment in the form of unkind words or behaviour.' },
  { n: 6, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Tenho prazos impossíveis de cumprir.', en: 'I have unachievable deadlines.' },
  { n: 7, dimension: 'peer', reverse: false, scale: 'frequency', pt: 'Se o trabalho fica difícil, meus colegas me ajudam.', en: 'If work gets difficult, my colleagues will help me.' },
  { n: 8, dimension: 'manager', reverse: false, scale: 'frequency', pt: 'Recebo retorno de apoio sobre o trabalho que faço.', en: 'I am given supportive feedback on the work I do.' },
  { n: 9, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Preciso trabalhar de modo muito intenso.', en: 'I have to work very intensively.' },
  { n: 10, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Tenho voz sobre o ritmo do meu trabalho.', en: 'I have a say in my own work speed.' },
  { n: 11, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Tenho clareza sobre os meus deveres e responsabilidades.', en: 'I am clear what my duties and responsibilities are.' },
  { n: 12, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Deixo algumas tarefas de lado porque tenho coisa demais para fazer.', en: 'I have to neglect some tasks because I have too much to do.' },
  { n: 13, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Tenho clareza sobre as metas e os objetivos da minha área.', en: 'I am clear about the goals and objectives for my department.' },
  { n: 14, dimension: 'relationships', reverse: true, scale: 'frequency', pt: 'Há atrito ou raiva entre colegas.', en: 'There is friction or anger between colleagues.' },
  { n: 15, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Posso escolher como faço o meu trabalho.', en: 'I have a choice in deciding how I do my work.' },
  { n: 16, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Não consigo fazer pausas suficientes.', en: 'I am unable to take sufficient breaks.' },
  { n: 17, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Entendo como o meu trabalho se encaixa no objetivo da organização.', en: 'I understand how my work fits into the overall aim of the organisation.' },
  { n: 18, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Sou pressionado a trabalhar por muitas horas.', en: 'I am pressured to work long hours.' },
  { n: 19, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Posso escolher o que faço no trabalho.', en: 'I have a choice in deciding what I do at work.' },
  { n: 20, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Preciso trabalhar muito rápido.', en: 'I have to work very fast.' },
  { n: 21, dimension: 'relationships', reverse: true, scale: 'frequency', pt: 'Sofro intimidação no trabalho.', en: 'I am subject to bullying at work.' },
  { n: 22, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Sofro pressões de tempo irreais.', en: 'I have unrealistic time pressures.' },
  { n: 23, dimension: 'manager', reverse: false, scale: 'frequency', pt: 'Posso contar com minha chefia imediata quando tenho um problema de trabalho.', en: 'I can rely on my line manager to help me out with a work problem.' },
  { n: 24, dimension: 'peer', reverse: false, scale: 'agreement', pt: 'Recebo dos colegas a ajuda e o apoio de que preciso.', en: 'I get help and support I need from colleagues.' },
  { n: 25, dimension: 'control', reverse: false, scale: 'agreement', pt: 'Tenho alguma voz sobre o modo como trabalho.', en: 'I have some say over the way I work.' },
  { n: 26, dimension: 'change', reverse: false, scale: 'agreement', pt: 'Tenho oportunidades suficientes para questionar a chefia sobre mudanças no trabalho.', en: 'I have sufficient opportunities to question managers about change at work.' },
  { n: 27, dimension: 'peer', reverse: false, scale: 'agreement', pt: 'Recebo dos colegas o respeito que mereço no trabalho.', en: 'I receive the respect at work I deserve from my colleagues.' },
  { n: 28, dimension: 'change', reverse: false, scale: 'agreement', pt: 'As pessoas são sempre consultadas sobre mudanças no trabalho.', en: 'Staff are always consulted about change at work.' },
  { n: 29, dimension: 'manager', reverse: false, scale: 'agreement', pt: 'Posso falar com minha chefia imediata sobre algo no trabalho que me incomodou ou irritou.', en: 'I can talk to my line manager about something that has upset or annoyed me about work.' },
  { n: 30, dimension: 'control', reverse: false, scale: 'agreement', pt: 'Meu horário de trabalho pode ser flexível.', en: 'My working time can be flexible.' },
  { n: 31, dimension: 'peer', reverse: false, scale: 'agreement', pt: 'Meus colegas estão dispostos a ouvir problemas relacionados ao trabalho.', en: 'My colleagues are willing to listen to my work-related problems.' },
  { n: 32, dimension: 'change', reverse: false, scale: 'agreement', pt: 'Quando há mudanças no trabalho, entendo com clareza como elas vão funcionar na prática.', en: 'When changes are made at work, I am clear how they will work out in practice.' },
  { n: 33, dimension: 'manager', reverse: false, scale: 'agreement', pt: 'Recebo apoio quando o trabalho é emocionalmente exigente.', en: 'I am supported through emotionally demanding work.' },
  { n: 34, dimension: 'relationships', reverse: true, scale: 'agreement', pt: 'As relações no trabalho são tensas.', en: 'Relationships at work are strained.' },
  { n: 35, dimension: 'manager', reverse: false, scale: 'agreement', pt: 'Minha chefia imediata me encoraja no trabalho.', en: 'My line manager encourages me at work.' },
];

export function favourableScore(raw: number, reverse: boolean): number {
  if (!Number.isInteger(raw) || raw < 1 || raw > 5) {
    throw new Error('HSE answer must be an integer from 1 to 5');
  }
  return reverse ? 6 - raw : raw;
}

export function bandFor(mean: number, dimension: DimensionId): Band {
  const cuts = DIMENSIONS[dimension];
  if (mean < cuts.p20) {
    return 'urgent';
  }
  if (mean < cuts.p50) {
    return 'improve';
  }
  if (mean < cuts.p80) {
    return 'good';
  }
  return 'maintain';
}

export function scoreHse(answers: readonly number[]): DimensionScore[] {
  if (answers.length !== HSE_ITEMS.length) {
    throw new Error('HSE-IT expects 35 answers');
  }
  return DIMENSION_ORDER.map((id) => {
    const items = HSE_ITEMS.filter((item) => item.dimension === id);
    const total = items.reduce(
      (sum, item) => sum + favourableScore(answers[item.n - 1], item.reverse),
      0,
    );
    const mean = total / items.length;
    return { id, mean, band: bandFor(mean, id) };
  });
}

export function formatMean(mean: number, lang: Lang): string {
  const text = mean.toFixed(2);
  return lang === 'pt-BR' ? text.replace('.', ',') : text;
}

export function barWidth(mean: number): number {
  const span = ((mean - 1) / 4) * 100;
  return Math.min(100, Math.max(2, span));
}

export function hseSummary(scores: readonly DimensionScore[], sector: string, lang: Lang): string {
  const lines = [
    lang === 'en' ? 'HSE-IT — local reading (test)' : 'HSE-IT — leitura local (teste)',
  ];
  const area = sector.trim();
  if (area) {
    lines.push(lang === 'en' ? `Area: ${area}` : `Setor: ${area}`);
  }
  lines.push('');
  for (const score of scores) {
    const name = lang === 'en' ? DIMENSIONS[score.id].en : DIMENSIONS[score.id].pt;
    lines.push(`${name}: ${formatMean(score.mean, lang)} — ${BAND_COPY[score.band][lang]}`);
  }
  lines.push('');
  lines.push(
    lang === 'en'
      ? 'Bands follow the HSE Analysis Tool (136 organisations). One answer is not a group result.'
      : 'As faixas seguem a ferramenta de análise do HSE (136 organizações). Uma resposta não é o resultado de um grupo.',
  );
  return lines.join('\n');
}
