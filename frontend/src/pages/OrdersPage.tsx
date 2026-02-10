import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, PlusCircle, Package, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import StatusBadge from '../components/ui/StatusBadge';
import SourceBadge from '../components/ui/SourceBadge';
import { SkeletonTable } from '../components/ui/Skeleton';
import { getOrders, type OrderSummary } from '../services/api';

const STATUSES = ['all', 'pending', 'validated', 'routed', 'completed', 'error'];
const SOURCES = ['all', 'email', 'csv', 'api', 'manual', 'fax', 'sheets'];
const PAGE_SIZE = 15;

export default function OrdersPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [sortField, setSortField] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [loading, setLoading] = useState(true);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getOrders({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        source: sourceFilter !== 'all' ? sourceFilter : undefined,
        search: search || undefined,
        sort: sortField,
        order: sortOrder,
      });
      setOrders(res.data.orders);
      setTotal(res.data.total);
      setTotalPages(res.data.pages);
    } catch {
      // Degrade gracefully
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, sourceFilter, sortField, sortOrder]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const handleFilterChange = () => {
    setPage(1);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 w-full sm:w-auto">
          {/* Search */}
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-secondary)] flex-1 max-w-md">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search by customer, PO, order ID..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); handleFilterChange(); }}
              className="bg-transparent outline-none text-sm w-full text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
            />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); handleFilterChange(); }}
              className="pl-8 pr-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-sm text-[var(--text-primary)] outline-none appearance-none cursor-pointer"
            >
              {STATUSES.map(s => (
                <option key={s} value={s} className="bg-[var(--bg-secondary)]">
                  {s === 'all' ? 'All Status' : s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Source Filter */}
          <select
            value={sourceFilter}
            onChange={(e) => { setSourceFilter(e.target.value); handleFilterChange(); }}
            className="px-3 py-2 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-sm text-[var(--text-primary)] outline-none appearance-none cursor-pointer"
          >
            {SOURCES.map(s => (
              <option key={s} value={s} className="bg-[var(--bg-secondary)]">
                {s === 'all' ? 'All Sources' : s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={() => navigate('/orders/new')}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-blue)] text-white text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <PlusCircle size={16} />
          New Order
        </button>
      </div>

      {/* Table */}
      <GlassCard className="overflow-hidden">
        {loading ? (
          <div className="p-6">
            <SkeletonTable rows={8} />
          </div>
        ) : orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-[var(--text-muted)]">
            <Package size={48} className="mb-4 opacity-40" />
            <p className="text-lg font-medium mb-1">No orders found</p>
            <p className="text-sm">Try adjusting your filters or create a new order.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)] bg-[var(--bg-secondary)]/50">
                    {[
                      { key: 'id', label: 'Order ID' },
                      { key: 'customer_name', label: 'Customer' },
                      { key: 'po_number', label: 'PO Number' },
                      { key: 'source', label: 'Source' },
                      { key: 'total_quantity', label: 'Items' },
                      { key: 'total_amount', label: 'Total' },
                      { key: 'status', label: 'Status' },
                      { key: 'created_at', label: 'Date' },
                    ].map(col => (
                      <th
                        key={col.key}
                        onClick={() => handleSort(col.key)}
                        className="px-6 py-3 font-medium cursor-pointer hover:text-[var(--text-primary)] transition-colors select-none"
                      >
                        <div className="flex items-center gap-1">
                          {col.label}
                          <ArrowUpDown size={12} className={sortField === col.key ? 'text-[var(--accent-blue)]' : 'opacity-30'} />
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr
                      key={order.id}
                      onClick={() => navigate(`/orders/${order.id}`)}
                      className="border-b border-[var(--border)] last:border-0 cursor-pointer hover:bg-[var(--bg-card-hover)] transition-colors"
                    >
                      <td className="px-6 py-4 font-mono text-xs text-[var(--accent-blue)]">
                        {order.id.slice(0, 8)}...
                      </td>
                      <td className="px-6 py-4">{order.customer_name || order.customer_id}</td>
                      <td className="px-6 py-4 text-[var(--text-secondary)]">{order.po_number}</td>
                      <td className="px-6 py-4"><SourceBadge source={order.source} /></td>
                      <td className="px-6 py-4 text-[var(--text-secondary)]">{order.item_count}</td>
                      <td className="px-6 py-4 font-medium">${Number(order.total_amount).toLocaleString()}</td>
                      <td className="px-6 py-4"><StatusBadge status={order.status} /></td>
                      <td className="px-6 py-4 text-[var(--text-muted)] text-xs">
                        {new Date(order.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-[var(--border)]">
              <p className="text-sm text-[var(--text-muted)]">
                Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total} orders
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-2 rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-sm text-[var(--text-secondary)] px-2">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-2 rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </GlassCard>
    </div>
  );
}
