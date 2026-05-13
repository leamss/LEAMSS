import { useMemo } from 'react';

/**
 * Real-time password strength meter.
 * Shows bar + text feedback. Matches backend rules:
 *  8+ chars, lowercase, uppercase, digit, special.
 */
export default function PasswordStrengthMeter({ password = '' }) {
  const score = useMemo(() => {
    let s = 0;
    if (password.length >= 8) s++;
    if (/[a-z]/.test(password)) s++;
    if (/[A-Z]/.test(password)) s++;
    if (/\d/.test(password)) s++;
    if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password)) s++;
    return s;
  }, [password]);

  const labels = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very strong'];
  const colors = ['bg-rose-300', 'bg-rose-400', 'bg-amber-400', 'bg-amber-500', 'bg-emerald-500', 'bg-emerald-600'];

  if (!password) return null;

  return (
    <div className="mt-2" data-testid="pwd-strength">
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className={`h-1.5 flex-1 rounded ${i < score ? colors[score] : 'bg-slate-200'} transition-colors`} />
        ))}
      </div>
      <div className="flex justify-between mt-1.5 text-xs">
        <span className="text-slate-500">{labels[score]}</span>
        <span className="text-slate-400">{score}/5 rules</span>
      </div>
      {score < 5 && (
        <ul className="text-[10px] text-slate-500 mt-1 space-y-0.5">
          {password.length < 8 && <li>• At least 8 characters</li>}
          {!/[a-z]/.test(password) && <li>• Add a lowercase letter</li>}
          {!/[A-Z]/.test(password) && <li>• Add an uppercase letter</li>}
          {!/\d/.test(password) && <li>• Add a number</li>}
          {!/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password) && <li>• Add a special character</li>}
        </ul>
      )}
    </div>
  );
}
