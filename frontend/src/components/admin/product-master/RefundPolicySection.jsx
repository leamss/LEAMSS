import React, { useState, useEffect, useMemo, useRef } from 'react';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import {
  ShieldCheck, ShieldAlert, CheckCircle2, AlertTriangle,
  Plus, Trash2, DollarSign, Calendar, Clock, Eye, BarChart3,
  X, Check, RefreshCw, FileText, Layers, Tag, Save
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

const defaultPolicyTypeConfigs = {
  protection: {
    name: 'LEAMSS Protection Policy Guarantee',
    refundable_service_fee_pct: 100,
    is_service_fee_refundable: true,
    negative_skills_assessment_guarantee: true,
    visa_refusal_guarantee: true,
    voluntary_withdrawal_milestones: true,
    package_overrides: {
      standard: { name: 'Standard Tier', enabled: true, refundable_pct: 100 },
      smart: { name: 'Smart Tier', enabled: true, refundable_pct: 100 },
      premium: { name: 'Premium Tier', enabled: true, refundable_pct: 100 }
    }
  },
  standard: {
    name: 'LEAMSS Milestone-Based Refund Policy',
    refundable_service_fee_pct: 50,
    is_service_fee_refundable: true,
    negative_skills_assessment_guarantee: true,
    visa_refusal_guarantee: false,
    voluntary_withdrawal_milestones: true,
    package_overrides: {
      standard: { name: 'Standard Tier', enabled: true, refundable_pct: 50 },
      smart: { name: 'Smart Tier', enabled: true, refundable_pct: 50 },
      premium: { name: 'Premium Tier', enabled: true, refundable_pct: 50 }
    }
  },
  no_refund: {
    name: 'No Refund Policy',
    refundable_service_fee_pct: 0,
    is_service_fee_refundable: false,
    negative_skills_assessment_guarantee: false,
    visa_refusal_guarantee: false,
    voluntary_withdrawal_milestones: false,
    package_overrides: {
      standard: { name: 'Standard Tier', enabled: true, refundable_pct: 0 },
      smart: { name: 'Smart Tier', enabled: true, refundable_pct: 0 },
      premium: { name: 'Premium Tier', enabled: true, refundable_pct: 0 }
    }
  }
};

const defaultPolicy = {
  enabled: true,
  policy_type: 'protection', // 'protection' | 'standard' | 'no_refund'
  name: 'LEAMSS Protection Policy Guarantee',
  refundable_service_fee_pct: 100,
  is_service_fee_refundable: true,
  govt_fees_handling: 'non_refundable',
  is_govt_fee_refundable: false,
  gst_treatment: 'credit_note',
  negative_skills_assessment_guarantee: true,
  visa_refusal_guarantee: true,
  voluntary_withdrawal_milestones: true,
  claim_window_days: 30,
  payout_time_days: 14,
  maker_checker_required: true,
  custom_fee_components: [],
  custom_guaranteed_triggers: [],
  conditions: [
    '100% genuine documentation provided without omissions',
    'Client responds to case manager queries within 7 working days',
    'Medical examination and police clearance certificates passed without adverse records'
  ],
  exclusions: [
    'Rejection caused by fraudulent, forged or misleading documents',
    'Undisclosed prior medical condition or criminal conviction',
    'Statutory quota exhaustion or material change in destination country immigration law',
    'Client voluntary withdrawal after release of document checklist and case dossier',
    'Failure to achieve required statutory English test scores (IELTS/PTE)'
  ],
  package_overrides: {
    standard: { name: 'Standard Tier', enabled: true, refundable_pct: 100 },
    smart: { name: 'Smart Tier', enabled: true, refundable_pct: 100 },
    premium: { name: 'Premium Tier', enabled: true, refundable_pct: 100 }
  },
  policy_type_configs: defaultPolicyTypeConfigs,
  version: 1
};

export const mergePolicyWithDefaults = (initial, defaults = defaultPolicy) => {
  if (!initial) return { ...defaults };
  const activeType = initial.policy_type || defaults.policy_type || 'protection';
  const defActiveConfig = defaultPolicyTypeConfigs[activeType] || defaultPolicyTypeConfigs.protection;

  const activeBasePct = initial.refundable_service_fee_pct !== undefined && initial.refundable_service_fee_pct !== null
    ? Number(initial.refundable_service_fee_pct)
    : defActiveConfig.refundable_service_fee_pct;

  const initialConfigs = initial.policy_type_configs && typeof initial.policy_type_configs === 'object'
    ? initial.policy_type_configs
    : {};

  const mergedConfigs = {};

  ['protection', 'standard', 'no_refund'].forEach((typeKey) => {
    const defForType = defaultPolicyTypeConfigs[typeKey];
    const savedForType = initialConfigs[typeKey];

    if (savedForType) {
      const typeBasePct = savedForType.refundable_service_fee_pct !== undefined && savedForType.refundable_service_fee_pct !== null
        ? Number(savedForType.refundable_service_fee_pct)
        : defForType.refundable_service_fee_pct;

      const typeOverrides = {};
      Object.entries(defForType.package_overrides || {}).forEach(([k, v]) => {
        typeOverrides[k] = { ...v, refundable_pct: typeBasePct };
      });
      if (savedForType.package_overrides && typeof savedForType.package_overrides === 'object') {
        Object.entries(savedForType.package_overrides).forEach(([k, v]) => {
          typeOverrides[k] = {
            ...(typeOverrides[k] || {}),
            ...v,
            refundable_pct: v?.refundable_pct !== undefined && v?.refundable_pct !== null
              ? Number(v.refundable_pct)
              : typeBasePct
          };
        });
      }
      mergedConfigs[typeKey] = {
        ...defForType,
        ...savedForType,
        refundable_service_fee_pct: typeBasePct,
        package_overrides: typeOverrides
      };
    } else if (typeKey === activeType) {
      const typeOverrides = {};
      Object.entries(defForType.package_overrides || {}).forEach(([k, v]) => {
        typeOverrides[k] = { ...v, refundable_pct: activeBasePct };
      });
      if (initial.package_overrides && typeof initial.package_overrides === 'object') {
        Object.entries(initial.package_overrides).forEach(([k, v]) => {
          typeOverrides[k] = {
            ...(typeOverrides[k] || {}),
            ...v,
            refundable_pct: v?.refundable_pct !== undefined && v?.refundable_pct !== null
              ? Number(v.refundable_pct)
              : activeBasePct
          };
        });
      }
      mergedConfigs[typeKey] = {
        ...defForType,
        refundable_service_fee_pct: activeBasePct,
        is_service_fee_refundable: initial.is_service_fee_refundable !== undefined
          ? initial.is_service_fee_refundable
          : defForType.is_service_fee_refundable,
        negative_skills_assessment_guarantee: initial.negative_skills_assessment_guarantee !== undefined
          ? initial.negative_skills_assessment_guarantee
          : defForType.negative_skills_assessment_guarantee,
        visa_refusal_guarantee: initial.visa_refusal_guarantee !== undefined
          ? initial.visa_refusal_guarantee
          : defForType.visa_refusal_guarantee,
        voluntary_withdrawal_milestones: initial.voluntary_withdrawal_milestones !== undefined
          ? initial.voluntary_withdrawal_milestones
          : defForType.voluntary_withdrawal_milestones,
        package_overrides: typeOverrides
      };
    } else {
      mergedConfigs[typeKey] = {
        ...defForType,
        package_overrides: { ...defForType.package_overrides }
      };
    }
  });

  const activeOverrides = mergedConfigs[activeType]?.package_overrides || {
    standard: { name: 'Standard Tier', enabled: true, refundable_pct: activeBasePct },
    smart: { name: 'Smart Tier', enabled: true, refundable_pct: activeBasePct },
    premium: { name: 'Premium Tier', enabled: true, refundable_pct: activeBasePct }
  };

  return {
    ...defaults,
    ...initial,
    policy_type: activeType,
    name: initial.name || defActiveConfig.name,
    refundable_service_fee_pct: activeBasePct,
    custom_fee_components: Array.isArray(initial.custom_fee_components)
      ? initial.custom_fee_components
      : (defaults.custom_fee_components || []),
    custom_guaranteed_triggers: Array.isArray(initial.custom_guaranteed_triggers)
      ? initial.custom_guaranteed_triggers
      : (defaults.custom_guaranteed_triggers || []),
    conditions: Array.isArray(initial.conditions) && initial.conditions.length > 0
      ? initial.conditions
      : defaults.conditions,
    exclusions: Array.isArray(initial.exclusions) && initial.exclusions.length > 0
      ? initial.exclusions
      : defaults.exclusions,
    package_overrides: activeOverrides,
    policy_type_configs: mergedConfigs,
  };
};

export default function RefundPolicySection({
  product,
  refundPolicy: initialRefundPolicy,
  onChange,
  onSaved,
  readOnly = false
}) {
  const [policy, setPolicy] = useState(() => mergePolicyWithDefaults(initialRefundPolicy, defaultPolicy));
  const [savingPolicy, setSavingPolicy] = useState(false);
  const lastProductIdRef = useRef(product?.id);
  const isInternalChangeRef = useRef(false);

  const [newCondition, setNewCondition] = useState('');
  const [newExclusion, setNewExclusion] = useState('');
  const [showFinanceModal, setShowFinanceModal] = useState(false);
  const [financeReport, setFinanceReport] = useState(null);
  const [financeLoading, setFinanceLoading] = useState(false);

  useEffect(() => {
    if (product?.id !== lastProductIdRef.current) {
      lastProductIdRef.current = product?.id;
      setPolicy(mergePolicyWithDefaults(initialRefundPolicy, defaultPolicy));
    } else if (!isInternalChangeRef.current && initialRefundPolicy) {
      setPolicy(mergePolicyWithDefaults(initialRefundPolicy, defaultPolicy));
    }
    isInternalChangeRef.current = false;
  }, [product?.id, initialRefundPolicy]);

  const updateField = (field, value) => {
    isInternalChangeRef.current = true;
    let updatedOverrides = policy.package_overrides;
    const curType = policy.policy_type || 'protection';

    if (field === 'refundable_service_fee_pct' && value !== '') {
      const numVal = Math.min(100, Math.max(0, Number(value)));
      const oldBase = policy.refundable_service_fee_pct != null ? Number(policy.refundable_service_fee_pct) : 100;
      if (policy.package_overrides) {
        updatedOverrides = { ...policy.package_overrides };
        Object.entries(updatedOverrides).forEach(([k, v]) => {
          if (v && (v.refundable_pct == null || Number(v.refundable_pct) === oldBase)) {
            updatedOverrides[k] = { ...v, refundable_pct: numVal };
          }
        });
      }
    }

    const updatedConfigs = {
      ...(policy.policy_type_configs || {}),
      [curType]: {
        ...((policy.policy_type_configs || {})[curType] || {}),
        ...(field === 'refundable_service_fee_pct'
          ? { refundable_service_fee_pct: value, package_overrides: updatedOverrides }
          : { [field]: value })
      }
    };

    const updated = {
      ...policy,
      [field]: value,
      ...(updatedOverrides ? { package_overrides: updatedOverrides } : {}),
      policy_type_configs: updatedConfigs
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handleSavePolicyDirect = async () => {
    if (!product?.id) {
      toast.error('No product selected');
      return;
    }
    setSavingPolicy(true);
    try {
      const curType = policy.policy_type || 'protection';
      const defActiveConfig = defaultPolicyTypeConfigs[curType] || defaultPolicyTypeConfigs.protection;
      const normalizedBasePct = policy.refundable_service_fee_pct === '' || policy.refundable_service_fee_pct == null
        ? defActiveConfig.refundable_service_fee_pct
        : Math.min(100, Math.max(0, Number(policy.refundable_service_fee_pct)));

      // Normalize package overrides
      const normalizedOverrides = {};
      packageOverrideEntries.forEach((entry) => {
        const saved = (policy.package_overrides || {})[entry.key] || {};
        normalizedOverrides[entry.key] = {
          ...saved,
          name: entry.name,
          enabled: entry.enabled !== false,
          refundable_pct: entry.refundable_pct === '' || entry.refundable_pct == null
            ? normalizedBasePct
            : Math.min(100, Math.max(0, Number(entry.refundable_pct)))
        };
      });

      const updatedConfigs = {
        ...(policy.policy_type_configs || {}),
        [curType]: {
          ...((policy.policy_type_configs || {})[curType] || {}),
          refundable_service_fee_pct: normalizedBasePct,
          package_overrides: normalizedOverrides,
          is_service_fee_refundable: policy.is_service_fee_refundable,
          negative_skills_assessment_guarantee: policy.negative_skills_assessment_guarantee,
          visa_refusal_guarantee: policy.visa_refusal_guarantee,
          voluntary_withdrawal_milestones: policy.voluntary_withdrawal_milestones,
        }
      };

      const normalizedPolicy = {
        ...policy,
        refundable_service_fee_pct: normalizedBasePct,
        package_overrides: normalizedOverrides,
        policy_type_configs: updatedConfigs,
      };

      const token = localStorage.getItem('token');
      const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await axios.put(`${API}/product-master/${product.id}`, {
        ...product,
        refund_policy: normalizedPolicy,
      }, { headers: authHeader });

      setPolicy(normalizedPolicy);
      toast.success('Refund Policy & Statutory Safeguards updated successfully!');
      if (onSaved) {
        await onSaved(product.id, res.data?.product);
      }
    } catch (err) {
      console.error('Failed to save refund policy:', err);
      toast.error(err.response?.data?.detail || 'Failed to update Refund Policy');
    } finally {
      setSavingPolicy(false);
    }
  };

  const handleTypeChange = (type) => {
    isInternalChangeRef.current = true;
    const curType = policy.policy_type || 'protection';

    // 1. Snapshot current active type's values
    const currentConfigs = {
      ...(policy.policy_type_configs || {}),
      [curType]: {
        ...((policy.policy_type_configs || {})[curType] || {}),
        refundable_service_fee_pct: policy.refundable_service_fee_pct,
        package_overrides: policy.package_overrides,
        is_service_fee_refundable: policy.is_service_fee_refundable,
        negative_skills_assessment_guarantee: policy.negative_skills_assessment_guarantee,
        visa_refusal_guarantee: policy.visa_refusal_guarantee,
        voluntary_withdrawal_milestones: policy.voluntary_withdrawal_milestones,
      }
    };

    // 2. Load target type's values
    const targetConfig = currentConfigs[type] || defaultPolicyTypeConfigs[type] || defaultPolicyTypeConfigs.protection;
    const targetBasePct = targetConfig.refundable_service_fee_pct !== undefined && targetConfig.refundable_service_fee_pct !== null
      ? (targetConfig.refundable_service_fee_pct === '' ? '' : Number(targetConfig.refundable_service_fee_pct))
      : (type === 'protection' ? 100 : type === 'standard' ? 50 : 0);

    const targetOverrides = targetConfig.package_overrides || {
      standard: { name: 'Standard Tier', enabled: true, refundable_pct: targetBasePct || 0 },
      smart: { name: 'Smart Tier', enabled: true, refundable_pct: targetBasePct || 0 },
      premium: { name: 'Premium Tier', enabled: true, refundable_pct: targetBasePct || 0 }
    };

    const updated = {
      ...policy,
      policy_type: type,
      name: targetConfig.name || (type === 'protection'
        ? 'LEAMSS Protection Policy Guarantee'
        : type === 'standard'
          ? 'LEAMSS Milestone-Based Refund Policy'
          : 'No Refund Policy'),
      refundable_service_fee_pct: targetBasePct,
      is_service_fee_refundable: targetConfig.is_service_fee_refundable !== undefined
        ? targetConfig.is_service_fee_refundable
        : (type !== 'no_refund'),
      negative_skills_assessment_guarantee: targetConfig.negative_skills_assessment_guarantee !== undefined
        ? targetConfig.negative_skills_assessment_guarantee
        : (type !== 'no_refund'),
      visa_refusal_guarantee: targetConfig.visa_refusal_guarantee !== undefined
        ? targetConfig.visa_refusal_guarantee
        : (type === 'protection'),
      voluntary_withdrawal_milestones: targetConfig.voluntary_withdrawal_milestones !== undefined
        ? targetConfig.voluntary_withdrawal_milestones
        : (type !== 'no_refund'),
      package_overrides: targetOverrides,
      policy_type_configs: currentConfigs
    };

    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  // 1. Fee Breakdown & Tax Treatment Custom Options
  const handleAddCustomFeeComponent = () => {
    isInternalChangeRef.current = true;
    const newItem = {
      id: `fee_${Date.now()}`,
      name: 'Administrative File Processing Charge',
      type: 'non_refundable', // 'non_refundable' | 'deduct_flat' | 'percentage'
      value: 15000,
      description: 'Retained for preliminary profile vetting & file compilation'
    };
    const updated = {
      ...policy,
      custom_fee_components: [...(policy.custom_fee_components || []), newItem]
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handleUpdateCustomFeeComponent = (idx, field, val) => {
    isInternalChangeRef.current = true;
    const list = [...(policy.custom_fee_components || [])];
    list[idx] = { ...list[idx], [field]: val };
    const updated = { ...policy, custom_fee_components: list };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handleRemoveCustomFeeComponent = (idx) => {
    isInternalChangeRef.current = true;
    const list = (policy.custom_fee_components || []).filter((_, i) => i !== idx);
    const updated = { ...policy, custom_fee_components: list };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  // 2. Guaranteed Triggers Custom Options
  const handleAddCustomTrigger = () => {
    isInternalChangeRef.current = true;
    const newTrig = {
      id: `trig_${Date.now()}`,
      name: 'State Nomination Rejection Guarantee',
      description: '100% refund if designated state authority rejects valid state EOI nomination',
      enabled: true,
      refund_pct: 100
    };
    const updated = {
      ...policy,
      custom_guaranteed_triggers: [...(policy.custom_guaranteed_triggers || []), newTrig]
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handleUpdateCustomTrigger = (idx, field, val) => {
    isInternalChangeRef.current = true;
    const list = [...(policy.custom_guaranteed_triggers || [])];
    list[idx] = { ...list[idx], [field]: val };
    const updated = { ...policy, custom_guaranteed_triggers: list };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handleRemoveCustomTrigger = (idx) => {
    isInternalChangeRef.current = true;
    const list = (policy.custom_guaranteed_triggers || []).filter((_, i) => i !== idx);
    const updated = { ...policy, custom_guaranteed_triggers: list };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  // 3. Package-Wise Overrides (Standard, Smart, Premium + Product Packages + Custom Tiers)
  const packageOverrideEntries = useMemo(() => {
    const existing = policy.package_overrides || {};
    const entriesMap = new Map();
    const basePct = policy.refundable_service_fee_pct !== undefined && policy.refundable_service_fee_pct !== null
      ? Number(policy.refundable_service_fee_pct)
      : 100;

    // 1. Standard default tiers (standard, smart, premium)
    const defaultTiers = [
      { key: 'standard', name: 'Standard Tier', isDefault: true },
      { key: 'smart', name: 'Smart Tier', isDefault: true },
      { key: 'premium', name: 'Premium Tier', isDefault: true },
    ];
    defaultTiers.forEach((t) => {
      const savedTier = existing[t.key] || {};
      entriesMap.set(t.key, {
        key: t.key,
        name: savedTier.name || t.name,
        enabled: savedTier.enabled !== false,
        refundable_pct: savedTier.refundable_pct !== undefined && savedTier.refundable_pct !== null
          ? Number(savedTier.refundable_pct)
          : basePct,
        isDefault: true,
        ...savedTier,
      });
    });

    // 2. Add or merge packages defined under Section 3 (product.packages)
    if (Array.isArray(product?.packages)) {
      product.packages.forEach((p, idx) => {
        const pkgType = (p.package_type || '').toLowerCase();
        let pKey = p.id;
        if (!pKey) {
          if (pkgType === 'standard' || pkgType === 'smart' || pkgType === 'premium') {
            pKey = pkgType;
          } else {
            pKey = `pkg_${idx}`;
          }
        } else if (pkgType === 'standard' || pkgType === 'smart' || pkgType === 'premium') {
          if (!existing[pKey] && existing[pkgType]) {
            pKey = pkgType;
          }
        }

        const savedTier = existing[pKey] || existing[pkgType] || existing[p.name] || {};
        const existingEntry = entriesMap.get(pKey);

        entriesMap.set(pKey, {
          key: pKey,
          name: p.name || existingEntry?.name || `${pkgType.charAt(0).toUpperCase() + pkgType.slice(1)} Tier`,
          enabled: p.is_active !== false && savedTier.enabled !== false,
          refundable_pct: savedTier.refundable_pct !== undefined && savedTier.refundable_pct !== null
            ? Number(savedTier.refundable_pct)
            : (existingEntry?.refundable_pct !== undefined ? existingEntry.refundable_pct : basePct),
          isDefault: !!existingEntry?.isDefault,
          isFromProductPackages: true,
          price: p.price,
          ...savedTier,
        });
      });
    }

    // 3. Add any standalone custom overrides in existing package_overrides
    Object.keys(existing).forEach((k) => {
      if (!entriesMap.has(k)) {
        const savedTier = existing[k] || {};
        entriesMap.set(k, {
          key: k,
          name: savedTier.name || `${k.charAt(0).toUpperCase() + k.slice(1)} Tier`,
          enabled: savedTier.enabled !== false,
          refundable_pct: savedTier.refundable_pct !== undefined && savedTier.refundable_pct !== null
            ? Number(savedTier.refundable_pct)
            : basePct,
          is_custom: true,
          isDefault: false,
          ...savedTier,
        });
      }
    });

    return Array.from(entriesMap.values());
  }, [policy.package_overrides, policy.refundable_service_fee_pct, product?.packages]);

  const handleAddPackageOverride = () => {
    isInternalChangeRef.current = true;
    const curType = policy.policy_type || 'protection';
    const basePct = policy.refundable_service_fee_pct !== undefined && policy.refundable_service_fee_pct !== null
      ? Number(policy.refundable_service_fee_pct)
      : 100;
    const key = `custom_pkg_${Date.now()}`;
    const newPkg = {
      name: 'Custom Package Tier',
      enabled: true,
      refundable_pct: basePct,
      is_custom: true
    };
    const updatedOverrides = {
      ...(policy.package_overrides || {}),
      [key]: newPkg
    };
    const updatedConfigs = {
      ...(policy.policy_type_configs || {}),
      [curType]: {
        ...((policy.policy_type_configs || {})[curType] || {}),
        package_overrides: updatedOverrides
      }
    };
    const updated = {
      ...policy,
      package_overrides: updatedOverrides,
      policy_type_configs: updatedConfigs
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handlePackageOverrideChange = (pkgKey, field, val) => {
    isInternalChangeRef.current = true;
    const curType = policy.policy_type || 'protection';
    const basePct = policy.refundable_service_fee_pct !== undefined && policy.refundable_service_fee_pct !== null
      ? Number(policy.refundable_service_fee_pct)
      : 100;
    const current = (policy.package_overrides || {})[pkgKey] || {
      name: pkgKey.charAt(0).toUpperCase() + pkgKey.slice(1) + ' Tier',
      enabled: true,
      refundable_pct: basePct
    };
    const processedVal = field === 'refundable_pct'
      ? (val === '' ? '' : Math.min(100, Math.max(0, Number(val) || 0)))
      : val;
    const updatedOverrides = {
      ...(policy.package_overrides || {}),
      [pkgKey]: {
        ...current,
        [field]: processedVal
      }
    };
    const updatedConfigs = {
      ...(policy.policy_type_configs || {}),
      [curType]: {
        ...((policy.policy_type_configs || {})[curType] || {}),
        package_overrides: updatedOverrides
      }
    };
    const updated = {
      ...policy,
      package_overrides: updatedOverrides,
      policy_type_configs: updatedConfigs
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handleRemovePackageOverride = (pkgKey) => {
    isInternalChangeRef.current = true;
    const curType = policy.policy_type || 'protection';
    const updatedOverrides = { ...(policy.package_overrides || {}) };
    delete updatedOverrides[pkgKey];
    const updatedConfigs = {
      ...(policy.policy_type_configs || {}),
      [curType]: {
        ...((policy.policy_type_configs || {})[curType] || {}),
        package_overrides: updatedOverrides
      }
    };
    const updated = {
      ...policy,
      package_overrides: updatedOverrides,
      policy_type_configs: updatedConfigs
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  // Conditions & Exclusions
  const handleAddCondition = () => {
    if (!newCondition.trim()) return;
    isInternalChangeRef.current = true;
    const updated = {
      ...policy,
      conditions: [...(policy.conditions || []), newCondition.trim()]
    };
    setPolicy(updated);
    setNewCondition('');
    if (onChange) onChange(updated);
  };

  const handleRemoveCondition = (idx) => {
    isInternalChangeRef.current = true;
    const updated = {
      ...policy,
      conditions: (policy.conditions || []).filter((_, i) => i !== idx)
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const handleAddExclusion = () => {
    if (!newExclusion.trim()) return;
    isInternalChangeRef.current = true;
    const updated = {
      ...policy,
      exclusions: [...(policy.exclusions || []), newExclusion.trim()]
    };
    setPolicy(updated);
    setNewExclusion('');
    if (onChange) onChange(updated);
  };

  const handleRemoveExclusion = (idx) => {
    isInternalChangeRef.current = true;
    const updated = {
      ...policy,
      exclusions: (policy.exclusions || []).filter((_, i) => i !== idx)
    };
    setPolicy(updated);
    if (onChange) onChange(updated);
  };

  const fetchFinanceReport = async () => {
    setFinanceLoading(true);
    setShowFinanceModal(true);
    try {
      const res = await axios.get(`${API}/refunds/finance-report`);
      setFinanceReport(res.data);
    } catch (err) {
      console.error('Failed to load finance report', err);
    } finally {
      setFinanceLoading(false);
    }
  };

  return (
    <Card className="p-4 bg-white border border-slate-200 space-y-4" data-testid="refund-policy-section">
      {/* Header & Overall Enable Toggle */}
      <div className="flex items-center justify-between pb-3 border-b flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-emerald-600" />
          <div>
            <h3 className="font-extrabold text-slate-900 text-sm flex items-center gap-2">
              Refund Policy Master & Statutory Safeguards
              <Badge className={policy.enabled ? "bg-emerald-100 text-emerald-800 text-[10px]" : "bg-slate-100 text-slate-600 text-[10px]"}>
                {policy.enabled ? "Active for Sales" : "Disabled"}
              </Badge>
              <Badge variant="outline" className="text-[10px] text-indigo-700 border-indigo-200">
                v{policy.version || 1}
              </Badge>
            </h3>
            <p className="text-[11px] text-slate-500">
              Configure country & product refund guarantees, claim windows, payout SLAs and finance liability rules.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={fetchFinanceReport}
            className="h-8 text-xs font-semibold gap-1.5 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
            data-testid="view-finance-liability-btn"
          >
            <BarChart3 className="h-3.5 w-3.5" />
            Finance Report
          </Button>

          {!readOnly && (
            <Button
              type="button"
              size="sm"
              onClick={handleSavePolicyDirect}
              disabled={savingPolicy}
              className="h-8 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 shadow-xs px-3"
              data-testid="save-refund-policy-header-btn"
            >
              <Save className="h-3.5 w-3.5" />
              {savingPolicy ? 'Saving...' : 'Update Refund Policy'}
            </Button>
          )}

          <label className="flex items-center gap-2 text-xs font-bold text-slate-700 cursor-pointer bg-slate-50 px-3 py-1.5 rounded-lg border">
            <input
              type="checkbox"
              disabled={readOnly}
              checked={!!policy.enabled}
              onChange={(e) => updateField('enabled', e.target.checked)}
              className="h-4 w-4 rounded text-emerald-600"
              data-testid="refund-policy-enable-checkbox"
            />
            <span>Enable for Salesperson</span>
          </label>
        </div>
      </div>

      {!policy.enabled ? (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3 text-amber-800 text-xs">
          <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
          <div>
            <p className="font-bold">Refund Policy is currently Disabled for this Product</p>
            <p className="text-[11px] text-amber-700">
              Assigned salespersons will not see any refund guarantee in their sales pitch or client quotation view. Enable the checkbox above to publish refund terms.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* 1. Policy Type Tabs */}
          <div className="space-y-2">
            <Label className="text-xs font-bold text-slate-700">Select Refund Policy Model:</Label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
              {/* Protection Policy */}
              <div
                onClick={() => !readOnly && handleTypeChange('protection')}
                className={`p-3 rounded-lg border-2 cursor-pointer transition ${
                  policy.policy_type === 'protection'
                    ? 'border-emerald-600 bg-emerald-50/60 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
                data-testid="refund-type-protection"
              >
                <div className="flex items-center justify-between pb-1">
                  <span className="font-extrabold text-xs text-slate-900 flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-emerald-600" />
                    Protection Policy
                  </span>
                  {policy.policy_type === 'protection' && (
                    <Badge className="bg-emerald-600 text-white text-[9px]">Selected</Badge>
                  )}
                </div>
                <p className="text-[11px] text-slate-600">
                  100% money-back guarantee on negative skills assessment or official visa refusal. Strongest sales conversion driver.
                </p>
              </div>

              {/* Standard Policy */}
              <div
                onClick={() => !readOnly && handleTypeChange('standard')}
                className={`p-3 rounded-lg border-2 cursor-pointer transition ${
                  policy.policy_type === 'standard'
                    ? 'border-indigo-600 bg-indigo-50/60 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
                data-testid="refund-type-standard"
              >
                <div className="flex items-center justify-between pb-1">
                  <span className="font-extrabold text-xs text-slate-900 flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-indigo-600" />
                    Standard Tiered Policy
                  </span>
                  {policy.policy_type === 'standard' && (
                    <Badge className="bg-indigo-600 text-white text-[9px]">Selected</Badge>
                  )}
                </div>
                <p className="text-[11px] text-slate-600">
                  Graduated milestone deductions. 50-70% refundable before case lodgement, reduced post document compilation.
                </p>
              </div>

              {/* No Refund Policy */}
              <div
                onClick={() => !readOnly && handleTypeChange('no_refund')}
                className={`p-3 rounded-lg border-2 cursor-pointer transition ${
                  policy.policy_type === 'no_refund'
                    ? 'border-rose-600 bg-rose-50/60 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
                data-testid="refund-type-norefund"
              >
                <div className="flex items-center justify-between pb-1">
                  <span className="font-extrabold text-xs text-slate-900 flex items-center gap-1.5">
                    <ShieldAlert className="h-4 w-4 text-rose-600" />
                    No Refund Policy
                  </span>
                  {policy.policy_type === 'no_refund' && (
                    <Badge className="bg-rose-600 text-white text-[9px]">Selected</Badge>
                  )}
                </div>
                <p className="text-[11px] text-slate-600">
                  Strictly non-refundable service fee. Used for high-risk profiles, appeals, or express verification products.
                </p>
              </div>
            </div>
          </div>

          {/* 2. Refund Components & Financial Rules Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
            {/* Left Column: Fee Breakdown & Tax Treatment */}
            <div className="space-y-3 p-3 bg-slate-50 border rounded-lg">
              <div className="flex items-center justify-between pb-1">
                <h4 className="text-xs font-extrabold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <DollarSign className="h-3.5 w-3.5 text-emerald-600" />
                  Fee Breakdown & Tax Treatment
                </h4>
                {!readOnly && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleAddCustomFeeComponent}
                    className="h-6 text-[10px] font-bold text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100 gap-1"
                    data-testid="add-fee-breakdown-option-btn"
                  >
                    <Plus className="h-3 w-3" />
                    Add Option
                  </Button>
                )}
              </div>

              {/* Service Fee Refundable % */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-bold text-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      disabled={readOnly || policy.policy_type === 'no_refund'}
                      checked={!!policy.is_service_fee_refundable}
                      onChange={(e) => updateField('is_service_fee_refundable', e.target.checked)}
                      className="h-3.5 w-3.5 rounded text-emerald-600"
                      data-testid="refund-service-fee-checkbox"
                    />
                    <span>Service Fee Refundable</span>
                  </label>
                  <div className="flex items-center gap-1">
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      disabled={readOnly || !policy.is_service_fee_refundable || policy.policy_type === 'no_refund'}
                      value={policy.refundable_service_fee_pct !== undefined && policy.refundable_service_fee_pct !== null ? policy.refundable_service_fee_pct : (policy.policy_type === 'standard' ? 50 : policy.policy_type === 'no_refund' ? 0 : 100)}
                      onChange={(e) => {
                        const raw = e.target.value;
                        const val = raw === '' ? '' : Math.min(100, Math.max(0, Number(raw)));
                        updateField('refundable_service_fee_pct', val);
                      }}
                      className="h-7 w-20 text-xs font-bold text-right"
                    />
                    <span className="text-xs font-bold text-slate-500">%</span>
                  </div>
                </div>
                <p className="text-[10px] text-slate-500">
                  Percentage of base retainer fee returned upon validated claim.
                </p>
              </div>

              {/* Government Fees Handling */}
              <div className="space-y-1 pt-1 border-t">
                <Label className="text-xs font-bold text-slate-700">Statutory Government Fees:</Label>
                <div className="flex items-center gap-4 text-xs">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="govt_fees_handling"
                      disabled={readOnly}
                      checked={policy.govt_fees_handling === 'non_refundable'}
                      onChange={() => updateField('govt_fees_handling', 'non_refundable')}
                      className="text-emerald-600"
                    />
                    <span className="text-slate-700 font-medium">Non-refundable (Standard)</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="govt_fees_handling"
                      disabled={readOnly}
                      checked={policy.govt_fees_handling === 'subsidized'}
                      onChange={() => updateField('govt_fees_handling', 'subsidized')}
                      className="text-emerald-600"
                    />
                    <span className="text-slate-700 font-medium">Subsidized / Reimbursed</span>
                  </label>
                </div>
                <p className="text-[10px] text-slate-500">
                  Embassy / Department fees paid directly to statutory authorities are non-refundable by default.
                </p>
              </div>

              {/* GST Treatment */}
              <div className="space-y-1 pt-1 border-t">
                <Label className="text-xs font-bold text-slate-700">GST (Goods & Services Tax) Treatment:</Label>
                <div className="flex items-center gap-4 text-xs">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="gst_treatment"
                      disabled={readOnly}
                      checked={policy.gst_treatment === 'credit_note'}
                      onChange={() => updateField('gst_treatment', 'credit_note')}
                      className="text-emerald-600"
                    />
                    <span className="text-slate-700 font-medium">Credit Note Issued (Full GST refunded)</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="gst_treatment"
                      disabled={readOnly}
                      checked={policy.gst_treatment === 'retained'}
                      onChange={() => updateField('gst_treatment', 'retained')}
                      className="text-emerald-600"
                    />
                    <span className="text-slate-700 font-medium">GST Retained</span>
                  </label>
                </div>
              </div>

              {/* SLA & Claim Window */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                <div>
                  <Label className="text-[11px] font-bold text-slate-700">Claim Window:</Label>
                  <div className="flex items-center gap-1 mt-0.5">
                    <Input
                      type="number"
                      min="1"
                      disabled={readOnly}
                      value={policy.claim_window_days ?? 30}
                      onChange={(e) => updateField('claim_window_days', Number(e.target.value) || 30)}
                      className="h-7 text-xs font-bold"
                    />
                    <span className="text-[11px] text-slate-500">days</span>
                  </div>
                </div>
                <div>
                  <Label className="text-[11px] font-bold text-slate-700">Payout SLA:</Label>
                  <div className="flex items-center gap-1 mt-0.5">
                    <Input
                      type="number"
                      min="1"
                      disabled={readOnly}
                      value={policy.payout_time_days ?? 14}
                      onChange={(e) => updateField('payout_time_days', Number(e.target.value) || 14)}
                      className="h-7 text-xs font-bold"
                    />
                    <span className="text-[11px] text-slate-500">days</span>
                  </div>
                </div>
              </div>

              {/* Custom Added Fee Breakdown & Deduction Options */}
              {policy.custom_fee_components && policy.custom_fee_components.length > 0 && (
                <div className="space-y-2 pt-2 border-t">
                  <div className="flex items-center justify-between">
                    <Label className="text-[11px] font-bold text-slate-700">Custom Fee & Deduction Rules:</Label>
                    <Badge variant="outline" className="text-[9px]">{policy.custom_fee_components.length} options</Badge>
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {policy.custom_fee_components.map((item, idx) => (
                      <div key={item.id || idx} className="p-2 bg-white rounded border text-xs space-y-1.5 shadow-sm">
                        <div className="flex items-center justify-between gap-1">
                          <Input
                            disabled={readOnly}
                            value={item.name}
                            onChange={(e) => handleUpdateCustomFeeComponent(idx, 'name', e.target.value)}
                            placeholder="Option Name (e.g. Admin File Charge)..."
                            className="h-6 text-xs font-bold flex-1"
                          />
                          <select
                            disabled={readOnly}
                            value={item.type || 'non_refundable'}
                            onChange={(e) => handleUpdateCustomFeeComponent(idx, 'type', e.target.value)}
                            className="h-6 text-[10px] font-semibold border rounded bg-slate-50 px-1 text-slate-700"
                          >
                            <option value="non_refundable">Non-Refundable</option>
                            <option value="deduct_flat">Deduct Flat ₹</option>
                            <option value="percentage">Refundable %</option>
                          </select>
                          {(item.type === 'deduct_flat' || item.type === 'percentage') && (
                            <div className="flex items-center gap-0.5">
                              <Input
                                type="number"
                                disabled={readOnly}
                                value={item.value ?? 0}
                                onChange={(e) => handleUpdateCustomFeeComponent(idx, 'value', Number(e.target.value) || 0)}
                                className="h-6 w-16 text-xs font-bold text-right"
                              />
                              <span className="text-[10px] text-slate-400 font-bold">{item.type === 'percentage' ? '%' : '₹'}</span>
                            </div>
                          )}
                          {!readOnly && (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => handleRemoveCustomFeeComponent(idx)}
                              className="h-6 w-6 p-0 text-rose-500 hover:bg-rose-50"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                        <Input
                          disabled={readOnly}
                          value={item.description || ''}
                          onChange={(e) => handleUpdateCustomFeeComponent(idx, 'description', e.target.value)}
                          placeholder="Description / deduction condition..."
                          className="h-5 text-[10px] text-slate-500"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Trigger Guarantees & Approvals */}
            <div className="space-y-3 p-3 bg-slate-50 border rounded-lg">
              <div className="flex items-center justify-between pb-1">
                <h4 className="text-xs font-extrabold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  Guaranteed Triggers & Approvals
                </h4>
                {!readOnly && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleAddCustomTrigger}
                    className="h-6 text-[10px] font-bold text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100 gap-1"
                    data-testid="add-trigger-option-btn"
                  >
                    <Plus className="h-3 w-3" />
                    Add Trigger
                  </Button>
                )}
              </div>

              <div className="space-y-2.5">
                <label className="flex items-start gap-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    disabled={readOnly}
                    checked={!!policy.negative_skills_assessment_guarantee}
                    onChange={(e) => updateField('negative_skills_assessment_guarantee', e.target.checked)}
                    className="h-4 w-4 rounded text-emerald-600 mt-0.5"
                    data-testid="refund-negative-skills-checkbox"
                  />
                  <div>
                    <span className="font-bold text-slate-900">Negative Skills Assessment Guarantee</span>
                    <p className="text-[10px] text-slate-500">
                      100% refund of retainer fee if skills assessment body issues negative outcome on eligible claims.
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    disabled={readOnly}
                    checked={!!policy.visa_refusal_guarantee}
                    onChange={(e) => updateField('visa_refusal_guarantee', e.target.checked)}
                    className="h-4 w-4 rounded text-emerald-600 mt-0.5"
                    data-testid="refund-visa-refusal-checkbox"
                  />
                  <div>
                    <span className="font-bold text-slate-900">Official Visa Refusal Guarantee</span>
                    <p className="text-[10px] text-slate-500">
                      Refund protection if destination immigration department rejects valid, genuine visa lodgement.
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-2 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    disabled={readOnly}
                    checked={!!policy.voluntary_withdrawal_milestones}
                    onChange={(e) => updateField('voluntary_withdrawal_milestones', e.target.checked)}
                    className="h-4 w-4 rounded text-emerald-600 mt-0.5"
                    data-testid="refund-voluntary-milestones-checkbox"
                  />
                  <div>
                    <span className="font-bold text-slate-900">Voluntary Withdrawal Milestones</span>
                    <p className="text-[10px] text-slate-500">
                      Tiered fee retention if client withdraws prior to file preparation or official lodgement.
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-2 text-xs text-slate-700 cursor-pointer pt-2 border-t">
                  <input
                    type="checkbox"
                    disabled={true}
                    checked={true}
                    className="h-4 w-4 rounded text-emerald-600 mt-0.5"
                  />
                  <div>
                    <span className="font-bold text-slate-900 flex items-center gap-1">
                      Maker-Checker Two-Step Review
                      <Badge className="bg-amber-100 text-amber-800 text-[9px]">Mandatory Rule 6</Badge>
                    </span>
                    <p className="text-[10px] text-slate-500">
                      Refund initiator can never approve payout. Enforced automatically at backend on every refund request.
                    </p>
                  </div>
                </label>

                {/* Custom Added Guaranteed Triggers */}
                {policy.custom_guaranteed_triggers && policy.custom_guaranteed_triggers.length > 0 && (
                  <div className="space-y-2 pt-2 border-t">
                    <div className="flex items-center justify-between">
                      <Label className="text-[11px] font-bold text-slate-700">Custom Guaranteed Triggers:</Label>
                      <Badge variant="outline" className="text-[9px]">{policy.custom_guaranteed_triggers.length} triggers</Badge>
                    </div>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {policy.custom_guaranteed_triggers.map((trig, idx) => (
                        <div key={trig.id || idx} className="p-2 bg-white rounded border text-xs space-y-1.5 shadow-sm">
                          <div className="flex items-center justify-between gap-1.5">
                            <label className="flex items-center gap-1.5 cursor-pointer flex-1">
                              <input
                                type="checkbox"
                                disabled={readOnly}
                                checked={trig.enabled !== false}
                                onChange={(e) => handleUpdateCustomTrigger(idx, 'enabled', e.target.checked)}
                                className="h-3.5 w-3.5 rounded text-emerald-600"
                              />
                              <Input
                                disabled={readOnly}
                                value={trig.name}
                                onChange={(e) => handleUpdateCustomTrigger(idx, 'name', e.target.value)}
                                placeholder="Trigger Name (e.g. State Nomination Rejection)..."
                                className="h-6 text-xs font-bold"
                              />
                            </label>
                            <div className="flex items-center gap-1">
                              <Input
                                type="number"
                                min="0"
                                max="100"
                                disabled={readOnly}
                                value={trig.refund_pct ?? 100}
                                onChange={(e) => handleUpdateCustomTrigger(idx, 'refund_pct', Number(e.target.value) || 0)}
                                className="h-6 w-14 text-xs font-bold text-right"
                              />
                              <span className="text-[10px] text-slate-400 font-bold">%</span>
                              {!readOnly && (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleRemoveCustomTrigger(idx)}
                                  className="h-6 w-6 p-0 text-rose-500 hover:bg-rose-50"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                          </div>
                          <Input
                            disabled={readOnly}
                            value={trig.description || ''}
                            onChange={(e) => handleUpdateCustomTrigger(idx, 'description', e.target.value)}
                            placeholder="Trigger terms & documentation required..."
                            className="h-5 text-[10px] text-slate-500"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 3. Package-wise Refund Overrides */}
          <div className="space-y-2 pt-2 border-t">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-indigo-600" />
                <Label className="text-xs font-bold text-slate-700">Package-Wise Refund Overrides:</Label>
              </div>
              {!readOnly && (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleAddPackageOverride}
                  className="h-6 text-[10px] font-bold text-indigo-700 bg-indigo-50 border-indigo-200 hover:bg-indigo-100 gap-1"
                  data-testid="add-package-override-btn"
                >
                  <Plus className="h-3 w-3" />
                  Add Package Override
                </Button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {packageOverrideEntries.map((pkg) => (
                <div key={pkg.key} className="p-2.5 bg-slate-50 rounded-lg border text-xs space-y-1.5 shadow-sm">
                  <div className="flex items-center justify-between gap-1">
                    {pkg.is_custom ? (
                      <Input
                        disabled={readOnly}
                        value={pkg.name}
                        onChange={(e) => handlePackageOverrideChange(pkg.key, 'name', e.target.value)}
                        placeholder="Package Name..."
                        className="h-6 text-xs font-bold flex-1"
                      />
                    ) : (
                      <span className="font-extrabold capitalize text-slate-900">{pkg.name || `${pkg.key} Tier`}</span>
                    )}
                    <div className="flex items-center gap-1.5">
                      <label className="flex items-center gap-1 text-[10px] font-semibold text-slate-600 cursor-pointer">
                        <input
                          type="checkbox"
                          disabled={readOnly}
                          checked={pkg.enabled !== false}
                          onChange={(e) => handlePackageOverrideChange(pkg.key, 'enabled', e.target.checked)}
                          className="h-3.5 w-3.5 rounded text-indigo-600"
                        />
                        Active
                      </label>
                      {pkg.is_custom && !readOnly && (
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => handleRemovePackageOverride(pkg.key)}
                          className="h-5 w-5 p-0 text-rose-500 hover:bg-rose-50"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[10px] text-slate-500">Refundable %</span>
                    <div className="flex items-center gap-1">
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        disabled={readOnly || pkg.enabled === false}
                        value={pkg.refundable_pct !== undefined && pkg.refundable_pct !== null ? pkg.refundable_pct : (policy.refundable_service_fee_pct ?? 100)}
                        onChange={(e) => {
                          const raw = e.target.value;
                          const val = raw === '' ? '' : Math.min(100, Math.max(0, Number(raw)));
                          handlePackageOverrideChange(pkg.key, 'refundable_pct', val);
                        }}
                        className="h-6 w-16 text-[11px] font-bold text-right"
                      />
                      <span className="text-[10px] text-slate-400">%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 4. Conditions & Exclusions Lists */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t">
            {/* Qualifying Conditions */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                  Mandatory Client Conditions:
                </Label>
                <Badge variant="outline" className="text-[9px]">{(policy.conditions || []).length} items</Badge>
              </div>

              <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                {(policy.conditions || []).map((c, idx) => (
                  <div key={idx} className="p-2 bg-slate-50 rounded border text-[11px] flex items-start gap-1.5 justify-between">
                    <span className="text-slate-700 leading-relaxed">• {c}</span>
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={() => handleRemoveCondition(idx)}
                        className="text-rose-500 hover:text-rose-700 p-0.5 shrink-0"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {!readOnly && (
                <div className="flex gap-1.5">
                  <Input
                    value={newCondition}
                    onChange={(e) => setNewCondition(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCondition())}
                    placeholder="Add qualifying condition..."
                    className="h-7 text-xs bg-white"
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleAddCondition}
                    className="h-7 text-xs font-bold text-emerald-700 hover:bg-emerald-50 shrink-0"
                  >
                    <Plus className="h-3 w-3 mr-1" />
                    Add
                  </Button>
                </div>
              )}
            </div>

            {/* Ineligibility Exclusions */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-bold text-slate-700 flex items-center gap-1">
                  <X className="h-3.5 w-3.5 text-rose-600" />
                  Policy Exclusions & Disqualifications:
                </Label>
                <Badge variant="outline" className="text-[9px]">{(policy.exclusions || []).length} items</Badge>
              </div>

              <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                {(policy.exclusions || []).map((ex, idx) => (
                  <div key={idx} className="p-2 bg-slate-50 rounded border text-[11px] flex items-start gap-1.5 justify-between">
                    <span className="text-slate-700 leading-relaxed">• {ex}</span>
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={() => handleRemoveExclusion(idx)}
                        className="text-rose-500 hover:text-rose-700 p-0.5 shrink-0"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              {!readOnly && (
                <div className="flex gap-1.5">
                  <Input
                    value={newExclusion}
                    onChange={(e) => setNewExclusion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddExclusion())}
                    placeholder="Add policy exclusion..."
                    className="h-7 text-xs bg-white"
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleAddExclusion}
                    className="h-7 text-xs font-bold text-rose-700 hover:bg-rose-50 shrink-0"
                  >
                    <Plus className="h-3 w-3 mr-1" />
                    Add
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Bottom Save / Update Bar */}
          {!readOnly && (
            <div className="pt-3 border-t flex items-center justify-between bg-emerald-50/80 p-3.5 rounded-xl border border-emerald-200 shadow-xs flex-wrap gap-2">
              <div>
                <p className="text-xs font-bold text-emerald-950 flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
                  Refund Policy & Statutory Safeguards Configured
                </p>
                <p className="text-[11px] text-emerald-800">
                  Save to apply custom fee options, triggers, and package overrides immediately across Sales Pitch Mode and client quotes.
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                onClick={handleSavePolicyDirect}
                disabled={savingPolicy}
                className="h-9 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 shadow-sm px-5 shrink-0"
                data-testid="save-refund-policy-bottom-btn"
              >
                <Save className="h-4 w-4" />
                {savingPolicy ? 'Saving Changes...' : 'Update Refund Policy'}
              </Button>
            </div>
          )}
        </>
      )}

      {/* Finance Liability & Loss Report Modal */}
      {showFinanceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <Card className="max-w-2xl w-full p-5 bg-white rounded-xl shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-2 border-b">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-emerald-600" />
                <h3 className="font-extrabold text-slate-900 text-sm">Finance Refund Liability & Loss Statement</h3>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowFinanceModal(false)}
                className="h-7 w-7 p-0 rounded-full"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {financeLoading ? (
              <div className="p-8 text-center space-y-2">
                <RefreshCw className="h-6 w-6 animate-spin text-emerald-600 mx-auto" />
                <p className="text-xs text-slate-500">Calculating real-time contingent liabilities...</p>
              </div>
            ) : financeReport ? (
              <div className="space-y-4">
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
                  <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                    <p className="text-[10px] uppercase font-bold text-emerald-700">Contingent Refund Liability</p>
                    <p className="text-base font-extrabold text-emerald-900">
                      {formatINR(financeReport.summary?.total_refund_contingent_liability)}
                    </p>
                    <p className="text-[10px] text-emerald-700 mt-0.5">
                      Across {financeReport.summary?.protection_coverage_count || 0} protected sales
                    </p>
                  </div>

                  <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
                    <p className="text-[10px] uppercase font-bold text-rose-700">Actual Refund Loss to Date</p>
                    <p className="text-base font-extrabold text-rose-900">
                      {formatINR(financeReport.summary?.total_actual_loss_to_date)}
                    </p>
                    <p className="text-[10px] text-rose-700 mt-0.5">
                      {financeReport.summary?.processed_refunds_count || 0} processed claims
                    </p>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 col-span-2 md:col-span-1">
                    <p className="text-[10px] uppercase font-bold text-slate-600">Active Retainer Base</p>
                    <p className="text-base font-extrabold text-slate-900">
                      {formatINR(financeReport.summary?.total_active_sales_value)}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      Total collections for approved cases
                    </p>
                  </div>
                </div>

                {/* Monthly Loss Schedule */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800">Monthly Processed Refund Losses:</h4>
                  {(!financeReport.monthly_losses || financeReport.monthly_losses.length === 0) ? (
                    <p className="text-xs text-slate-400 italic p-3 bg-slate-50 rounded border text-center">
                      Zero refund losses processed to date.
                    </p>
                  ) : (
                    <div className="border rounded-lg overflow-hidden text-xs">
                      <table className="w-full text-left">
                        <thead className="bg-slate-100 text-slate-700 font-bold text-[11px]">
                          <tr>
                            <th className="p-2">Month</th>
                            <th className="p-2">Claims Processed</th>
                            <th className="p-2 text-right">Refund Loss (INR)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {financeReport.monthly_losses.map((m, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="p-2 font-semibold text-slate-800">{m.month}</td>
                              <td className="p-2 text-slate-600">{m.count}</td>
                              <td className="p-2 text-right font-extrabold text-rose-700">{formatINR(m.total_refund_loss)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                <div className="text-[11px] text-slate-500 bg-slate-50 p-2.5 rounded border leading-relaxed">
                  <strong>Finance Audit Note:</strong> Contingent liability tracks maximum contractually committed refunds across open retainer engagements under the Protection Policy. Once a sale is confirmed, its refund policy schedule is locked and immune to future policy master alterations.
                </div>
              </div>
            ) : (
              <p className="text-xs text-rose-600">Failed to generate finance report.</p>
            )}

            <div className="flex justify-end pt-2">
              <Button
                size="sm"
                onClick={() => setShowFinanceModal(false)}
                className="h-8 text-xs font-bold bg-slate-900 text-white"
              >
                Close Statement
              </Button>
            </div>
          </Card>
        </div>
      )}
    </Card>
  );
}
