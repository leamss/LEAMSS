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

    // 👇 NEW — Coupon-based discount
    const [coupons, setCoupons] = useState([]);
    const [loadingCoupons, setLoadingCoupons] = useState(true);
    useEffect(() => {
        if (!pa.product_id) { setLoadingCoupons(false); return; }
        axios.get(`${API}/products/${pa.product_id}/coupons`, getAuthHeader())
            .then(r => setCoupons(r.data.coupons || []))
            .catch(() => setCoupons([]))
            .finally(() => setLoadingCoupons(false));
    }, [pa.product_id]);

    const selectedCoupon = coupons.find(c => c.code === paymentMethodForm.coupon_code) || null;
    let discountAmount = 0;
    if (selectedCoupon) {
        discountAmount = selectedCoupon.discount_type === 'percentage'
            ? Math.round(basePrice * selectedCoupon.discount_value / 100)
            : Math.round(selectedCoupon.discount_value);
        discountAmount = Math.min(discountAmount, basePrice);
    }
    const discountedPrice = Math.max(0, basePrice - discountAmount);

    const includeGst = paymentMethodForm.include_gst || false;
    const gstAmount = includeGst ? Math.round(discountedPrice * 0.18) : 0;
    const totalAmount = discountedPrice + gstAmount || null;
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

{/* 👇 NEW — Discount coupon (admin-defined, per product) */}
    <div className="bg-white border border-fuchsia-200 rounded-lg p-3 space-y-2">
        <p className="text-xs font-semibold text-slate-700">Apply Discount Coupon (optional)</p>
        {loadingCoupons ? (
            <p className="text-xs text-slate-400">Loading coupons…</p>
        ) : coupons.length === 0 ? (
            <p className="text-xs text-slate-400 italic">No active coupons for this product. Ask admin to add one.</p>
        ) : (
            <select
                value={paymentMethodForm.coupon_code || ''}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, coupon_code: e.target.value || null })}
                className="w-full border border-fuchsia-200 rounded-md px-3 py-2 text-sm bg-white"
                data-testid="coupon-select"
            >
                <option value="">— No coupon —</option>
                {coupons.map(c => (
                    <option key={c.id} value={c.code}>
                        {c.code} — {c.discount_type === 'percentage' ? `${c.discount_value}% off` : `₹${c.discount_value} off`}
                        {c.notes ? ` (${c.notes})` : ''}
                    </option>
                ))}
            </select>
        )}
        {discountAmount > 0 && (
            <p className="text-xs font-semibold text-emerald-700">
                ₹{discountAmount.toLocaleString('en-IN')} discount applied — New price: ₹{discountedPrice.toLocaleString('en-IN')}
            </p>
        )}
    </div>

    {/* GST 18% toggle — applies to ALL packages, domestic (India) clients only */}
    <label className="flex items-center gap-2 bg-white border border-fuchsia-200 rounded-lg px-3 py-2 cursor-pointer w-fit">
        <input
        type="checkbox"
        checked={includeGst}
        onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, include_gst: e.target.checked })}
        className="h-4 w-4"
        data-testid="gst-toggle"
        />
        <span className="text-xs font-semibold text-slate-700">Add GST (18%)</span>
    </label>

    {(includeGst || discountAmount > 0) && (
        <div className="bg-white border border-fuchsia-200 rounded-lg p-3 text-xs space-y-1">
        <div className="flex justify-between"><span className="text-slate-500">Base Service Fee</span><span className="font-semibold">₹{basePrice.toLocaleString('en-IN')}</span></div>
        {discountAmount > 0 && (
            <div className="flex justify-between text-emerald-700">
                <span>Coupon {selectedCoupon?.code} ({selectedCoupon?.discount_type === 'percentage' ? `${selectedCoupon.discount_value}%` : `₹${selectedCoupon.discount_value}`})</span>
                <span>-₹{discountAmount.toLocaleString('en-IN')}</span>
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
        onClick={() => setPaymentMethodForm({ payment_method_type: 'full_payment', installment_schedule: null })}
        className={`px-3 py-1.5 rounded text-xs font-semibold border ${paymentMethodForm.payment_method_type === 'full_payment' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white border-slate-300'}`}>
        Full Payment
        </button>
        <button type="button"
        onClick={() => setPaymentMethodForm({ payment_method_type: 'split_50_50', installment_schedule: null })}
        className={`px-3 py-1.5 rounded text-xs font-semibold border ${paymentMethodForm.payment_method_type === 'split_50_50' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white border-slate-300'}`}>
        50-50 Split
        </button>
        <button type="button"
        onClick={() => setPaymentMethodForm({ payment_method_type: 'installments', installment_schedule: [] })}
        className={`px-3 py-1.5 rounded text-xs font-semibold border ${paymentMethodForm.payment_method_type === 'installments' ? 'bg-amber-600 text-white border-amber-600' : 'bg-white border-slate-300'}`}>
        Installments (needs admin approval)
        </button>
    </div>

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