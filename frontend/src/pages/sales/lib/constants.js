// Smart Sales Helper — Shared constants used across the 7 wizard steps.

import { Briefcase, Calculator, CheckCircle2, Globe, Trophy, User, Wand2, Coins } from 'lucide-react';

export const STEPS = [
  { id: 1, label: 'Start', icon: User },
  { id: 2, label: 'Approach', icon: Wand2 },
  { id: 3, label: 'Profile', icon: Briefcase },
  { id: 4, label: 'Countries', icon: Globe },
  { id: 5, label: 'Calculator', icon: Calculator },
  { id: 6, label: 'Cost Estimator', icon: Coins },
  { id: 7, label: 'Review', icon: CheckCircle2 },
  { id: 8, label: 'Done', icon: Trophy },
];

export const QUALIFICATIONS = [
  { v: 'doctorate', l: 'Doctorate / PhD' },
  { v: 'master', l: "Master's Degree" },
  { v: 'bachelor', l: "Bachelor's Degree" },
  { v: 'diploma', l: 'Diploma' },
  { v: 'trade', l: 'Trade Qualification' },
  { v: 'high_school', l: 'High School' },
];

export const MARITAL_OPTIONS = [
  { v: 'single', l: 'Single' },
  { v: 'married', l: 'Married' },
  { v: 'de_facto', l: 'De facto' },
  { v: 'divorced', l: 'Divorced' },
  { v: 'widowed', l: 'Widowed' },
  { v: 'separated', l: 'Separated' },
];

export const CONTRIBUTION_OPTIONS = [
  { v: 'skill_assessment', l: 'Spouse Skill Assessment + Work Exp (+10)' },
  { v: 'english_only', l: 'Spouse Competent English Only (+5)' },
  { v: 'non_contributing', l: "Spouse won't contribute (0)" },
  { v: 'australian_pr_citizen', l: 'Spouse is AU PR/Citizen (+10)' },
];

export const COUNTRIES = [
  { code: 'AU', name: 'Australia', flag: '🇦🇺' },
  { code: 'CA', name: 'Canada', flag: '🇨🇦' },
  { code: 'NZ', name: 'New Zealand', flag: '🇳🇿' },
];

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
