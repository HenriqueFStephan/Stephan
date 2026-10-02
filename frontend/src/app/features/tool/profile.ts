/**
 * Anexo B, asked after the introduction and stored on the same form as the 35 items.
 * Option ids are the database codes. Keep them aligned with DEMOGRAPHIC_FIELDS
 * in backend/app/services/campaign_store.py.
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
    required: false,
    pt: 'Gênero',
    en: 'Gender',
    options: [
      { id: 'female', pt: 'Feminino', en: 'Female' },
      { id: 'male', pt: 'Masculino', en: 'Male' },
      { id: 'undisclosed', pt: 'Prefiro não declarar', en: 'Prefer not to say' },
    ],
  },
  {
    id: 'education',
    required: false,
    pt: 'Grau de Escolaridade',
    en: 'Education',
    options: [
      {
        id: 'fundamental',
        pt: 'Ensino Fundamental completo/incompleto',
        en: 'Elementary education, complete or incomplete',
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
    id: 'economic_sector',
    required: true,
    pt: 'Setor Econômico da Organização de Trabalho',
    en: 'Economic sector of the work organization',
    options: [
      {
        id: 'manufacturing',
        pt: 'Indústria e Produção de Manufaturados',
        en: 'Manufacturing',
      },
      { id: 'retail', pt: 'Comércio Varejista e Atacadista', en: 'Retail and wholesale trade' },
      { id: 'services', pt: 'Setor de Serviços Gerais', en: 'General services' },
      { id: 'health', pt: 'Saúde Humana e Serviços Sociais', en: 'Human health and social services' },
      { id: 'education', pt: 'Educação e Ensino', en: 'Education and teaching' },
      {
        id: 'it',
        pt: 'Tecnologia da Informação (TI) e Comunicação',
        en: 'Information technology and communication',
      },
      { id: 'construction', pt: 'Construção Civil', en: 'Construction' },
      {
        id: 'transport',
        pt: 'Transporte, Logística e Armazenagem',
        en: 'Transport, logistics, and storage',
      },
      {
        id: 'agribusiness',
        pt: 'Agropecuária e Agronegócio',
        en: 'Agriculture and agribusiness',
      },
      {
        id: 'public_admin',
        pt: 'Administração Pública e Gestão Governamental',
        en: 'Public administration',
      },
      { id: 'other', pt: 'Outro segmento produtivo', en: 'Another productive sector' },
    ],
  },
  {
    id: 'org_size',
    required: false,
    pt: 'Porte Aproximado da Organização de Trabalho',
    en: 'Approximate size of the work organization',
    options: [
      { id: 'micro', pt: 'Microempresa (até 19 colaboradores)', en: 'Micro enterprise (up to 19 employees)' },
      { id: 'small', pt: 'Pequena empresa (20 a 99 colaboradores)', en: 'Small enterprise (20 to 99 employees)' },
      {
        id: 'medium',
        pt: 'Média empresa (100 a 499 colaboradores)',
        en: 'Medium enterprise (100 to 499 employees)',
      },
      {
        id: 'large',
        pt: 'Grande empresa (500 ou mais colaboradores)',
        en: 'Large enterprise (500 or more employees)',
      },
      { id: 'unknown', pt: 'Não sei informar', en: 'I do not know' },
    ],
  },
  {
    id: 'employment_bond',
    required: false,
    pt: 'Natureza do Vínculo de Trabalho',
    en: 'Employment relationship',
    options: [
      {
        id: 'clt',
        pt: 'Empregado com registro em carteira profissional (CLT)',
        en: 'Employee with a signed work card (CLT)',
      },
      {
        id: 'public_statute',
        pt: 'Servidor público regido por estatuto',
        en: 'Public servant under a statute',
      },
      {
        id: 'autonomous_pj',
        pt: 'Trabalhador autônomo / Prestador de serviços Pessoa Jurídica (PJ)',
        en: 'Self-employed or service provider as a legal entity (PJ)',
      },
      {
        id: 'intern_apprentice',
        pt: 'Estágio curricular ou contrato de Jovem Aprendiz',
        en: 'Curricular internship or young apprentice contract',
      },
      { id: 'other', pt: 'Outra modalidade contratual', en: 'Another contractual arrangement' },
    ],
  },
  {
    id: 'tenure_org',
    required: false,
    pt: 'Tempo de Serviço na Organização Atual',
    en: 'Length of service in the current organization',
    options: [
      { id: 'lt_1', pt: 'Menos de 1 ano', en: 'Less than 1 year' },
      { id: 'y1_3', pt: 'Entre 1 e 3 anos', en: 'Between 1 and 3 years' },
      { id: 'y4_10', pt: 'Entre 4 e 10 anos', en: 'Between 4 and 10 years' },
      { id: 'gt_10', pt: 'Mais de 10 anos', en: 'More than 10 years' },
    ],
  },
  {
    id: 'tenure_profession',
    required: false,
    pt: 'Tempo Total de Atuação na Profissão Vigente',
    en: 'Total time in the current occupation',
    options: [
      { id: 'lt_1', pt: 'Menos de 1 ano', en: 'Less than 1 year' },
      { id: 'y1_5', pt: 'Entre 1 e 5 anos', en: 'Between 1 and 5 years' },
      { id: 'y6_15', pt: 'Entre 6 e 15 anos', en: 'Between 6 and 15 years' },
      { id: 'gt_15', pt: 'Mais de 15 anos', en: 'More than 15 years' },
    ],
  },
  {
    id: 'work_shift',
    required: false,
    pt: 'Regime de Turno Laboral Predominante',
    en: 'Predominant work shift',
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
    required: false,
    pt: 'Você exerce atribuições funcionais de chefia, gestão ou liderança formal de equipes?',
    en: 'Do you formally supervise, manage, or lead a team?',
    options: [
      { id: 'yes', pt: 'Sim', en: 'Yes' },
      { id: 'no', pt: 'Não', en: 'No' },
    ],
  },
  {
    id: 'region',
    required: false,
    pt: 'Região Geográfica de Residência e Trabalho',
    en: 'Geographic region of residence and work',
    options: [
      { id: 'north', pt: 'Região Norte', en: 'North' },
      { id: 'northeast', pt: 'Região Nordeste', en: 'Northeast' },
      { id: 'center_west', pt: 'Região Centro-Oeste', en: 'Center-West' },
      { id: 'southeast', pt: 'Região Sudeste', en: 'Southeast' },
      { id: 'south', pt: 'Região Sul', en: 'South' },
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
