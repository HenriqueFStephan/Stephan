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
  it('keeps the stored codes and does not require them on the form', () => {
    expect(PROFILE_QUESTIONS.map((question) => question.id)).toEqual([
      'age_band',
      'gender',
      'education',
      'tenure_org',
      'work_shift',
      'leadership',
    ]);
    expect(PROFILE_QUESTIONS.every((question) => question.required)).toBeFalse();
    expect(isProfileReady({})).toBeTrue();
    expect(profilePayload({})).toEqual({});
    expect(profilePayload({ ...COMPLETE_PROFILE, region: '' })).toEqual(COMPLETE_PROFILE);
  });
});
