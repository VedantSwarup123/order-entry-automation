import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { OrdersBySource } from '../../services/api';
import GlassCard from '../ui/GlassCard';
import { SkeletonChart } from '../ui/Skeleton';

interface Props {
  data: OrdersBySource[];
  loading?: boolean;
}

const COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#F43F5E', '#34A853'];

export default function OrdersBySourceChart({ data, loading }: Props) {
  if (loading) {
    return (
      <GlassCard className="p-6">
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Orders by Source</h3>
        <SkeletonChart />
      </GlassCard>
    );
  }

  return (
    <GlassCard className="p-6">
      <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-4">Orders by Source</h3>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={65}
            outerRadius={100}
            paddingAngle={4}
            dataKey="count"
            nameKey="source"
            animationDuration={1500}
          >
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '13px',
            }}
            formatter={(value, name) => [String(value), String(name).charAt(0).toUpperCase() + String(name).slice(1)]}
          />
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            formatter={(value: string) => (
              <span style={{ color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'capitalize' }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </GlassCard>
  );
}
