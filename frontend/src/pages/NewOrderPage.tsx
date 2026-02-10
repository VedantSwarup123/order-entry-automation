import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, ChevronLeft, ChevronRight, Plus, X, Loader2, User, MapPin, ShoppingCart, ClipboardCheck } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import { createOrder } from '../services/api';

const STEPS = [
  { label: 'Customer', icon: User },
  { label: 'Shipping', icon: MapPin },
  { label: 'Items', icon: ShoppingCart },
  { label: 'Review', icon: ClipboardCheck },
];

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
];

interface LineItemForm {
  sku: string;
  description: string;
  quantity: number;
  unit_price: number;
  uom: string;
}

export default function NewOrderPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Step 1: Customer
  const [customerId, setCustomerId] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [poNumber, setPoNumber] = useState('');
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);
  const [requestedShipDate, setRequestedShipDate] = useState('');

  // Step 2: Shipping
  const [shipName, setShipName] = useState('');
  const [shipLine1, setShipLine1] = useState('');
  const [shipLine2, setShipLine2] = useState('');
  const [shipCity, setShipCity] = useState('');
  const [shipState, setShipState] = useState('');
  const [shipZip, setShipZip] = useState('');
  const [shipCountry, setShipCountry] = useState('US');

  // Step 3: Items
  const [lineItems, setLineItems] = useState<LineItemForm[]>([
    { sku: '', description: '', quantity: 1, unit_price: 0, uom: 'EA' },
  ]);

  const addItem = () => {
    setLineItems([...lineItems, { sku: '', description: '', quantity: 1, unit_price: 0, uom: 'EA' }]);
  };

  const removeItem = (index: number) => {
    if (lineItems.length > 1) {
      setLineItems(lineItems.filter((_, i) => i !== index));
    }
  };

  const updateItem = (index: number, field: keyof LineItemForm, value: string | number) => {
    const updated = [...lineItems];
    updated[index] = { ...updated[index], [field]: value };
    setLineItems(updated);
  };

  const orderTotal = lineItems.reduce((sum, item) => sum + item.quantity * item.unit_price, 0);

  const canProceed = () => {
    if (step === 0) return customerId && poNumber;
    if (step === 1) return true;
    if (step === 2) return lineItems.every(i => i.sku && i.quantity > 0 && i.unit_price >= 0);
    return true;
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const payload = {
        customer_id: customerId,
        customer_name: customerName,
        po_number: poNumber,
        order_date: orderDate || undefined,
        requested_ship_date: requestedShipDate || undefined,
        ship_to: {
          name: shipName,
          line1: shipLine1,
          line2: shipLine2 || undefined,
          city: shipCity,
          state: shipState,
          postal_code: shipZip,
          country: shipCountry,
        },
        line_items: lineItems.map(i => ({
          sku: i.sku,
          description: i.description,
          quantity: i.quantity,
          unit_price: i.unit_price,
          uom: i.uom,
        })),
      };
      const res = await createOrder(payload);
      setSuccess(true);
      setTimeout(() => navigate(`/orders/${res.data.order_id}`), 1500);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to create order';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in">
        <div className="w-16 h-16 rounded-full bg-[var(--accent-emerald)]/20 flex items-center justify-center mb-6">
          <Check size={32} className="text-[var(--accent-emerald)]" />
        </div>
        <h2 className="text-2xl font-bold mb-2">Order Created!</h2>
        <p className="text-[var(--text-secondary)]">Redirecting to order details...</p>
      </div>
    );
  }

  const inputClass = "w-full px-3 py-2.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-sm text-[var(--text-primary)] outline-none focus:border-[var(--accent-blue)] transition-colors placeholder:text-[var(--text-muted)]";
  const labelClass = "block text-sm font-medium text-[var(--text-secondary)] mb-1.5";

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      {/* Progress Bar */}
      <div className="flex items-center justify-between">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-center flex-1">
            <div className="flex items-center gap-2">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-300 ${
                  i < step ? 'bg-[var(--accent-emerald)] text-white' :
                  i === step ? 'bg-[var(--accent-blue)] text-white' :
                  'bg-[var(--bg-card)] text-[var(--text-muted)] border border-[var(--border)]'
                }`}
              >
                {i < step ? <Check size={16} /> : <s.icon size={16} />}
              </div>
              <span className={`text-sm font-medium hidden sm:block ${i <= step ? 'text-[var(--text-primary)]' : 'text-[var(--text-muted)]'}`}>
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-px mx-4 transition-colors duration-300 ${i < step ? 'bg-[var(--accent-emerald)]' : 'bg-[var(--border)]'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Form Content */}
      <GlassCard className="p-8">
        {/* Step 1: Customer */}
        {step === 0 && (
          <div className="space-y-5 animate-fade-in">
            <h3 className="text-lg font-semibold mb-6">Customer Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className={labelClass}>Customer ID *</label>
                <input value={customerId} onChange={e => setCustomerId(e.target.value)} className={inputClass} placeholder="e.g. CUST-001" />
              </div>
              <div>
                <label className={labelClass}>Customer Name</label>
                <input value={customerName} onChange={e => setCustomerName(e.target.value)} className={inputClass} placeholder="e.g. Acme Corp" />
              </div>
              <div>
                <label className={labelClass}>PO Number *</label>
                <input value={poNumber} onChange={e => setPoNumber(e.target.value)} className={inputClass} placeholder="e.g. PO-2024-001" />
              </div>
              <div>
                <label className={labelClass}>Order Date</label>
                <input type="date" value={orderDate} onChange={e => setOrderDate(e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Requested Ship Date</label>
                <input type="date" value={requestedShipDate} onChange={e => setRequestedShipDate(e.target.value)} className={inputClass} />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Shipping */}
        {step === 1 && (
          <div className="space-y-5 animate-fade-in">
            <h3 className="text-lg font-semibold mb-6">Shipping Address</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="md:col-span-2">
                <label className={labelClass}>Name</label>
                <input value={shipName} onChange={e => setShipName(e.target.value)} className={inputClass} placeholder="Recipient name" />
              </div>
              <div className="md:col-span-2">
                <label className={labelClass}>Address Line 1</label>
                <input value={shipLine1} onChange={e => setShipLine1(e.target.value)} className={inputClass} placeholder="Street address" />
              </div>
              <div className="md:col-span-2">
                <label className={labelClass}>Address Line 2</label>
                <input value={shipLine2} onChange={e => setShipLine2(e.target.value)} className={inputClass} placeholder="Apt, suite, unit" />
              </div>
              <div>
                <label className={labelClass}>City</label>
                <input value={shipCity} onChange={e => setShipCity(e.target.value)} className={inputClass} placeholder="City" />
              </div>
              <div>
                <label className={labelClass}>State</label>
                <select value={shipState} onChange={e => setShipState(e.target.value)} className={inputClass}>
                  <option value="">Select state</option>
                  {US_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Zip Code</label>
                <input value={shipZip} onChange={e => setShipZip(e.target.value)} className={inputClass} placeholder="12345" />
              </div>
              <div>
                <label className={labelClass}>Country</label>
                <input value={shipCountry} onChange={e => setShipCountry(e.target.value)} className={inputClass} />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Line Items */}
        {step === 2 && (
          <div className="space-y-5 animate-fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">Line Items</h3>
              <button
                onClick={addItem}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] text-sm font-medium hover:bg-[var(--accent-blue)]/20 transition-colors"
              >
                <Plus size={14} />
                Add Item
              </button>
            </div>
            <div className="space-y-4">
              {lineItems.map((item, i) => (
                <div key={i} className="flex items-start gap-3 p-4 rounded-lg bg-[var(--bg-secondary)]/50 border border-[var(--border)] animate-fade-in">
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3 flex-1">
                    <div>
                      <label className={labelClass}>SKU *</label>
                      <input value={item.sku} onChange={e => updateItem(i, 'sku', e.target.value)} className={inputClass} placeholder="SKU-001" />
                    </div>
                    <div>
                      <label className={labelClass}>Description</label>
                      <input value={item.description} onChange={e => updateItem(i, 'description', e.target.value)} className={inputClass} placeholder="Item name" />
                    </div>
                    <div>
                      <label className={labelClass}>Qty *</label>
                      <input type="number" min={1} value={item.quantity} onChange={e => updateItem(i, 'quantity', parseInt(e.target.value) || 0)} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>Unit Price *</label>
                      <input type="number" min={0} step={0.01} value={item.unit_price} onChange={e => updateItem(i, 'unit_price', parseFloat(e.target.value) || 0)} className={inputClass} />
                    </div>
                    <div>
                      <label className={labelClass}>UOM</label>
                      <select value={item.uom} onChange={e => updateItem(i, 'uom', e.target.value)} className={inputClass}>
                        <option value="EA">EA</option>
                        <option value="CS">CS</option>
                        <option value="BX">BX</option>
                        <option value="PK">PK</option>
                        <option value="LB">LB</option>
                        <option value="KG">KG</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={() => removeItem(i)}
                    className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--accent-rose)] hover:bg-[var(--accent-rose)]/10 transition-colors mt-6"
                    disabled={lineItems.length <= 1}
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex justify-end pt-2">
              <div className="text-right">
                <p className="text-sm text-[var(--text-muted)]">Running Total</p>
                <p className="text-2xl font-bold">${orderTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 3 && (
          <div className="space-y-6 animate-fade-in">
            <h3 className="text-lg font-semibold mb-6">Review Order</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-medium text-[var(--text-muted)] mb-3">Customer</h4>
                <div className="space-y-1 text-sm">
                  <p><span className="text-[var(--text-muted)]">ID:</span> {customerId}</p>
                  <p><span className="text-[var(--text-muted)]">Name:</span> {customerName || '—'}</p>
                  <p><span className="text-[var(--text-muted)]">PO:</span> {poNumber}</p>
                  <p><span className="text-[var(--text-muted)]">Date:</span> {orderDate}</p>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-[var(--text-muted)] mb-3">Ship To</h4>
                <div className="space-y-1 text-sm text-[var(--text-secondary)]">
                  {shipName && <p>{shipName}</p>}
                  {shipLine1 && <p>{shipLine1}</p>}
                  {shipLine2 && <p>{shipLine2}</p>}
                  <p>{[shipCity, shipState, shipZip].filter(Boolean).join(', ')}</p>
                  <p>{shipCountry}</p>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-[var(--text-muted)] mb-3">Line Items ({lineItems.length})</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                      <th className="pb-2 pr-4 font-medium">SKU</th>
                      <th className="pb-2 pr-4 font-medium">Description</th>
                      <th className="pb-2 pr-4 font-medium text-right">Qty</th>
                      <th className="pb-2 pr-4 font-medium text-right">Price</th>
                      <th className="pb-2 font-medium text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lineItems.map((item, i) => (
                      <tr key={i} className="border-b border-[var(--border)] last:border-0">
                        <td className="py-2 pr-4 font-mono text-xs text-[var(--accent-blue)]">{item.sku}</td>
                        <td className="py-2 pr-4 text-[var(--text-secondary)]">{item.description || '—'}</td>
                        <td className="py-2 pr-4 text-right">{item.quantity}</td>
                        <td className="py-2 pr-4 text-right">${item.unit_price.toFixed(2)}</td>
                        <td className="py-2 text-right font-medium">${(item.quantity * item.unit_price).toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex justify-end mt-4 pt-4 border-t border-[var(--border)]">
                <div className="text-right">
                  <p className="text-sm text-[var(--text-muted)]">Order Total</p>
                  <p className="text-3xl font-bold">${orderTotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
                </div>
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-lg bg-[var(--accent-rose)]/10 border border-[var(--accent-rose)]/30 text-sm text-[var(--accent-rose)]">
                {error}
              </div>
            )}
          </div>
        )}
      </GlassCard>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setStep(s => s - 1)}
          disabled={step === 0}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-[var(--border)] text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ChevronLeft size={16} />
          Back
        </button>

        {step < 3 ? (
          <button
            onClick={() => setStep(s => s + 1)}
            disabled={!canProceed()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent-blue)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight size={16} />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-[var(--accent-emerald)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-60"
          >
            {submitting ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
            {submitting ? 'Submitting...' : 'Submit Order'}
          </button>
        )}
      </div>
    </div>
  );
}
