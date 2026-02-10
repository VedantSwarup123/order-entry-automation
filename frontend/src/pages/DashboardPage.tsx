import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Package, CalendarDays, CheckCircle2, DollarSign, Activity } from 'lucide-react';
import StatCard from '../components/ui/StatCard';
import GlassCard from '../components/ui/GlassCard';
import StatusBadge from '../components/ui/StatusBadge';
import SourceBadge from '../components/ui/SourceBadge';
import { SkeletonCard, SkeletonTable } from '../components/ui/Skeleton';
import OrderVolumeChart from '../components/charts/OrderVolumeChart';
import OrdersBySourceChart from '../components/charts/OrdersBySourceChart';
import {
  getStats,
  getOrders,
  getOrdersByDay,
  getOrdersBySource,
  getRecentActivity,
  type DashboardStats,
  type OrderSummary,
  type OrdersByDay,
  type OrdersBySource as OrdersBySourceType,
  type AuditEntry,
} from '../services/api';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentOrders, setRecentOrders] = useState<OrderSummary[]>([]);
  const [dailyData, setDailyData] = useState<OrdersByDay[]>([]);
  const [sourceData, setSourceData] = useState<OrdersBySourceType[]>([]);
  const [activity, setActivity] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [statsRes, ordersRes, dailyRes, sourceRes, activityRes] = await Promise.allSettled([
          getStats(),
          getOrders({ limit: 10 }),
          getOrdersByDay(30),
          getOrdersBySource(),
          getRecentActivity(),
        ]);

        if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
        if (ordersRes.status === 'fulfilled') setRecentOrders(ordersRes.value.data.orders);
        if (dailyRes.status === 'fulfilled') setDailyData(dailyRes.value.data);
        if (sourceRes.status === 'fulfilled') setSourceData(sourceRes.value.data);
        if (activityRes.status === 'fulfilled') setActivity(activityRes.value.data);
      } catch {
        // Silently handle — dashboard degrades gracefully
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  const formatTimeAgo = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays}d ago`;
  };

  return (
    <div className="space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <StatCard
              label="Total Orders"
              value={stats?.total_orders ?? 0}
              icon={<Package size={20} />}
              trend={stats?.trends.orders_change}
              color="blue"
              delay={0}
            />
            <StatCard
              label="Orders Today"
              value={stats?.orders_today ?? 0}
              icon={<CalendarDays size={20} />}
              color="emerald"
              delay={100}
            />
            <StatCard
              label="Success Rate"
              value={stats?.success_rate ?? 0}
              icon={<CheckCircle2 size={20} />}
              suffix="%"
              color="amber"
              delay={200}
            />
            <StatCard
              label="Total Revenue"
              value={stats?.total_revenue ?? 0}
              icon={<DollarSign size={20} />}
              trend={stats?.trends.revenue_change}
              prefix="$"
              color="purple"
              delay={300}
            />
          </>
        )}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OrderVolumeChart data={dailyData} loading={loading} />
        <OrdersBySourceChart data={sourceData} loading={loading} />
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Orders */}
        <div className="lg:col-span-2">
          <GlassCard className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-[var(--text-secondary)]">Recent Orders</h3>
              <button
                onClick={() => navigate('/orders')}
                className="text-xs text-[var(--accent-blue)] hover:underline"
              >
                View all
              </button>
            </div>
            {loading ? (
              <SkeletonTable rows={5} />
            ) : recentOrders.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-[var(--text-muted)]">
                <Package size={40} className="mb-3 opacity-40" />
                <p className="text-sm">No orders yet</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                      <th className="pb-3 pr-4 font-medium">Customer</th>
                      <th className="pb-3 pr-4 font-medium">PO Number</th>
                      <th className="pb-3 pr-4 font-medium">Amount</th>
                      <th className="pb-3 pr-4 font-medium">Status</th>
                      <th className="pb-3 pr-4 font-medium">Source</th>
                      <th className="pb-3 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentOrders.map((order) => (
                      <tr
                        key={order.id}
                        onClick={() => navigate(`/orders/${order.id}`)}
                        className="border-b border-[var(--border)] last:border-0 cursor-pointer hover:bg-[var(--bg-card-hover)] transition-colors"
                      >
                        <td className="py-3 pr-4">{order.customer_name || order.customer_id}</td>
                        <td className="py-3 pr-4 text-[var(--text-secondary)]">{order.po_number}</td>
                        <td className="py-3 pr-4 font-medium">${Number(order.total_amount).toLocaleString()}</td>
                        <td className="py-3 pr-4"><StatusBadge status={order.status} /></td>
                        <td className="py-3 pr-4"><SourceBadge source={order.source} /></td>
                        <td className="py-3 text-[var(--text-muted)] text-xs">{formatTimeAgo(order.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </GlassCard>
        </div>

        {/* Activity Feed */}
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={16} className="text-[var(--accent-blue)]" />
            <h3 className="text-sm font-semibold text-[var(--text-secondary)]">Activity Feed</h3>
          </div>
          {loading ? (
            <div className="space-y-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex gap-3">
                  <div className="w-2 h-2 rounded-full mt-1.5 bg-[var(--bg-card-hover)]" />
                  <div className="flex-1 space-y-1">
                    <div className="h-3 w-3/4 rounded bg-[var(--bg-card-hover)]" />
                    <div className="h-2 w-1/3 rounded bg-[var(--bg-card-hover)]" />
                  </div>
                </div>
              ))}
            </div>
          ) : activity.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-[var(--text-muted)]">
              <Activity size={32} className="mb-3 opacity-40" />
              <p className="text-sm">No recent activity</p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[400px] overflow-y-auto pr-1">
              {activity.slice(0, 15).map((entry) => (
                <div key={entry.id} className="flex gap-3 group">
                  <div className="w-2 h-2 rounded-full mt-1.5 bg-[var(--accent-blue)] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--text-primary)] truncate">
                      Order <span className="text-[var(--accent-blue)] font-mono text-xs">{entry.order_id.slice(0, 8)}</span> {entry.action}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{entry.detail}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{formatTimeAgo(entry.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
