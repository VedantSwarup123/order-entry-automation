interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusStyles: Record<string, { bg: string; text: string }> = {
  completed: { bg: 'rgba(16,185,129,0.1)', text: 'var(--accent-emerald)' },
  routed: { bg: 'rgba(16,185,129,0.1)', text: 'var(--accent-emerald)' },
  validated: { bg: 'rgba(59,130,246,0.1)', text: 'var(--accent-blue)' },
  pending: { bg: 'rgba(245,158,11,0.1)', text: 'var(--accent-amber)' },
  error: { bg: 'rgba(244,63,94,0.1)', text: 'var(--accent-rose)' },
};

export default function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const style = statusStyles[status] || statusStyles.pending;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium capitalize ${className}`}
      style={{ backgroundColor: style.bg, color: style.text }}
    >
      {status}
    </span>
  );
}
