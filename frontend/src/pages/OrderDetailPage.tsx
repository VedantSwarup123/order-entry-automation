import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, FileText, AlertTriangle, Download, RefreshCw } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import StatusBadge from '../components/ui/StatusBadge';
import SourceBadge from '../components/ui/SourceBadge';
import Skeleton from '../components/ui/Skeleton';
import { getOrder, type OrderDetail } from '../services/api';

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
                ['Source Ref', order.source_ref || '—'],
                ['Items', String(order.line_items.length)],
                ['Total Qty', String(order.total_quantity)],
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
