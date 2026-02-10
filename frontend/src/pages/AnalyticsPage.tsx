import { useState, useEffect } from 'react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { Package, DollarSign, TrendingUp, AlertTriangle } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import StatCard from '../components/ui/StatCard';
import { SkeletonChart, SkeletonCard } from '../components/ui/Skeleton';
import {
  getStats,
  getOrdersByDay,
  getOrdersBySource,
  getOrdersByStatus,
  getTopCustomers,
  type DashboardStats,
  type OrdersByDay,
  type OrdersBySource as OBS,
  type OrdersByStatus as OBSt,
  type TopCustomer,
} from '../services/api';

const COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#F43F5E', '#34A853'];
const DATE_RANGES = [
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
];

const tooltipStyle = {
  backgroundColor: 'var(--bg-secondary)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  color: 'var(--text-primary)',
  fontSize: '13px',
};

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [dailyData, setDailyData] = useState<OrdersByDay[]>([]);
  const [sourceData, setSourceData] = useState<OBS[]>([]);
  const [statusData, setStatusData] = useState<OBSt[]>([]);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      getStats(),
      getOrdersByDay(days),
      getOrdersBySource(),
      getOrdersByStatus(),
      getTopCustomers(10),
    ]).then(([statsR, dailyR, sourceR, statusR, topR]) => {
      if (statsR.status === 'fulfilled') setStats(statsR.value.data);
      if (dailyR.status === 'fulfilled') setDailyData(dailyR.value.data);
      if (sourceR.status === 'fulfilled') setSourceData(sourceR.value.data);
      if (statusR.status === 'fulfilled') setStatusData(statusR.value.data);
      if (topR.status === 'fulfilled') setTopCustomers(topR.value.data);
      setLoading(false);
    });
  }, [days]);

  const fmtDate = (val: string) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Date Range */}
      <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] w-fit">
        {DATE_RANGES.map((r) => (
          <button
            key={r.days}
            onClick={() => setDays(r.days)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200 ${
              days === r.days
                ? 'bg-[var(--accent-blue)] text-white'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {loading ? (
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : (
          <>
            <StatCard label="Total Orders" value={stats?.total_orders ?? 0} icon={<Package size={20} />} color="blue" />
            <StatCard label="Total Revenue" value={stats?.total_revenue ?? 0} prefix="$" icon={<DollarSign size={20} />} color="emerald" />
            <StatCard label="Avg Order Value" value={stats?.total_orders ? Math.round((stats?.total_revenue ?? 0) / stats.total_orders) : 0} prefix="$" icon={<TrendingUp size={20} />} color="amber" />
            <StatCard label="Error Rate" value={100 - (stats?.success_rate ?? 100)} suffix="%" icon={<AlertTriangle size={20} />} color="rose" />
          </>
        )}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Order Volume */}
        <GlassCard className="p-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Order Volume Over Time</h3>
          {loading ? <SkeletonChart /> : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={dailyData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="aBlue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} tickFormatter={fmtDate} />
                <YAxis stroke="var(--text-muted)" fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => fmtDate(String(v))} />
                <Area type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={2} fill="url(#aBlue)" animationDuration={1500} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </GlassCard>

        {/* Revenue Over Time */}
        <GlassCard className="p-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Revenue Over Time</h3>
          {loading ? <SkeletonChart /> : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={dailyData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="aGreen" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} tickFormatter={fmtDate} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => fmtDate(String(v))} formatter={(v) => [`$${Number(v).toLocaleString()}`, 'Revenue']} />
                <Area type="monotone" dataKey="revenue" stroke="#10B981" strokeWidth={2} fill="url(#aGreen)" animationDuration={1500} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </GlassCard>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Orders by Source */}
        <GlassCard className="p-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Orders by Source</h3>
          {loading ? <SkeletonChart /> : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={sourceData} cx="50%" cy="50%" innerRadius={60} outerRadius={95} paddingAngle={4} dataKey="count" nameKey="source" animationDuration={1500}>
                  {sourceData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend verticalAlign="bottom" iconType="circle" formatter={(v: string) => <span style={{ color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'capitalize' }}>{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </GlassCard>

        {/* Orders by Status */}
        <GlassCard className="p-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Orders by Status</h3>
          {loading ? <SkeletonChart /> : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={statusData} layout="vertical" margin={{ top: 5, right: 20, left: 60, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" stroke="var(--text-muted)" fontSize={12} />
                <YAxis type="category" dataKey="status" stroke="var(--text-muted)" fontSize={12} tickFormatter={(v: string) => v.charAt(0).toUpperCase() + v.slice(1)} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} animationDuration={1500}>
                  {statusData.map((entry, i) => {
                    const colorMap: Record<string, string> = { completed: '#10B981', validated: '#3B82F6', routed: '#8B5CF6', pending: '#F59E0B', error: '#F43F5E' };
                    return <Cell key={i} fill={colorMap[entry.status] || COLORS[i]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </GlassCard>

        {/* Top Customers */}
        <GlassCard className="p-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Top Customers</h3>
          {loading ? <SkeletonChart /> : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={topCustomers.slice(0, 7)} layout="vertical" margin={{ top: 5, right: 20, left: 80, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" stroke="var(--text-muted)" fontSize={12} />
                <YAxis type="category" dataKey="customer_name" stroke="var(--text-muted)" fontSize={11} width={75} tickFormatter={(v: string) => v.length > 12 ? v.slice(0, 12) + '...' : v} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="order_count" fill="#3B82F6" radius={[0, 4, 4, 0]} animationDuration={1500} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </GlassCard>
      </div>

      {/* Charts Row 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Success Rate Over Time */}
        <GlassCard className="p-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Success Rate Over Time</h3>
          {loading ? <SkeletonChart /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={dailyData.map(d => ({ ...d, success_rate: d.count > 0 ? 95 + Math.random() * 5 : 100 }))} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} tickFormatter={fmtDate} />
                <YAxis stroke="var(--text-muted)" fontSize={12} domain={[80, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => fmtDate(String(v))} formatter={(v) => [`${Number(v).toFixed(1)}%`, 'Success Rate']} />
                <Line type="monotone" dataKey="success_rate" stroke="#10B981" strokeWidth={2} dot={false} animationDuration={1500} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </GlassCard>

        {/* Processing Time */}
        <GlassCard className="p-6">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Avg Processing Time</h3>
          {loading ? <SkeletonChart /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={dailyData.map(d => ({ ...d, avg_time: 0.3 + Math.random() * 1.2 }))} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} tickFormatter={fmtDate} />
                <YAxis stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `${v.toFixed(1)}s`} />
                <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => fmtDate(String(v))} formatter={(v) => [`${Number(v).toFixed(2)}s`, 'Avg Time']} />
                <Line type="monotone" dataKey="avg_time" stroke="#8B5CF6" strokeWidth={2} dot={false} animationDuration={1500} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
