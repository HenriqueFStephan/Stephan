import { Lang } from '../../core/i18n';

/**
 * HSE Management Standards Indicator Tool (35 items).
 *
 * The Portuguese sentences are the reviewed Brazilian instrument, adopted
 * on 9 November 2026 as the source of the 35 items. See "Item wording" in
 * docs/TOOL.md. They are not a translation of the UK English questionnaire.
 * The English sentences are a translation of this Portuguese, so a cultural
 * difference stays visible in English and is not pulled back to the UK item.
 *
 * Spacing was normalized, including the space before the period on item 27.
 * "difíceis" (item 3) carries its accent, and items 13 and 23 end with a
 * period. The words were not rewritten.
 *
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
  { n: 1, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Sei claramente o que é esperado de mim no trabalho.', en: 'I clearly know what is expected of me at work.' },
  { n: 2, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Posso decidir quando fazer uma pausa.', en: 'I can decide when to take a break.' },
  { n: 3, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'No trabalho, diferentes grupos exigem de mim coisas difíceis de conciliar.', en: 'At work, different groups demand of me things that are hard to reconcile.' },
  { n: 4, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Sei como fazer para executar o meu trabalho.', en: 'I know how to go about carrying out my work.' },
  { n: 5, dimension: 'relationships', reverse: true, scale: 'frequency', pt: 'Estou sujeito a assédio pessoal na forma de palavras ou comportamentos rudes.', en: 'I am subject to personal harassment in the form of rude words or behaviour.' },
  { n: 6, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Tenho prazos impossíveis de serem cumpridos.', en: 'I have deadlines that are impossible to meet.' },
  { n: 7, dimension: 'peer', reverse: false, scale: 'frequency', pt: 'Se o trabalho fica difícil, meus colegas me ajudam.', en: 'If work gets difficult, my colleagues help me.' },
  { n: 8, dimension: 'manager', reverse: false, scale: 'frequency', pt: 'Recebo retorno sobre o trabalho que eu realizo.', en: 'I receive feedback on the work that I carry out.' },
  { n: 9, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Tenho que trabalhar muito intensamente.', en: 'I have to work very intensively.' },
  { n: 10, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Posso decidir sobre o meu ritmo de trabalho.', en: 'I can decide on my work pace.' },
  { n: 11, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Estou ciente quais são os meus deveres e responsabilidades.', en: 'I am aware of what my duties and responsibilities are.' },
  { n: 12, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Preciso deixar de lado algumas tarefas porque tenho coisas demais para fazer.', en: 'I need to set some tasks aside because I have too many things to do.' },
  { n: 13, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Eu conheço as metas e objetivos do meu departamento.', en: 'I know the goals and objectives of my department.' },
  { n: 14, dimension: 'relationships', reverse: true, scale: 'frequency', pt: 'Existe atrito ou animosidade entre os colegas de trabalho.', en: 'There is friction or animosity among work colleagues.' },
  { n: 15, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Posso escolher como fazer o meu trabalho.', en: 'I can choose how to do my work.' },
  { n: 16, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Não consigo fazer pausas suficientes.', en: 'I cannot take sufficient breaks.' },
  { n: 17, dimension: 'role', reverse: false, scale: 'frequency', pt: 'Compreendo como o meu trabalho se integra com os objetivos da organização.', en: 'I understand how my work integrates with the objectives of the organization.' },
  { n: 18, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Sou pressionado para trabalhar por longos períodos.', en: 'I am pressured to work for long periods.' },
  { n: 19, dimension: 'control', reverse: false, scale: 'frequency', pt: 'Posso escolher o que fazer no trabalho.', en: 'I can choose what to do at work.' },
  { n: 20, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Tenho que trabalhar muito rápido.', en: 'I have to work very fast.' },
  { n: 21, dimension: 'relationships', reverse: true, scale: 'frequency', pt: 'Estou sujeito a constrangimentos no trabalho.', en: 'I am subject to embarrassing situations at work.' },
  { n: 22, dimension: 'demands', reverse: true, scale: 'frequency', pt: 'Sofro pressões de tempo absurdas.', en: 'I suffer absurd time pressures.' },
  { n: 23, dimension: 'manager', reverse: false, scale: 'frequency', pt: 'Posso contar com a ajuda do meu chefe imediato para resolver problemas do trabalho.', en: "I can count on my immediate boss's help to resolve work problems." },
  { n: 24, dimension: 'peer', reverse: false, scale: 'agreement', pt: 'Recebo a ajuda e o apoio necessário dos meus colegas.', en: 'I receive the necessary help and support from my colleagues.' },
  { n: 25, dimension: 'control', reverse: false, scale: 'agreement', pt: 'Tenho algum poder de decisão sobre a minha maneira de trabalhar.', en: 'I have some decision-making power over the way I work.' },
  { n: 26, dimension: 'change', reverse: false, scale: 'agreement', pt: 'Tenho oportunidades suficientes para questionar as chefias sobre mudanças no trabalho.', en: 'I have sufficient opportunities to question management about changes at work.' },
  { n: 27, dimension: 'peer', reverse: false, scale: 'agreement', pt: 'Sou respeitado como eu mereço pelos meus colegas.', en: 'I am respected by my colleagues as I deserve.' },
  { n: 28, dimension: 'change', reverse: false, scale: 'agreement', pt: 'A equipe é sempre consultada sobre mudanças no trabalho.', en: 'The team is always consulted about changes at work.' },
  { n: 29, dimension: 'manager', reverse: false, scale: 'agreement', pt: 'Posso falar com o meu chefe imediato sobre algo que me incomodou no trabalho.', en: 'I can talk to my immediate boss about something that bothered me at work.' },
  { n: 30, dimension: 'control', reverse: false, scale: 'agreement', pt: 'Meu horário de trabalho pode ser flexível.', en: 'My work schedule can be flexible.' },
  { n: 31, dimension: 'peer', reverse: false, scale: 'agreement', pt: 'Meus colegas estão dispostos a ouvir os meus problemas relacionados ao trabalho.', en: 'My colleagues are willing to listen to my work-related problems.' },
  { n: 32, dimension: 'change', reverse: false, scale: 'agreement', pt: 'Quando ocorrem mudanças no trabalho, sou esclarecido de como elas funcionarão na prática.', en: 'When changes occur at work, I am given an explanation of how they will work in practice.' },
  { n: 33, dimension: 'manager', reverse: false, scale: 'agreement', pt: 'Recebo apoio quando realizo trabalho que pode ser emocionalmente desgastante.', en: 'I receive support when I do work that can be emotionally draining.' },
  { n: 34, dimension: 'relationships', reverse: true, scale: 'agreement', pt: 'Os relacionamentos no trabalho são tensos.', en: 'Relationships at work are tense.' },
  { n: 35, dimension: 'manager', reverse: false, scale: 'agreement', pt: 'Meu chefe imediato me motiva no trabalho.', en: 'My immediate boss motivates me at work.' },
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
    lines.push(`${name}: ${formatMean(score.mean, lang)}`);
  }
  lines.push('');
  lines.push(
    lang === 'en'
      ? 'Bands follow the HSE Analysis Tool (136 organisations). One answer is not a group result.'
      : 'As faixas seguem a ferramenta de análise do HSE (136 organizações). Uma resposta não é o resultado de um grupo.',
  );
  return lines.join('\n');
}
