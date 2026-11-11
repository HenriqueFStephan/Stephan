import { PROFILE_QUESTIONS, isProfileReady, profilePayload } from './profile';

const COMPLETE_PROFILE = {
  age_band: '18_24',
  gender: 'female',
  education: 'high_school_incomplete',
  tenure_org: 'y1_3',
  work_shift: 'day_fixed',
  leadership: 'no',
};

describe('Anexo B', () => {
  it('asks six required questions and splits elementary and secondary school', () => {
    expect(PROFILE_QUESTIONS.map((question) => question.id)).toEqual([
      'age_band',
      'gender',
      'education',
      'tenure_org',
      'work_shift',
      'leadership',
    ]);
    expect(PROFILE_QUESTIONS.every((question) => question.required)).toBeTrue();
    expect(PROFILE_QUESTIONS.map((question) => question.pt)).toEqual([
      'Faixa Etária',
      'Sexo',
      'Grau de Escolaridade',
      'Tempo de Serviço na Empresa',
      'Regime de Turno de Trabalho',
      'Você exerce atribuições funcionais de chefia, gestão ou liderança formal de equipes?',
    ]);
    const education = PROFILE_QUESTIONS.find((question) => question.id === 'education');
    expect(education?.options.map((option) => option.id)).toEqual([
      'fundamental_incomplete',
      'fundamental_complete',
      'high_school_incomplete',
      'high_school',
      'higher_incomplete',
      'higher_complete',
      'postgraduate',
    ]);
    expect(isProfileReady({})).toBeFalse();
    expect(isProfileReady({ age_band: '18_24' })).toBeFalse();
    expect(isProfileReady(COMPLETE_PROFILE)).toBeTrue();
    expect(isProfileReady({ ...COMPLETE_PROFILE, age_band: 'nope' })).toBeFalse();
    expect(profilePayload({ ...COMPLETE_PROFILE, region: '' })).toEqual(COMPLETE_PROFILE);
  });
});
