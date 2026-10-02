import { PROFILE_QUESTIONS, isProfileReady, profilePayload } from './profile';

describe('Anexo B', () => {
  it('asks eleven closed questions, and only age and sector are required', () => {
    expect(PROFILE_QUESTIONS.map((question) => question.id)).toEqual([
      'age_band',
      'gender',
      'education',
      'economic_sector',
      'org_size',
      'employment_bond',
      'tenure_org',
      'tenure_profession',
      'work_shift',
      'leadership',
      'region',
    ]);
    expect(PROFILE_QUESTIONS.filter((question) => question.required).map((question) => question.id)).toEqual([
      'age_band',
      'economic_sector',
    ]);
    expect(PROFILE_QUESTIONS.map((question) => question.options.length)).toEqual([
      6, 3, 5, 11, 5, 5, 4, 4, 4, 2, 5,
    ]);
    expect(isProfileReady({})).toBeFalse();
    expect(isProfileReady({ age_band: '18_24' })).toBeFalse();
    expect(isProfileReady({ age_band: '18_24', economic_sector: 'services' })).toBeTrue();
    expect(isProfileReady({ age_band: 'nope', economic_sector: 'services' })).toBeFalse();
    expect(profilePayload({ age_band: '35_44', economic_sector: 'health', gender: 'female', region: '' })).toEqual({
      age_band: '35_44',
      economic_sector: 'health',
      gender: 'female',
    });
  });
});
