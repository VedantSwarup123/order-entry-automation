import type { ReactNode } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { useAnimatedCounter } from '../../hooks/useAnimatedCounter';
import GlassCard from './GlassCard';

interface StatCardProps {
  label: string;
  value: number;
  icon: ReactNode;
  trend?: number;
  prefix?: string;
  suffix?: string;
  color: 'blue' | 'emerald' | 'amber' | 'rose' | 'purple';
  delay?: number;
}

const colorMap = {
  blue: { bg: 'rgba(59,130,246,0.1)', text: 'var(--accent-blue)', glow: 'var(--glow-blue)' },
  emerald: { bg: 'rgba(16,185,129,0.1)', text: 'var(--accent-emerald)', glow: 'var(--glow-emerald)' },
  amber: { bg: 'rgba(245,158,11,0.1)', text: 'var(--accent-amber)', glow: 'var(--glow-amber)' },
  rose: { bg: 'rgba(244,63,94,0.1)', text: 'var(--accent-rose)', glow: 'var(--glow-rose)' },
  purple: { bg: 'rgba(139,92,246,0.1)', text: '#8B5CF6', glow: '0 0 20px rgba(139,92,246,0.3)' },
};

export default function StatCard({ label, value, icon, trend, prefix = '', suffix = '', color, delay = 0 }: StatCardProps) {
  const animatedValue = useAnimatedCounter(value);
  const c = colorMap[color];

  return (
    <GlassCard
      className="p-6 opacity-0 animate-fade-in"
      hover
    >
      <div style={{ animationDelay: `${delay}ms` }} className="opacity-0 animate-fade-in">
        <div className="flex items-center justify-between mb-4">
          <div
            className="flex items-center justify-center w-10 h-10 rounded-lg"
            style={{ backgroundColor: c.bg }}
          >
            <div style={{ color: c.text }}>{icon}</div>
          </div>
          {trend !== undefined && (
            <div className={`flex items-center gap-1 text-sm font-medium ${trend >= 0 ? 'text-[var(--accent-emerald)]' : 'text-[var(--accent-rose)]'}`}>
              {trend >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {Math.abs(trend)}%
            </div>
          )}
        </div>
        <p className="text-sm text-[var(--text-secondary)] mb-1">{label}</p>
        <p className="text-3xl font-bold tracking-tight">
          {prefix}{animatedValue.toLocaleString()}{suffix}
        </p>
      </div>
    </GlassCard>
  );
}
