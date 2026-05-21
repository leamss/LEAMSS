// Smart Sales Helper — Convert wizard `data` state into the shape that the
// /sales/calculator/* and /sales/assessments endpoints expect.
//
// Strict marital-status guard: only emits a spouse object when the client is
// married/de-facto AND the spouse is migrating. Single applicants never carry
// stale spouse fields into the saved profile.
//
// Phase 6.8.4 — now emits the full au_extras / ca_extras / nz_extras blocks
// expected by core/sales_calculator.py so Step 5 "Additional Factors" actually
// influence the score (state nomination, NAATI, PNP, CLB7 French, etc.).

export function buildProfile(data) {
  const num = (v) => (v === '' || v === null || v === undefined ? null : parseFloat(v));
  const bool = (v) => v === true || v === 'true';

  const primary = {
    personal: { age: num(data.age) },
    professional: {
      current_profession: data.occupation_title,
      designation: data.occupation_title,
      years_experience_total: num(data.years_experience_total),
      years_experience_australia: num(data.years_experience_australia),
    },
    education: { highest_qualification: data.qualification },
    language: {
      scores: {
        overall: num(data.ielts_overall),
        listening: num(data.ielts_listening),
        reading: num(data.ielts_reading),
        writing: num(data.ielts_writing),
        speaking: num(data.ielts_speaking),
      },
    },
    au_extras: {
      australian_study_2_years: bool(data.australian_study_2_years),
      specialist_education_stem_au: bool(data.specialist_education_stem_au),
      professional_year_completed: bool(data.professional_year_completed),
      naati_accredited: bool(data.naati_accredited),
      regional_study_au: bool(data.regional_study_au),
      state_nominated: bool(data.state_nominated),
      state_code: data.state_code || null,
    },
    ca_extras: {
      canadian_work_years: num(data.canadian_work_years),
      provincial_nomination: bool(data.provincial_nomination),
      job_offer_noc_00: bool(data.job_offer_noc_00),
      job_offer_noc_0_a_b: bool(data.job_offer_noc_0_a_b),
      canadian_education_3plus_years: bool(data.canadian_education_3plus_years),
      canadian_education_1_2_years: bool(data.canadian_education_1_2_years),
      sibling_in_canada: bool(data.sibling_in_canada),
      french_proficiency_clb_7: bool(data.french_proficiency_clb_7),
    },
    nz_extras: {
      nz_skilled_employment_current: bool(data.nz_skilled_employment_current),
      nz_job_offer: bool(data.nz_job_offer),
      regional_employment_nz: bool(data.regional_employment_nz),
    },
  };

  let spouse = null;
  if ((data.marital_status === 'married' || data.marital_status === 'de_facto')
    && data.spouse_will_migrate === 'yes') {
    spouse = {
      contribution_type: data.spouse_contribution || 'not_applicable',
      is_applicant_on_visa: true,
      is_australian_pr_or_citizen: data.spouse_contribution === 'australian_pr_citizen',
      personal: { age: num(data.spouse_age) },
      professional: {
        current_profession: data.spouse_profession || '',
        years_experience_total: num(data.spouse_years_experience),
      },
      education: { highest_qualification: data.spouse_qualification },
      language: {
        scores: {
          overall: num(data.spouse_ielts_overall),
          listening: num(data.spouse_ielts_listening),
          reading: num(data.spouse_ielts_reading),
          writing: num(data.spouse_ielts_writing),
          speaking: num(data.spouse_ielts_speaking),
        },
      },
    };
  }

  return {
    client_name: data.client_name,
    marital_status: data.marital_status,
    primary_applicant: primary,
    spouse,
  };
}


// Build the targets[] array based on country_mode in the wizard.
export function buildTargets(data) {
  if (data.country_mode === 'top_3') {
    return [
      { country: 'AU', visa_subclass: data.visa_subclass || '189' },
      { country: 'CA' },
      { country: 'NZ' },
    ];
  }
  if (data.country_mode === 'custom') {
    return data.custom_countries.map((c) => ({
      country: c,
      visa_subclass: c === 'AU' ? data.visa_subclass : null,
    }));
  }
  // specific
  return [{
    country: data.specific_country,
    visa_subclass: data.specific_country === 'AU' ? data.visa_subclass : null,
  }];
}


