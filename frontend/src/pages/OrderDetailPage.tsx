import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  MapPin,
  FileText,
  AlertTriangle,
  Download,
  RefreshCw,
  Brain,
  Shield,
  Cpu,
} from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import StatusBadge from '../components/ui/StatusBadge';
import SourceBadge from '../components/ui/SourceBadge';
import Skeleton from '../components/ui/Skeleton';
import { getOrder, type OrderDetail } from '../services/api';

const confidenceColor = (c: number) => {
  if (c >= 0.8) return 'text-[var(--accent-emerald)]';
  if (c >= 0.6) return 'text-[var(--accent-amber)]';
  return 'text-[var(--accent-rose)]';
};

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getOrder(id)
      .then((res) => setOrder(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in">
        <FileText size={48} className="text-[var(--text-muted)] mb-4 opacity-40" />
        <p className="text-lg font-medium mb-1">Order not found</p>
        <p className="text-sm text-[var(--text-muted)] mb-6">The order you're looking for doesn't exist.</p>
        <button onClick={() => navigate('/orders')} className="text-[var(--accent-blue)] hover:underline text-sm">
          Back to Orders
        </button>
      </div>
    );
  }

  const sapData = order.sap_data as Record<string, unknown> | null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/orders')}
            className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-semibold font-mono">{order.id.slice(0, 12)}...</h2>
              <StatusBadge status={order.status} />
              <SourceBadge source={order.source} />
            </div>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              {order.customer_name} &middot; PO: {order.po_number}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {order.status === 'error' && (
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--accent-amber)] text-[var(--accent-amber)] text-sm font-medium hover:bg-[var(--accent-amber)]/10 transition-colors">
              <RefreshCw size={14} />
              Retry
            </button>
          )}
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--text-secondary)] text-sm font-medium hover:bg-[var(--bg-card-hover)] transition-colors">
            <Download size={14} />
            Export
          </button>
        </div>
      </div>

      {/* Confidence / Review Banner */}
      {order.review && (
        <div className={`flex items-center gap-4 px-5 py-3 rounded-xl border ${
          order.review.confidence >= 0.8
            ? 'bg-[var(--accent-emerald)]/5 border-[var(--accent-emerald)]/20'
            : order.review.confidence >= 0.6
            ? 'bg-[var(--accent-amber)]/5 border-[var(--accent-amber)]/20'
            : 'bg-[var(--accent-rose)]/5 border-[var(--accent-rose)]/20'
        }`}>
          <Brain size={18} className={confidenceColor(order.review.confidence)} />
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-[var(--text-primary)]">
                AI Extraction Confidence:
                <span className={`ml-2 font-bold ${confidenceColor(order.review.confidence)}`}>
                  {Math.round(order.review.confidence * 100)}%
                </span>
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-muted)]">
                {order.review.extraction_method}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${
                order.review.status === 'approved'
                  ? 'bg-[var(--accent-emerald)]/10 text-[var(--accent-emerald)] border-[var(--accent-emerald)]/20'
                  : order.review.status === 'pending'
                  ? 'bg-[var(--accent-amber)]/10 text-[var(--accent-amber)] border-[var(--accent-amber)]/20'
                  : 'bg-[var(--accent-rose)]/10 text-[var(--accent-rose)] border-[var(--accent-rose)]/20'
              }`}>
                Review: {order.review.status}
              </span>
            </div>
            {order.review.anomalies.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {order.review.anomalies.map((a, i) => (
                  <span key={i} className="text-xs px-2 py-1 rounded bg-[var(--accent-rose)]/10 text-[var(--accent-rose)]">
                    {a}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => navigate('/review')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/20 transition-colors"
          >
            <Shield size={12} />
            Review Queue
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Line Items */}
          <GlassCard className="overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--border)]">
              <h3 className="text-sm font-semibold">Line Items</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                    <th className="px-6 py-3 font-medium">SKU</th>
                    <th className="px-6 py-3 font-medium">Description</th>
                    <th className="px-6 py-3 font-medium text-right">Qty</th>
                    <th className="px-6 py-3 font-medium text-right">Unit Price</th>
                    <th className="px-6 py-3 font-medium">UOM</th>
                    <th className="px-6 py-3 font-medium text-right">Line Total</th>
                  </tr>
                </thead>
                <tbody>
                  {order.line_items.map((item) => (
                    <tr key={item.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-6 py-3 font-mono text-xs text-[var(--accent-blue)]">{item.sku}</td>
                      <td className="px-6 py-3 text-[var(--text-secondary)]">{item.description}</td>
                      <td className="px-6 py-3 text-right">{item.quantity}</td>
                      <td className="px-6 py-3 text-right">${Number(item.unit_price).toFixed(2)}</td>
                      <td className="px-6 py-3 text-[var(--text-muted)]">{item.uom}</td>
                      <td className="px-6 py-3 text-right font-medium">${Number(item.line_total).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 border-t border-[var(--border)] flex justify-end">
              <div className="text-right">
                <p className="text-sm text-[var(--text-muted)]">Order Total</p>
                <p className="text-2xl font-bold">${Number(order.total_amount).toLocaleString()}</p>
              </div>
            </div>
          </GlassCard>

          {/* SAP Preview */}
          {sapData && (
            <GlassCard className="overflow-hidden">
              <div className="px-6 py-4 border-b border-[var(--border)] flex items-center gap-2">
                <Cpu size={16} className="text-[var(--accent-blue)]" />
                <h3 className="text-sm font-semibold">SAP VA-01 Preview</h3>
                {order.sap_order_type && (
                  <span className={`ml-2 px-2 py-0.5 text-xs rounded-full border ${
                    order.sap_order_type === 'ZL01'
                      ? 'bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] border-[var(--accent-blue)]/20'
                      : 'bg-[var(--accent-emerald)]/10 text-[var(--accent-emerald)] border-[var(--accent-emerald)]/20'
                  }`}>
                    {order.sap_order_type} — {order.sap_order_type === 'ZL01' ? 'Stock Order' : 'Drop Ship'}
                  </span>
                )}
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                  {[
                    ['Order Type', `${sapData.order_type} (${sapData.order_type_desc})`],
                    ['Sales Org', String(sapData.sales_org || '—')],
                    ['Plant', String(sapData.plant || '—')],
                    ['Delivery Priority', String(sapData.delivery_priority || '—')],
                    ['Incoterms', String(sapData.incoterms || '—')],
                    ['Customer PO', order.po_number],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <p className="text-xs text-[var(--text-muted)] mb-0.5">{label}</p>
                      <p className="font-medium text-[var(--text-primary)]">{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </GlassCard>
          )}

          {/* Errors */}
          {order.errors && order.errors.length > 0 && (
            <GlassCard className="p-6 border-[var(--accent-rose)]/30">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={16} className="text-[var(--accent-rose)]" />
                <h3 className="text-sm font-semibold text-[var(--accent-rose)]">Errors</h3>
              </div>
              <p className="text-sm text-[var(--text-secondary)]">{order.errors}</p>
            </GlassCard>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Ship To */}
          <GlassCard className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <MapPin size={16} className="text-[var(--accent-emerald)]" />
              <h3 className="text-sm font-semibold">Ship To</h3>
            </div>
            <div className="text-sm text-[var(--text-secondary)] space-y-1">
              {order.ship_to_name && <p className="font-medium text-[var(--text-primary)]">{order.ship_to_name}</p>}
              {order.ship_to_line1 && <p>{order.ship_to_line1}</p>}
              {(order.ship_to_city || order.ship_to_state) && (
                <p>{[order.ship_to_city, order.ship_to_state, order.ship_to_postal_code].filter(Boolean).join(', ')}</p>
              )}
              {order.ship_to_country && <p>{order.ship_to_country}</p>}
            </div>
          </GlassCard>

          {/* Metadata */}
          <GlassCard className="p-6">
            <h3 className="text-sm font-semibold mb-4">Order Details</h3>
            <div className="space-y-3 text-sm">
              {[
                ['Order Date', order.order_date],
                ['Source', order.source],
                ['Source Ref', order.source_ref || '\u2014'],
                ['Items', String(order.line_items.length)],
                ['Total Qty', String(order.total_quantity)],
                ['SAP Type', order.sap_order_type || '\u2014'],
                ['Created', new Date(order.created_at).toLocaleString()],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-[var(--text-muted)]">{label}</span>
                  <span className="text-[var(--text-secondary)]">{value}</span>
                </div>
              ))}
            </div>
            {order.notes && (
              <div className="mt-4 pt-4 border-t border-[var(--border)]">
                <p className="text-xs text-[var(--text-muted)] mb-1">Notes</p>
                <p className="text-sm text-[var(--text-secondary)]">{order.notes}</p>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
