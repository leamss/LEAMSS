import { Button } from '@/components/ui/button';
import { CreditCard, Send } from 'lucide-react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function InstallmentEditor({ maxCount = 5, totalAmount, schedule, onChange }) {
    const addRow = () => {
    if (schedule.length >= maxCount) return;
    onChange([...schedule, { amount: 0, due_date: '' }]);
};
const update = (i, patch) => {
    const next = [...schedule];
    next[i] = { ...next[i], ...patch };
    onChange(next);
    };
const remove = (i) => onChange(schedule.filter((_, idx) => idx !== i));
const sum = schedule.reduce((s, r) => s + (parseFloat(r.amount) || 0), 0);

    return (
    <div className="mt-2 space-y-1.5 bg-amber-50 border border-amber-200 rounded p-2">
    <div className="flex justify-between items-center">
        <p className="text-[11px] font-bold text-amber-800">Installment Schedule (max {maxCount})</p>
        {schedule.length < maxCount && (
        <button type="button" onClick={addRow} className="text-[11px] text-amber-700 underline">+ Add installment</button>
        )}
    </div>
    {schedule.map((r, i) => (
        <div key={i} className="flex gap-1.5 items-center">
        <input type="number" className="border rounded px-2 py-1 text-xs w-28" placeholder="₹ amount"
            value={r.amount} onChange={e => update(i, { amount: parseFloat(e.target.value) || 0 })} />
        <input type="date" className="border rounded px-2 py-1 text-xs" value={r.due_date}
            onChange={e => update(i, { due_date: e.target.value })} />
        <button type="button" onClick={() => remove(i)} className="text-rose-500 text-xs">✕</button>
        </div>
        ))}
    {totalAmount != null && (
        <p className={`text-[11px] font-bold ${sum === totalAmount ? 'text-emerald-700' : 'text-rose-600'}`}>
        Total: ₹{sum.toLocaleString('en-IN')} / ₹{totalAmount.toLocaleString('en-IN')} required
        </p>
    )}
    </div>
    );
}