// Phase 6.8.5 — Inverse of buildProfile: hydrate the wizard `data` state from a
// saved assessment document so the Resume / Continue flow can pre-fill all
// inputs. Falls back to safe defaults for missing keys.
export function dataFromAssessment(a, baseDefaults = {}) {
  const profile = a?.profile_snapshot || {};
  const primary = profile.primary_applicant || {};
  const lang = (primary.language && primary.language.scores) || {};
  const auEx = primary.au_extras || {};
  const caEx = primary.ca_extras || {};
  const nzEx = primary.nz_extras || {};
  const sp = profile.spouse || {};
  const spLang = (sp.language && sp.language.scores) || {};
  const occ = a?.occupation || {};
  const targets = a?.targets || [];

  // Reconstruct country_mode
  let country_mode = 'specific';
  let specific_country = (targets[0] && targets[0].country) || 'AU';
  let visa_subclass = '189';
  let custom_countries = [specific_country];
  const auTarget = targets.find((t) => t.country === 'AU');
  if (auTarget && auTarget.visa_subclass) visa_subclass = String(auTarget.visa_subclass);

  if (targets.length === 1) {
    country_mode = 'specific';
    custom_countries = [specific_country];
  } else if (targets.length === 3
    && targets.every((t) => ['AU', 'CA', 'NZ'].includes(t.country))) {
    country_mode = 'top_3';
    specific_country = 'AU';
    custom_countries = ['AU', 'CA', 'NZ'];
  } else if (targets.length > 1) {
    country_mode = 'custom';
    specific_country = 'AU';
    custom_countries = targets.map((t) => t.country).filter(Boolean);
  }

  const num = (v) => (v == null ? '' : String(v));

  return {
    ...baseDefaults,
    client_name: a?.client_name || '',
    client_email: a?.client_email || '',
    client_phone: a?.client_phone || '',
    approach: 'direct',
    marital_status: profile.marital_status || '',
    age: num(primary.personal && primary.personal.age),
    qualification: (primary.education && primary.education.highest_qualification) || '',
    ielts_overall: num(lang.overall),
    ielts_listening: num(lang.listening),
    ielts_reading: num(lang.reading),
    ielts_writing: num(lang.writing),
    ielts_speaking: num(lang.speaking),
    years_experience_total: num(primary.professional && primary.professional.years_experience_total),
    years_experience_australia: num(primary.professional && primary.professional.years_experience_australia),
    occupation_country: occ.country_code || 'AU',
    occupation_code: occ.code || '',
    occupation_title: occ.title || '',
    occupation_body: occ.assessing_body || '',
    occupation_pathway: occ.pathway || '',
    country_mode,
    specific_country,
    visa_subclass,
    custom_countries,
    // Spouse
    spouse_will_migrate: sp.is_applicant_on_visa === false ? 'no' : 'yes',
    spouse_contribution: sp.contribution_type || '',
    spouse_age: num(sp.personal && sp.personal.age),
    spouse_qualification: (sp.education && sp.education.highest_qualification) || '',
    spouse_ielts_overall: num(spLang.overall),
    spouse_ielts_listening: num(spLang.listening),
    spouse_ielts_reading: num(spLang.reading),
    spouse_ielts_writing: num(spLang.writing),
    spouse_ielts_speaking: num(spLang.speaking),
    spouse_profession: (sp.professional && sp.professional.current_profession) || '',
    spouse_years_experience: num(sp.professional && sp.professional.years_experience_total),
    // AU extras
    australian_study_2_years: !!auEx.australian_study_2_years,
    specialist_education_stem_au: !!auEx.specialist_education_stem_au,
    professional_year_completed: !!auEx.professional_year_completed,
    naati_accredited: !!auEx.naati_accredited,
    regional_study_au: !!auEx.regional_study_au,
    state_nominated: !!auEx.state_nominated,
    state_code: auEx.state_code || '',
    // CA extras
    canadian_work_years: num(caEx.canadian_work_years),
    provincial_nomination: !!caEx.provincial_nomination,
    job_offer_noc_00: !!caEx.job_offer_noc_00,
    job_offer_noc_0_a_b: !!caEx.job_offer_noc_0_a_b,
    canadian_education_3plus_years: !!caEx.canadian_education_3plus_years,
    canadian_education_1_2_years: !!caEx.canadian_education_1_2_years,
    sibling_in_canada: !!caEx.sibling_in_canada,
    french_proficiency_clb_7: !!caEx.french_proficiency_clb_7,
    // NZ extras
    nz_skilled_employment_current: !!nzEx.nz_skilled_employment_current,
    nz_job_offer: !!nzEx.nz_job_offer,
    regional_employment_nz: !!nzEx.regional_employment_nz,
  };
}
