import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Users, DollarSign, Package, Calendar } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import { SkeletonTable } from '../components/ui/Skeleton';
import { getCustomers, type CustomerSummary } from '../services/api';

export default function CustomersPage() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCustomers()
      .then((res) => setCustomers(res.data.customers))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = customers.filter(
    (c) =>
      c.customer_name.toLowerCase().includes(search.toLowerCase()) ||
      c.customer_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Search */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-secondary)] max-w-md">
        <Search size={16} />
        <input
          type="text"
          placeholder="Search customers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-transparent outline-none text-sm w-full text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
        />
      </div>

      {/* Customer Cards Grid */}
      {loading ? (
        <div className="p-6"><SkeletonTable rows={6} /></div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-[var(--text-muted)]">
          <Users size={48} className="mb-4 opacity-40" />
          <p className="text-lg font-medium mb-1">No customers found</p>
          <p className="text-sm">Customers will appear here once orders are processed.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((customer) => (
            <GlassCard
              key={customer.customer_id}
              className="p-5"
              hover
              onClick={() => navigate(`/customers/${customer.customer_id}`)}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold">{customer.customer_name || customer.customer_id}</h3>
                  <p className="text-xs text-[var(--text-muted)] font-mono mt-0.5">{customer.customer_id}</p>
                </div>
                <div className="w-9 h-9 rounded-lg bg-[var(--accent-blue)]/10 flex items-center justify-center">
                  <Users size={16} className="text-[var(--accent-blue)]" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <div className="flex items-center justify-center gap-1 text-[var(--text-muted)] mb-1">
                    <Package size={12} />
                  </div>
                  <p className="text-sm font-semibold">{customer.order_count}</p>
                  <p className="text-xs text-[var(--text-muted)]">Orders</p>
                </div>
                <div>
                  <div className="flex items-center justify-center gap-1 text-[var(--text-muted)] mb-1">
                    <DollarSign size={12} />
                  </div>
                  <p className="text-sm font-semibold">${Number(customer.total_revenue).toLocaleString()}</p>
                  <p className="text-xs text-[var(--text-muted)]">Revenue</p>
                </div>
                <div>
                  <div className="flex items-center justify-center gap-1 text-[var(--text-muted)] mb-1">
                    <Calendar size={12} />
                  </div>
                  <p className="text-sm font-semibold">
                    {customer.last_order ? new Date(customer.last_order).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">Last Order</p>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
