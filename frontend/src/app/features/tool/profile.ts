/**
 * Anexo B, asked after the introduction and stored on the same form as the 35 items.
 * Option ids are the database codes. Keep them aligned with DEMOGRAPHIC_FIELDS
 * in backend/app/services/campaign_store.py.
 *
 * The form asks six questions, all required. Economic sector, organization size,
 * employment relationship, time in the occupation, and region stay as stored
 * columns and are no longer asked. The combined `fundamental` education code
 * is retired on the form and still accepted on older rows.
 */

export interface ProfileOption {
  id: string;
  pt: string;
  en: string;
}

export interface ProfileQuestion {
  id: string;
  required: boolean;
  pt: string;
  en: string;
  options: readonly ProfileOption[];
}

export const PROFILE_QUESTIONS: readonly ProfileQuestion[] = [
  {
    id: 'age_band',
    required: true,
    pt: 'Faixa Etária',
    en: 'Age band',
    options: [
      { id: '18_24', pt: '18 a 24 anos', en: '18 to 24 years' },
      { id: '25_34', pt: '25 a 34 anos', en: '25 to 34 years' },
      { id: '35_44', pt: '35 a 44 anos', en: '35 to 44 years' },
      { id: '45_54', pt: '45 a 54 anos', en: '45 to 54 years' },
      { id: '55_64', pt: '55 a 64 anos', en: '55 to 64 years' },
      { id: '65_plus', pt: '65 anos ou mais', en: '65 years or older' },
    ],
  },
  {
    id: 'gender',
    required: true,
    pt: 'Sexo',
    en: 'Sex',
    options: [
      { id: 'female', pt: 'Feminino', en: 'Female' },
      { id: 'male', pt: 'Masculino', en: 'Male' },
      { id: 'undisclosed', pt: 'Prefiro não declarar', en: 'Prefer not to say' },
    ],
  },
  {
    id: 'education',
    required: true,
    pt: 'Grau de Escolaridade',
    en: 'Education',
    options: [
      {
        id: 'fundamental_incomplete',
        pt: 'Ensino Fundamental incompleto',
        en: 'Incomplete elementary education',
      },
      {
        id: 'fundamental_complete',
        pt: 'Ensino Fundamental completo',
        en: 'Complete elementary education',
      },
      {
        id: 'high_school_incomplete',
        pt: 'Ensino Médio incompleto',
        en: 'Incomplete secondary education',
      },
      { id: 'high_school', pt: 'Ensino Médio completo', en: 'Complete secondary education' },
      {
        id: 'higher_incomplete',
        pt: 'Ensino Superior incompleto',
        en: 'Incomplete higher education',
      },
      { id: 'higher_complete', pt: 'Ensino Superior completo', en: 'Complete higher education' },
      {
        id: 'postgraduate',
        pt: 'Pós-graduação (Especialização, Mestrado ou Doutorado)',
        en: 'Postgraduate study (specialization, master, or doctorate)',
      },
    ],
  },
  {
    id: 'tenure_org',
    required: true,
    pt: 'Tempo de Serviço na Empresa',
    en: 'Length of service at the company',
    options: [
      { id: 'lt_1', pt: 'Menos de 1 ano', en: 'Less than 1 year' },
      { id: 'y1_3', pt: 'Entre 1 e 3 anos', en: 'Between 1 and 3 years' },
      { id: 'y4_10', pt: 'Entre 4 e 10 anos', en: 'Between 4 and 10 years' },
      { id: 'gt_10', pt: 'Mais de 10 anos', en: 'More than 10 years' },
    ],
  },
  {
    id: 'work_shift',
    required: true,
    pt: 'Regime de Turno de Trabalho',
    en: 'Work shift regime',
    options: [
      { id: 'day_fixed', pt: 'Diurno fixo', en: 'Fixed day shift' },
      { id: 'night_fixed', pt: 'Noturno fixo', en: 'Fixed night shift' },
      {
        id: 'rotating',
        pt: 'Turnos alternados / Escalas de revezamento contínuas',
        en: 'Alternating or continuous rotating shifts',
      },
      { id: 'flexible', pt: 'Regime de horários flexíveis', en: 'Flexible hours' },
    ],
  },
  {
    id: 'leadership',
    required: true,
    pt: 'Você exerce atribuições funcionais de chefia, gestão ou liderança formal de equipes?',
    en: 'Do you formally supervise, manage, or lead a team?',
    options: [
      { id: 'yes', pt: 'Sim', en: 'Yes' },
      { id: 'no', pt: 'Não', en: 'No' },
    ],
  },
];

export function isProfileReady(selected: Readonly<Record<string, string | undefined>>): boolean {
  return PROFILE_QUESTIONS.every((question) => {
    if (!question.required) {
      return true;
    }
    const value = selected[question.id];
    return question.options.some((option) => option.id === value);
  });
}

export function profilePayload(
  selected: Readonly<Record<string, string | undefined>>,
): Record<string, string> {
  const payload: Record<string, string> = {};
  for (const question of PROFILE_QUESTIONS) {
    const value = selected[question.id];
    if (value && question.options.some((option) => option.id === value)) {
      payload[question.id] = value;
    }
  }
  return payload;
}
