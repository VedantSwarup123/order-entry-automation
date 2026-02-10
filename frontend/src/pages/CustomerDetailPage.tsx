import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Users, Package, DollarSign } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import StatusBadge from '../components/ui/StatusBadge';
import SourceBadge from '../components/ui/SourceBadge';
import Skeleton from '../components/ui/Skeleton';
import { getCustomer, type CustomerDetail } from '../services/api';

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getCustomer(id)
      .then((res) => setCustomer(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-3 gap-6">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in">
        <Users size={48} className="text-[var(--text-muted)] mb-4 opacity-40" />
        <p className="text-lg font-medium mb-1">Customer not found</p>
        <button onClick={() => navigate('/customers')} className="text-[var(--accent-blue)] hover:underline text-sm mt-4">
          Back to Customers
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/customers')}
          className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h2 className="text-xl font-semibold">{customer.customer_name || customer.customer_id}</h2>
          <p className="text-sm text-[var(--text-muted)] font-mono">{customer.customer_id}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <GlassCard className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[var(--accent-blue)]/10 flex items-center justify-center">
              <Package size={18} className="text-[var(--accent-blue)]" />
            </div>
            <div>
              <p className="text-2xl font-bold">{customer.order_count}</p>
              <p className="text-xs text-[var(--text-muted)]">Total Orders</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[var(--accent-emerald)]/10 flex items-center justify-center">
              <DollarSign size={18} className="text-[var(--accent-emerald)]" />
            </div>
            <div>
              <p className="text-2xl font-bold">${Number(customer.total_revenue).toLocaleString()}</p>
              <p className="text-xs text-[var(--text-muted)]">Total Revenue</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard className="p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[var(--accent-amber)]/10 flex items-center justify-center">
              <DollarSign size={18} className="text-[var(--accent-amber)]" />
            </div>
            <div>
              <p className="text-2xl font-bold">${Number(customer.avg_order_value).toLocaleString()}</p>
              <p className="text-xs text-[var(--text-muted)]">Avg Order Value</p>
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Orders Table */}
      <GlassCard className="overflow-hidden">
        <div className="px-6 py-4 border-b border-[var(--border)]">
          <h3 className="text-sm font-semibold">Order History</h3>
        </div>
        {customer.orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-[var(--text-muted)]">
            <Package size={40} className="mb-3 opacity-40" />
            <p className="text-sm">No orders yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                  <th className="px-6 py-3 font-medium">Order ID</th>
                  <th className="px-6 py-3 font-medium">PO Number</th>
                  <th className="px-6 py-3 font-medium">Source</th>
                  <th className="px-6 py-3 font-medium text-right">Amount</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {customer.orders.map((order) => (
                  <tr
                    key={order.id}
                    onClick={() => navigate(`/orders/${order.id}`)}
                    className="border-b border-[var(--border)] last:border-0 cursor-pointer hover:bg-[var(--bg-card-hover)] transition-colors"
                  >
                    <td className="px-6 py-3 font-mono text-xs text-[var(--accent-blue)]">{order.id.slice(0, 8)}...</td>
                    <td className="px-6 py-3 text-[var(--text-secondary)]">{order.po_number}</td>
                    <td className="px-6 py-3"><SourceBadge source={order.source} /></td>
                    <td className="px-6 py-3 text-right font-medium">${Number(order.total_amount).toLocaleString()}</td>
                    <td className="px-6 py-3"><StatusBadge status={order.status} /></td>
                    <td className="px-6 py-3 text-[var(--text-muted)] text-xs">{new Date(order.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
