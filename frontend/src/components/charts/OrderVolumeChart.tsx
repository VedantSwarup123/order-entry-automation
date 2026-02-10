import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { OrdersByDay } from '../../services/api';
import GlassCard from '../ui/GlassCard';
import { SkeletonChart } from '../ui/Skeleton';

interface Props {
  data: OrdersByDay[];
  loading?: boolean;
}

export default function OrderVolumeChart({ data, loading }: Props) {
  if (loading) {
    return (
      <GlassCard className="p-6">
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Order Volume</h3>
        <SkeletonChart />
      </GlassCard>
    );
  }

  return (
    <GlassCard className="p-6">
      <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Order Volume</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="blueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="date"
            stroke="var(--text-muted)"
            fontSize={12}
            tickFormatter={(val: string) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          />
          <YAxis stroke="var(--text-muted)" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '13px',
            }}
            labelFormatter={(val) => new Date(String(val)).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#3B82F6"
            strokeWidth={2}
            fill="url(#blueGradient)"
            animationDuration={1500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}