export default function PaFinalizePaymentForm({
  pa, paymentMethodForm, setPaymentMethodForm, handleFinalizePaymentMethod, onCancel,
  requiresPartnerInfo, getAuthHeader, onSpouseSaved,
}) {
    const pkg = pa.selected_package_snapshot;
    const basePrice = pkg?.price ?? 0;

    // 👇 Load Marketing Hub Promo Codes + Product Coupons
    const [coupons, setCoupons] = useState([]);
    const [loadingCoupons, setLoadingCoupons] = useState(true);
    const [productWorkflowSteps, setProductWorkflowSteps] = useState([]);
    const [loadingWorkflow, setLoadingWorkflow] = useState(false);

    useEffect(() => {
        if (!pa.product_id) return;
        setLoadingWorkflow(true);
        axios.get(`${API}/products/${pa.product_id}`, getAuthHeader())
            .then(res => {
                const steps = res.data?.workflow_steps || [];
                steps.sort((a, b) => (a.step_order || 0) - (b.step_order || 0));
                setProductWorkflowSteps(steps);
                if (!paymentMethodForm.second_installment_step_order && steps.length > 0) {
                    const defaultStep = steps.find(s => s.step_order === 4) || steps[Math.min(2, steps.length - 1)];
                    if (defaultStep) {
                        setPaymentMethodForm(prev => ({
                            ...prev,
                            second_installment_trigger_type: prev.second_installment_trigger_type || 'step',
                            second_installment_step_order: prev.second_installment_step_order || defaultStep.step_order,
                            second_installment_step_name: prev.second_installment_step_name || defaultStep.step_name,
                        }));
                    }
                }
            })
            .catch(err => console.error('Failed to load product workflow steps:', err))
            .finally(() => setLoadingWorkflow(false));
    }, [pa.product_id]);

    useEffect(() => {
        let isMounted = true;
        setLoadingCoupons(true);
        Promise.allSettled([
            axios.get(`${API}/marketing/promos`, getAuthHeader()),
            pa.product_id ? axios.get(`${API}/products/${pa.product_id}/coupons`, getAuthHeader()) : Promise.resolve({ data: { coupons: [] } })
        ]).then(([mRes, pRes]) => {
            if (!isMounted) return;
            const marketingPromos = (mRes.status === 'fulfilled' && Array.isArray(mRes.value?.data))
                ? mRes.value.data.filter(p => {
                    const isExplicitActive = p.is_active ?? p.active ?? true;
                    const used = p.current_uses ?? p.used_count ?? 0;
                    const max = p.max_uses;
                    const isLimitReached = Boolean(max && max > 0 && used >= max) || Boolean(p.is_limit_reached);
                    return isExplicitActive && !isLimitReached;
                }).map(p => ({
                    id: p.id || p.code,
                    code: p.code,
                    discount_type: p.discount_type,
                    discount_value: p.discount_value,
                    notes: p.notes || (p.discount_type === 'percentage' ? `${p.discount_value}% Admin Promo` : `₹${p.discount_value} Flat Promo`),
                    source: 'marketing'
                }))
                : [];
            const productCoupons = (pRes.status === 'fulfilled' && Array.isArray(pRes.value?.data?.coupons))
                ? pRes.value.data.coupons.filter(c => {
                    const isExplicitActive = c.is_active ?? c.active ?? true;
                    const used = c.current_uses ?? c.used_count ?? 0;
                    const max = c.max_uses;
                    const isLimitReached = Boolean(max && max > 0 && used >= max) || Boolean(c.is_limit_reached);
                    return isExplicitActive && !isLimitReached;
                }).map(c => ({ ...c, source: 'product' }))
                : [];
            
            // Merge unique by code
            const map = new Map();
            [...marketingPromos, ...productCoupons].forEach(c => {
                if (c.code && !map.has(c.code.toUpperCase())) {
                    map.set(c.code.toUpperCase(), c);
                }
            });
            setCoupons(Array.from(map.values()));
        }).finally(() => {
            if (isMounted) setLoadingCoupons(false);
        });
        return () => { isMounted = false; };
    }, [pa.product_id]);

    const selectedCoupon = coupons.find(c => c.code?.toUpperCase() === (paymentMethodForm.coupon_code || paymentMethodForm.promo_code)?.toUpperCase()) || null;
    let discountAmount = 0;
    if (selectedCoupon) {
        discountAmount = selectedCoupon.discount_type === 'percentage'
            ? Math.round(basePrice * selectedCoupon.discount_value / 100)
            : Math.round(selectedCoupon.discount_value);
        discountAmount = Math.min(discountAmount, basePrice);
    }
    const deductPaFee = Boolean(paymentMethodForm.deduct_pre_assessment_fee);
    const paDeduction = deductPaFee ? 5100 : 0;
    const netBasePrice = Math.max(0, basePrice - discountAmount - paDeduction);
    const discountedPrice = Math.max(0, basePrice - discountAmount);

    const includeGst = paymentMethodForm.include_gst || false;
    const gstAmount = includeGst ? Math.round(netBasePrice * 0.18) : 0;
    const totalAmount = netBasePrice + gstAmount;
    const isInstallments = paymentMethodForm.payment_method_type === 'installments';

    // 👇 NEW — spouse info gate
    const needsSpouseForm = requiresPartnerInfo && !pa.spouse_info;
    const [spouse, setSpouse] = useState({
    name: '', mobile: '', email: '', age: '', education: '', work_experience: '', notes: '',
    });
    const [savingSpouse, setSavingSpouse] = useState(false);

    const saveSpouseInfo = async () => {
    if (!spouse.name || !spouse.email) {
        toast.error('Name and Email are required');
        return;
    }
    setSavingSpouse(true);
    try {
        await axios.post(`${API}/pre-assessment/${pa.id}/spouse-info`, {
        ...spouse,
        age: spouse.age ? parseInt(spouse.age) : null,
        }, getAuthHeader());
        toast.success('Partner/Spouse info saved');
        onSpouseSaved?.();
    } catch (e) {
        toast.error(e?.response?.data?.detail || 'Failed to save');
    } finally {
        setSavingSpouse(false);
    }
    };

    // 👇 NEW — render spouse form INSTEAD of payment method UI, until saved
    if (needsSpouseForm) {
    return (
        <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-200 space-y-3">
        <p className="text-sm font-semibold text-indigo-800 mb-1">
            Partner/Spouse Details — {pa.client_name}'s "{pkg?.name}" requires this info first
        </p>
        <div className="grid grid-cols-2 gap-3">
            <input className="border rounded px-3 py-2 text-sm" placeholder="Full Name *"
            value={spouse.name} onChange={e => setSpouse({ ...spouse, name: e.target.value })} />
            <input className="border rounded px-3 py-2 text-sm" placeholder="Email *"
            value={spouse.email} onChange={e => setSpouse({ ...spouse, email: e.target.value })} />
            <input className="border rounded px-3 py-2 text-sm" placeholder="Mobile No."
            value={spouse.mobile} onChange={e => setSpouse({ ...spouse, mobile: e.target.value })} />
            <input className="border rounded px-3 py-2 text-sm" type="number" placeholder="Age"
            value={spouse.age} onChange={e => setSpouse({ ...spouse, age: e.target.value })} />
            <input className="border rounded px-3 py-2 text-sm" placeholder="Education"
            value={spouse.education} onChange={e => setSpouse({ ...spouse, education: e.target.value })} />
            <input className="border rounded px-3 py-2 text-sm" placeholder="Work Experience"
            value={spouse.work_experience} onChange={e => setSpouse({ ...spouse, work_experience: e.target.value })} />
        </div>
        <textarea className="border rounded px-3 py-2 text-sm w-full" rows={2} placeholder="Notes"
            value={spouse.notes} onChange={e => setSpouse({ ...spouse, notes: e.target.value })} />
        <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
            <Button size="sm" onClick={saveSpouseInfo} disabled={savingSpouse}
            className="bg-indigo-600 hover:bg-indigo-700">
            {savingSpouse ? 'Saving…' : 'Save & Continue to Payment Method'}
            </Button>
        </div>
        </div>
    );
    }


return (
    <div className="bg-fuchsia-50 rounded-lg p-4 border border-fuchsia-200 space-y-4">
    <p className="text-sm font-semibold text-fuchsia-800 mb-1 flex items-center gap-2">
        <CreditCard className="h-4 w-4" /> Set Payment Method for {pa.client_name}
    </p>
     {pkg && (
        <p className="text-xs text-slate-600">
        Client selected: <strong>{pkg.name}</strong> — ₹{Number(pkg.price || 0).toLocaleString('en-IN')}
        </p>
    )}

{/* 👇 Discount coupon / Promo code (admin Marketing Hub + Product) */}
    <div className="bg-white border border-fuchsia-200 rounded-lg p-3 space-y-2">
        <div className="flex justify-between items-center">
            <p className="text-xs font-semibold text-slate-700">Apply Discount Coupon / Promo Code (optional)</p>
            {coupons.length > 0 && (
                <span className="text-[10px] bg-fuchsia-100 text-fuchsia-700 px-1.5 py-0.5 rounded-full font-semibold">
                    {coupons.length} Active
                </span>
            )}
        </div>
        {loadingCoupons ? (
            <p className="text-xs text-slate-400">Loading promo codes…</p>
        ) : coupons.length === 0 ? (
            <p className="text-xs text-slate-400 italic">No active promo codes available. Create one in Marketing Hub.</p>
        ) : (
            <select
                value={paymentMethodForm.coupon_code || paymentMethodForm.promo_code || ''}
                onChange={(e) => {
                    const val = e.target.value || null;
                    setPaymentMethodForm({
                        ...paymentMethodForm,
                        coupon_code: val,
                        promo_code: val,
                        promo_enabled: val ? (paymentMethodForm.promo_enabled !== false) : false
                    });
                }}
                className="w-full border border-fuchsia-200 rounded-md px-3 py-2 text-sm bg-white"
                data-testid="coupon-select"
            >
                <option value="">— No promo code —</option>
                {coupons.map(c => (
                    <option key={c.id || c.code} value={c.code}>
                        🏷️ {c.code} — {c.discount_type === 'percentage' ? `${c.discount_value}% off` : `₹${c.discount_value} off`}
                        {c.notes ? ` (${c.notes})` : ''}
                    </option>
                ))}
            </select>
        )}
        {selectedCoupon && (
            <div className="space-y-2 pt-1 border-t border-fuchsia-100 mt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                    <input
                        type="checkbox"
                        checked={paymentMethodForm.promo_enabled !== false}
                        onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, promo_enabled: e.target.checked })}
                        className="h-4 w-4 text-fuchsia-600 rounded"
                        data-testid="enable-client-promo-toggle"
                    />
                    <span className="text-xs font-semibold text-slate-700">
                        Enable & directly show this promo code on Client’s Payment screen
                    </span>
                </label>
                {discountAmount > 0 && (
                    <p className="text-xs font-semibold text-emerald-700">
                        ₹{discountAmount.toLocaleString('en-IN')} discount calculated — New base: ₹{discountedPrice.toLocaleString('en-IN')}
                    </p>
                )}
            </div>
        )}
    </div>

    <div className="flex items-center gap-3 flex-wrap">
        {/* Deduct ₹5,100 Pre-assessment fee toggle */}
        <label className="flex items-center gap-2 bg-white border border-fuchsia-200 rounded-lg px-3 py-2 cursor-pointer w-fit" data-testid="deduct-pa-fee-toggle">
            <input
                type="checkbox"
                checked={deductPaFee}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, deduct_pre_assessment_fee: e.target.checked })}
                className="h-4 w-4 text-fuchsia-600 rounded"
            />
            <span className="text-xs font-semibold text-slate-700">
                Deduct Pre-Assessment Fee (₹5,100 already paid)
            </span>
        </label>

        {/* GST 18% toggle — applies to ALL packages, domestic (India) clients only */}
        <label className="flex items-center gap-2 bg-white border border-fuchsia-200 rounded-lg px-3 py-2 cursor-pointer w-fit" data-testid="gst-toggle-label">
            <input
                type="checkbox"
                checked={includeGst}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, include_gst: e.target.checked })}
                className="h-4 w-4"
                data-testid="gst-toggle"
            />
            <span className="text-xs font-semibold text-slate-700">Add GST (18%)</span>
        </label>
    </div>

    {(includeGst || discountAmount > 0 || deductPaFee) && (
        <div className="bg-white border border-fuchsia-200 rounded-lg p-3 text-xs space-y-1">
        <div className="flex justify-between"><span className="text-slate-500">Base Package Fee</span><span className="font-semibold">₹{basePrice.toLocaleString('en-IN')}</span></div>
        {discountAmount > 0 && (
            <div className="flex justify-between text-emerald-700">
                <span>Coupon {selectedCoupon?.code} ({selectedCoupon?.discount_type === 'percentage' ? `${selectedCoupon.discount_value}%` : `₹${selectedCoupon.discount_value}`})</span>
                <span>-₹{discountAmount.toLocaleString('en-IN')}</span>
            </div>
        )}
        {deductPaFee && (
            <div className="flex justify-between text-emerald-700 font-semibold" data-testid="pa-fee-deduction-summary">
                <span>Pre-Assessment Fee Paid (Deduction)</span>
                <span>-₹5,100</span>
            </div>
        )}
        {includeGst && (
            <div className="flex justify-between"><span className="text-slate-500">GST (18%)</span><span className="font-semibold">₹{gstAmount.toLocaleString('en-IN')}</span></div>
        )}
        <div className="flex justify-between border-t border-slate-200 pt-1 mt-1"><span className="font-bold text-slate-700">Total Payable</span><span className="font-bold text-fuchsia-700">₹{totalAmount.toLocaleString('en-IN')}</span></div>
        </div>
    )}

    <div className="flex gap-2 flex-wrap">
        <button type="button"
        onClick={() => setPaymentMethodForm({ ...paymentMethodForm, payment_method_type: 'full_payment', installment_schedule: null })}
        className={`px-3 py-1.5 rounded text-xs font-semibold border ${paymentMethodForm.payment_method_type === 'full_payment' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white border-slate-300'}`}>
        Full Payment
        </button>
        <button type="button"
        onClick={() => {
            const firstValid = productWorkflowSteps.find(s => s.step_order >= 2) || productWorkflowSteps[0];
            setPaymentMethodForm({
                ...paymentMethodForm,
                payment_method_type: 'split_50_50',
                installment_schedule: null,
                second_installment_trigger_type: paymentMethodForm.second_installment_trigger_type || 'step',
                second_installment_step_order: paymentMethodForm.second_installment_step_order || (firstValid?.step_order || 4),
                second_installment_step_name: paymentMethodForm.second_installment_step_name || (firstValid?.step_name || 'Document Verification & Submission')
            });
        }}
        className={`px-3 py-1.5 rounded text-xs font-semibold border ${paymentMethodForm.payment_method_type === 'split_50_50' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white border-slate-300'}`}
        data-testid="split-50-50-btn">
        50-50 Split
        </button>
        <button type="button"
        onClick={() => setPaymentMethodForm({ ...paymentMethodForm, payment_method_type: 'installments', installment_schedule: [] })}
        className={`px-3 py-1.5 rounded text-xs font-semibold border ${paymentMethodForm.payment_method_type === 'installments' ? 'bg-amber-600 text-white border-amber-600' : 'bg-white border-slate-300'}`}>
        Installments (needs admin approval)
        </button>
    </div>

    {/* 👇 50-50 Split: Select Product Workflow Step or Specific Date Trigger */}
    {paymentMethodForm.payment_method_type === 'split_50_50' && (
        <div className="bg-white border border-fuchsia-200 rounded-lg p-3 space-y-3" data-testid="split-50-50-trigger-box">
            <div className="flex items-center justify-between">
                <p className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <span>⚡ 2nd Installment (50%) Unlock Condition</span>
                </p>
                <span className="text-[11px] font-semibold text-fuchsia-700 bg-fuchsia-50 border border-fuchsia-200 px-2 py-0.5 rounded-full">
                    2nd Part: ₹{Math.max(0, totalAmount - Math.round(totalAmount / 2)).toLocaleString('en-IN')} (50%)
                </span>
            </div>

            {/* Selected Product & Workflow steps preview */}
            <div className="bg-slate-50 border border-slate-200 rounded p-2.5 text-xs space-y-1.5">
                <p className="font-semibold text-slate-700">
                    Product: <span className="text-fuchsia-700 font-bold">{pa.product_name || 'Selected Service'}</span>
                </p>
                <p className="text-[11px] text-slate-500 font-medium">Configured Workflow Steps:</p>
                {loadingWorkflow ? (
                    <p className="text-[11px] text-slate-400">Loading product workflow steps…</p>
                ) : productWorkflowSteps.length > 0 ? (
                    <div className="flex gap-1.5 flex-wrap pt-0.5">
                        {productWorkflowSteps.map(s => {
                            const isChosen = (paymentMethodForm.second_installment_trigger_type || 'step') === 'step' && Number(paymentMethodForm.second_installment_step_order || 4) === Number(s.step_order);
                            return (
                                <span key={s.step_order} className={`text-[10px] px-2 py-0.5 rounded font-medium border ${isChosen ? 'bg-fuchsia-600 text-white border-fuchsia-600 font-bold shadow-xs' : 'bg-white text-slate-600 border-slate-200'}`}>
                                    Step {s.step_order}: {s.step_name} {isChosen ? '★' : ''}
                                </span>
                            );
                        })}
                    </div>
                ) : (
                    <p className="text-[11px] text-slate-400 italic">Standard workflow configured for this product.</p>
                )}
            </div>

            {/* Mutually Exclusive Trigger Selector */}
            <div className="space-y-2 pt-1">
                <p className="text-[11px] font-semibold text-slate-600 uppercase tracking-wide">
                    Choose when the 2nd Installment becomes payable (Select One):
                </p>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {/* Option 1: By Workflow Step */}
                    <label className={`flex items-start gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-all ${
                        (paymentMethodForm.second_installment_trigger_type || 'step') === 'step'
                            ? 'bg-fuchsia-50/70 border-fuchsia-400 ring-1 ring-fuchsia-400'
                            : 'bg-white border-slate-200 hover:border-slate-300'
                    }`}>
                        <input
                            type="radio"
                            name="installment_trigger_type"
                            value="step"
                            checked={(paymentMethodForm.second_installment_trigger_type || 'step') === 'step'}
                            onChange={() => {
                                const firstValid = productWorkflowSteps.find(s => s.step_order >= 2) || productWorkflowSteps[0];
                                setPaymentMethodForm({
                                    ...paymentMethodForm,
                                    second_installment_trigger_type: 'step',
                                    second_installment_step_order: paymentMethodForm.second_installment_step_order || (firstValid?.step_order || 4),
                                    second_installment_step_name: paymentMethodForm.second_installment_step_name || (firstValid?.step_name || 'Document Verification & Submission'),
                                    second_installment_due_date: null
                                });
                            }}
                            className="mt-0.5 text-fuchsia-600"
                            data-testid="trigger-type-step"
                        />
                        <div className="space-y-1.5 flex-1 min-w-0">
                            <span className="text-xs font-bold text-slate-800 block">At a Specific Workflow Step</span>
                            <p className="text-[11px] text-slate-500">Unlocks when the case advances to the selected step.</p>
                            
                            {(paymentMethodForm.second_installment_trigger_type || 'step') === 'step' && (
                                <select
                                    value={paymentMethodForm.second_installment_step_order || 4}
                                    onChange={(e) => {
                                        const order = parseInt(e.target.value);
                                        const matched = productWorkflowSteps.find(s => s.step_order === order);
                                        setPaymentMethodForm({
                                            ...paymentMethodForm,
                                            second_installment_trigger_type: 'step',
                                            second_installment_step_order: order,
                                            second_installment_step_name: matched?.step_name || `Step ${order}`,
                                            second_installment_due_date: null
                                        });
                                    }}
                                    className="w-full border border-fuchsia-300 rounded px-2 py-1 text-xs bg-white mt-1 font-medium"
                                    data-testid="select-trigger-step"
                                >
                                    {productWorkflowSteps.length > 0 ? (
                                        productWorkflowSteps.map(s => (
                                            <option key={s.step_order} value={s.step_order}>
                                                Step {s.step_order}: {s.step_name}
                                            </option>
                                        ))
                                    ) : (
                                        <>
                                            <option value={2}>Step 2: Document Verification</option>
                                            <option value={3}>Step 3: Eligibility & Assessment</option>
                                            <option value={4}>Step 4: Submission & Filing</option>
                                        </>
                                    )}
                                </select>
                            )}
                        </div>
                    </label>

                    {/* Option 2: By Due Date */}
                    <label className={`flex items-start gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-all ${
                        paymentMethodForm.second_installment_trigger_type === 'date'
                            ? 'bg-fuchsia-50/70 border-fuchsia-400 ring-1 ring-fuchsia-400'
                            : 'bg-white border-slate-200 hover:border-slate-300'
                    }`}>
                        <input
                            type="radio"
                            name="installment_trigger_type"
                            value="date"
                            checked={paymentMethodForm.second_installment_trigger_type === 'date'}
                            onChange={() => {
                                setPaymentMethodForm({
                                    ...paymentMethodForm,
                                    second_installment_trigger_type: 'date',
                                    second_installment_step_order: null,
                                    second_installment_step_name: null,
                                    second_installment_due_date: paymentMethodForm.second_installment_due_date || new Date(Date.now() + 30*24*60*60*1000).toISOString().split('T')[0]
                                });
                            }}
                            className="mt-0.5 text-fuchsia-600"
                            data-testid="trigger-type-date"
                        />
                        <div className="space-y-1.5 flex-1 min-w-0">
                            <span className="text-xs font-bold text-slate-800 block">On a Specific Date</span>
                            <p className="text-[11px] text-slate-500">Unlocks on the exact calendar due date.</p>

                            {paymentMethodForm.second_installment_trigger_type === 'date' && (
                                <input
                                    type="date"
                                    value={paymentMethodForm.second_installment_due_date || ''}
                                    onChange={(e) => {
                                        setPaymentMethodForm({
                                            ...paymentMethodForm,
                                            second_installment_trigger_type: 'date',
                                            second_installment_due_date: e.target.value,
                                            second_installment_step_order: null,
                                            second_installment_step_name: null
                                        });
                                    }}
                                    className="w-full border border-fuchsia-300 rounded px-2 py-1 text-xs bg-white mt-1 font-medium"
                                    data-testid="input-trigger-date"
                                />
                            )}
                        </div>
                    </label>
                </div>

                {/* Explanation banner */}
                <div className="bg-amber-50 border border-amber-200 rounded p-2 text-[11px] text-amber-800 mt-2">
                    <strong>Gating Rule:</strong>{' '}
                    {(paymentMethodForm.second_installment_trigger_type || 'step') === 'step' ? (
                        <span>
                            Client’s second installment (₹{Math.max(0, totalAmount - Math.round(totalAmount / 2)).toLocaleString('en-IN')}) will unlock when <strong>Step {paymentMethodForm.second_installment_step_order || 4} ({paymentMethodForm.second_installment_step_name || 'Document Verification & Submission'})</strong> is reached. Progression beyond Step {paymentMethodForm.second_installment_step_order || 4} will remain locked until payment is completed.
                        </span>
                    ) : (
                        <span>
                            Client’s second installment (₹{Math.max(0, totalAmount - Math.round(totalAmount / 2)).toLocaleString('en-IN')}) will be due on <strong>{paymentMethodForm.second_installment_due_date || 'the selected date'}</strong>.
                        </span>
                    )}
                </div>
            </div>
        </div>
    )}

    {isInstallments && (
        <InstallmentEditor
        totalAmount={totalAmount}
        schedule={paymentMethodForm.installment_schedule || []}
        onChange={(sch) => setPaymentMethodForm({ ...paymentMethodForm, installment_schedule: sch })}
        />
    )}

    <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => handleFinalizePaymentMethod(pa.id)}
        className="bg-fuchsia-600 hover:bg-fuchsia-700" data-testid="submit-payment-method">
        <Send className="h-4 w-4 mr-1" /> {isInstallments ? 'Send for Admin Approval' : 'Confirm & Notify Client'}
        </Button>
    </div>
    </div>
);
}