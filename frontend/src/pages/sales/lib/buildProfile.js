// Smart Sales Helper — Convert wizard `data` state into the shape that the
// /sales/calculator/* and /sales/assessments endpoints expect.
//
// Strict marital-status guard: only emits a spouse object when the client is
// married/de-facto AND the spouse is migrating. Single applicants never carry
// stale spouse fields into the saved profile.

export function buildProfile(data) {
  const num = (v) => (v === '' || v === null || v === undefined ? null : parseFloat(v));

  const primary = {
    personal: { age: num(data.age) },
    professional: {
      current_profession: data.occupation_title,
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
      australian_study_2_years: data.australian_study_2_years,
      naati_accredited: data.naati_accredited,
      professional_year_completed: data.professional_year_completed,
      state_nominated: data.state_nominated,
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
      education: { highest_qualification: data.spouse_qualification },
      language: { scores: { overall: num(data.spouse_ielts_overall) } },
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
