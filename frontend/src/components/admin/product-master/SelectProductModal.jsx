import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Package,
  Layers,
  Globe,
  Plus,
  Check,
  CheckCircle2,
  Trash2,
  Search,
  IndianRupee,
  AlertCircle,
  X,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatINR = (n) => {
  if (n == null) return '₹0';
  const num = Math.round(Number(n) || 0);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)}Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)}L`;
  return `₹${num.toLocaleString('en-IN')}`;
};

export default function SelectProductModal({
  isOpen,
  onClose,
  mode = 'packages', // 'packages' | 'commissions'
  currentProductId,
  allProducts = [],
  onAddPackages,
  onAddCommissions,
}) {
  const [products, setProducts] = useState(allProducts);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [selectedPackages, setSelectedPackages] = useState({});
  const [selectedAllocations, setSelectedAllocations] = useState({});
  const [searchFilter, setSearchFilter] = useState('');

  // Sync products from props or API
  useEffect(() => {
    if (allProducts && allProducts.length > 0) {
      setProducts(allProducts);
    } else if (isOpen) {
      loadProducts();
    }
  }, [allProducts, isOpen]);

  // Reset state on open
  useEffect(() => {
    if (isOpen) {
      setSelectedProductId('');
      setSelectedPackages({});
      setSelectedAllocations({});
      setSearchFilter('');
    }
  }, [isOpen]);

  const loadProducts = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API}/product-master?include_archived=false`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const items = res.data?.items || res.data || [];
      setProducts(items);
    } catch (err) {
      console.error('Failed to load products:', err);
    }
  };

  // Filter out current product
  const availableProducts = useMemo(() => {
    return products.filter((p) => p.id !== currentProductId && p.status !== 'archived');
  }, [products, currentProductId]);

  // Selected product object
  const selectedProduct = useMemo(() => {
    return availableProducts.find((p) => p.id === selectedProductId) || null;
  }, [availableProducts, selectedProductId]);

  // Available packages for the selected product
  const productPackages = useMemo(() => {
    if (!selectedProduct) return [];
    const baseFee = parseFloat(selectedProduct.service_price || selectedProduct.base_fee || 0);
    if (selectedProduct.packages && selectedProduct.packages.length > 0) {
      return selectedProduct.packages.map((pkg, idx) => ({
        id: pkg.id || `${selectedProduct.id}-pkg-${idx}`,
        package_type: pkg.package_type || 'standard',
        name: pkg.name || `${selectedProduct.name} ${pkg.package_type || 'Package'}`,
        price: parseFloat(pkg.price) || (pkg.package_type === 'smart' ? Math.round(baseFee * 1.25) : pkg.package_type === 'premium' ? Math.round(baseFee * 1.5) : baseFee),
        description: pkg.description || `Includes ${selectedProduct.name} application & processing scope.`,
        is_active: pkg.is_active !== false,
      }));
    }
    // Fallback default tiers for the product based on its fee
    return [
      {
        id: `${selectedProduct.id}-pkg-std`,
        package_type: 'standard',
        name: `${selectedProduct.name} (Standard)`,
        price: baseFee || 150000,
        description: `Core visa application guidance & filing for ${selectedProduct.name}.`,
        is_active: true,
      },
      {
        id: `${selectedProduct.id}-pkg-smart`,
        package_type: 'smart',
        name: `${selectedProduct.name} (Smart)`,
        price: Math.round((baseFee || 150000) * 1.25),
        description: `Full documentation prep, priority reviews & exam support for ${selectedProduct.name}.`,
        is_active: true,
      },
      {
        id: `${selectedProduct.id}-pkg-prem`,
        package_type: 'premium',
        name: `${selectedProduct.name} (Premium)`,
        price: Math.round((baseFee || 150000) * 1.5),
        description: `Dedicated senior case manager concierge for ${selectedProduct.name}.`,
        is_active: true,
      },
    ];
  }, [selectedProduct]);

  // Available commission splits for the selected product
  const productAllocations = useMemo(() => {
    if (!selectedProduct) return [];
    const baseFee = parseFloat(selectedProduct.service_price || selectedProduct.base_fee || 0);
    if (selectedProduct.cost_allocations && selectedProduct.cost_allocations.length > 0) {
      return selectedProduct.cost_allocations.map((a, idx) => ({
        id: `${selectedProduct.id}-alloc-${idx}`,
        label: a.label || `Commission Split ${idx + 1}`,
        vendor_category: a.vendor_category || 'internal_partner',
        payment_type: a.payment_type || 'percentage',
        rate: a.rate !== undefined && a.rate !== null ? a.rate : a.amount || 5,
        amount: a.amount !== undefined && a.amount !== null ? a.amount : 5000,
        is_optional: !!a.is_optional,
      }));
    }
    // Standard quick splits for the product
    return [
      {
        id: `${selectedProduct.id}-alloc-sales`,
        label: `Salesperson Commission (${selectedProduct.name})`,
        vendor_category: 'internal_partner',
        payment_type: 'percentage',
        rate: 5,
        amount: 0,
        is_optional: false,
      },
      {
        id: `${selectedProduct.id}-alloc-partner`,
        label: `External Partner Split (${selectedProduct.name})`,
        vendor_category: 'external_partner',
        payment_type: 'percentage',
        rate: 10,
        amount: 0,
        is_optional: false,
      },
      {
        id: `${selectedProduct.id}-alloc-cm`,
        label: `Case Manager Delivery Fee (${selectedProduct.name})`,
        vendor_category: 'case_manager',
        payment_type: 'flat',
        rate: 0,
        amount: 5000,
        is_optional: false,
      },
      {
        id: `${selectedProduct.id}-alloc-product-cost`,
        label: `Base Service Cost (${selectedProduct.name})`,
        vendor_category: 'external_partner',
        payment_type: 'flat',
        rate: 0,
        amount: baseFee,
        is_optional: false,
      },
    ];
  }, [selectedProduct]);

  // When selected product changes, select all its packages/splits by default for convenience
  const handleSelectProduct = (prodId) => {
    setSelectedProductId(prodId);
    const prod = availableProducts.find((p) => p.id === prodId);
    if (!prod) {
      setSelectedPackages({});
      setSelectedAllocations({});
      return;
    }
    // Default select all available packages
    const pkgMap = {};
    const baseFee = parseFloat(prod.service_price || prod.base_fee || 0);
    const pkgs = prod.packages && prod.packages.length > 0 ? prod.packages : [
      { package_type: 'standard' },
      { package_type: 'smart' },
      { package_type: 'premium' },
    ];
    pkgs.forEach((_, idx) => {
      pkgMap[idx] = true;
    });
    setSelectedPackages(pkgMap);

    // Default select all splits
    const allocMap = {};
    const allocs = prod.cost_allocations && prod.cost_allocations.length > 0 ? prod.cost_allocations : [0, 1, 2];
    allocs.forEach((_, idx) => {
      allocMap[idx] = true;
    });
    setSelectedAllocations(allocMap);
  };

  // Toggle package checkbox
  const togglePackage = (idx) => {
    setSelectedPackages((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  // Toggle allocation checkbox
  const toggleAllocation = (idx) => {
    setSelectedAllocations((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  // Count selected items
  const selectedPackagesCount = useMemo(() => {
    return Object.values(selectedPackages).filter(Boolean).length;
  }, [selectedPackages]);

  const selectedAllocationsCount = useMemo(() => {
    return Object.values(selectedAllocations).filter(Boolean).length;
  }, [selectedAllocations]);

  // Submission handler
  const handleConfirm = () => {
    if (!selectedProduct) {
      toast.error('Please select a product first.');
      return;
    }

    if (mode === 'packages') {
      const packagesToAdd = productPackages.filter((_, idx) => !!selectedPackages[idx]);
      if (packagesToAdd.length === 0) {
        toast.error('Please select at least one package to add.');
        return;
      }
      onAddPackages(packagesToAdd, selectedProduct);
      toast.success(`Added ${packagesToAdd.length} package(s) from ${selectedProduct.name}`);
      onClose();
    } else {
      const allocsToAdd = productAllocations.filter((_, idx) => !!selectedAllocations[idx]);
      if (allocsToAdd.length === 0) {
        toast.error('Please select at least one commission split to add.');
        return;
      }
      onAddCommissions(allocsToAdd, selectedProduct);
      toast.success(`Added ${allocsToAdd.length} commission split(s) from ${selectedProduct.name}`);
      onClose();
    }
  };

  const isPackagesMode = mode === 'packages';

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col p-0 overflow-hidden" data-testid="select-product-modal">
        {/* Header */}
        <DialogHeader className="p-4 px-6 border-b bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-lg ${isPackagesMode ? 'bg-purple-100 text-purple-700' : 'bg-emerald-100 text-emerald-700'}`}>
              {isPackagesMode ? <Package className="h-5 w-5" /> : <Layers className="h-5 w-5" />}
            </div>
            <div>
              <DialogTitle className="text-base font-extrabold text-slate-900">
                {isPackagesMode ? 'Add Product Packages' : 'Add Product Commissions & Splits'}
              </DialogTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                {isPackagesMode
                  ? 'Select an existing product to view its available packages, then select and add only the required packages.'
                  : 'Select an existing product to view its available commission splits and add only the required allocations.'}
              </p>
            </div>
          </div>
        </DialogHeader>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* 1. PRODUCT SELECTOR (Clean single dropdown — NOT a screen of 27 visa subclasses) */}
          <div className="space-y-1.5">
            <Label className="text-xs font-bold text-slate-700">Select Existing Product</Label>
            <select
              value={selectedProductId}
              onChange={(e) => handleSelectProduct(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-xs font-medium text-slate-900 shadow-sm focus:border-purple-600 focus:outline-none"
              data-testid="product-picker-dropdown"
            >
              <option value="">— Choose a Product to View Available Packages —</option>
              {availableProducts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.country ? `[${p.country}] ` : ''}{p.name} {p.service_price || p.base_fee ? `(₹${(p.service_price || p.base_fee).toLocaleString('en-IN')})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* 2. AVAILABLE PACKAGES / COMMISSIONS FOR THE SELECTED PRODUCT ONLY */}
          {selectedProduct ? (
            <div className="space-y-3 animate-in fade-in duration-200">
              {/* Product Info Bar */}
              <div className="p-3 bg-slate-100/80 rounded-lg flex items-center justify-between border border-slate-200">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-xs text-slate-900">{selectedProduct.name}</span>
                    {selectedProduct.country && (
                      <Badge variant="outline" className="text-[10px] bg-white gap-1 text-slate-600">
                        <Globe className="h-2.5 w-2.5" />
                        {selectedProduct.country}
                      </Badge>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Base Retainer: <strong>{formatINR(selectedProduct.service_price || selectedProduct.base_fee)}</strong>
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-[11px] h-7 text-slate-600 hover:bg-slate-200"
                    onClick={() => {
                      if (isPackagesMode) {
                        const allOn = {};
                        productPackages.forEach((_, i) => { allOn[i] = true; });
                        setSelectedPackages(allOn);
                      } else {
                        const allOn = {};
                        productAllocations.forEach((_, i) => { allOn[i] = true; });
                        setSelectedAllocations(allOn);
                      }
                    }}
                  >
                    Select All
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-[11px] h-7 text-slate-600 hover:bg-slate-200"
                    onClick={() => {
                      if (isPackagesMode) setSelectedPackages({});
                      else setSelectedAllocations({});
                    }}
                  >
                    Deselect All
                  </Button>
                </div>
              </div>

              {/* Mode: PACKAGES */}
              {isPackagesMode ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 px-1">
                    <span>Available Packages for {selectedProduct.name}</span>
                    <span className="text-[11px] text-purple-700 font-semibold">
                      {selectedPackagesCount} of {productPackages.length} selected
                    </span>
                  </div>

                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                    {productPackages.map((pkg, idx) => {
                      const isChecked = !!selectedPackages[idx];
                      return (
                        <div
                          key={pkg.id || idx}
                          onClick={() => togglePackage(idx)}
                          className={`p-3 rounded-lg border cursor-pointer transition flex items-start gap-3 ${
                            isChecked
                              ? 'border-purple-500 bg-purple-50/50 shadow-sm'
                              : 'border-slate-200 bg-white hover:border-slate-300'
                          }`}
                          data-testid={`package-checkbox-item-${idx}`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}} // handled by parent onClick
                            className="mt-1 h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500 cursor-pointer"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-xs text-slate-900">{pkg.name}</span>
                                <Badge
                                  className={
                                    pkg.package_type === 'premium'
                                      ? 'bg-amber-100 text-amber-800 text-[9px]'
                                      : pkg.package_type === 'smart'
                                      ? 'bg-blue-100 text-blue-800 text-[9px]'
                                      : 'bg-slate-100 text-slate-700 text-[9px]'
                                  }
                                >
                                  {pkg.package_type}
                                </Badge>
                              </div>
                              <span className="font-extrabold text-xs text-purple-700 shrink-0">
                                {formatINR(pkg.price)}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                              {pkg.description || 'Core package inclusions.'}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                /* Mode: COMMISSIONS */
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-700 px-1">
                    <span>Available Commission Splits for {selectedProduct.name}</span>
                    <span className="text-[11px] text-emerald-700 font-semibold">
                      {selectedAllocationsCount} of {productAllocations.length} selected
                    </span>
                  </div>

                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                    {productAllocations.map((alloc, idx) => {
                      const isChecked = !!selectedAllocations[idx];
                      return (
                        <div
                          key={alloc.id || idx}
                          onClick={() => toggleAllocation(idx)}
                          className={`p-3 rounded-lg border cursor-pointer transition flex items-start gap-3 ${
                            isChecked
                              ? 'border-emerald-500 bg-emerald-50/50 shadow-sm'
                              : 'border-slate-200 bg-white hover:border-slate-300'
                          }`}
                          data-testid={`allocation-checkbox-item-${idx}`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}} // handled by parent onClick
                            className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <div>
                                <span className="font-bold text-xs text-slate-900">{alloc.label}</span>
                                <span className="text-[10px] text-slate-400 ml-2">({alloc.vendor_category})</span>
                              </div>
                              <span className="font-extrabold text-xs text-emerald-700 shrink-0">
                                {alloc.payment_type === 'percentage'
                                  ? `${alloc.rate}% of Price`
                                  : formatINR(alloc.amount)}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 space-y-1.5">
              <Package className="h-8 w-8 text-slate-300 mx-auto" />
              <p className="text-xs font-bold text-slate-600">No Product Selected</p>
              <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                Select a product from the dropdown above to display only its available packages.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="p-3 px-6 border-t bg-slate-50 flex items-center justify-between">
          <Button variant="outline" size="sm" onClick={onClose} className="text-xs h-8">
            Cancel
          </Button>

          <Button
            onClick={handleConfirm}
            disabled={!selectedProduct || (isPackagesMode ? selectedPackagesCount === 0 : selectedAllocationsCount === 0)}
            className={`text-xs h-8 font-semibold gap-1.5 text-white ${
              isPackagesMode ? 'bg-purple-700 hover:bg-purple-800' : 'bg-emerald-700 hover:bg-emerald-800'
            }`}
            data-testid="confirm-add-btn"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            {isPackagesMode
              ? `Add Selected Packages (${selectedPackagesCount})`
              : `Add Selected Splits (${selectedAllocationsCount})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
