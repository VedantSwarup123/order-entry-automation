import type { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export default function GlassCard({ children, className = '', hover = false, onClick }: GlassCardProps) {
  return (
    <div
      onClick={onClick}
      className={`
        rounded-xl border border-[var(--border)] bg-[var(--bg-card)] backdrop-blur-xl
        ${hover ? 'cursor-pointer transition-all duration-300 hover:border-[var(--border-hover)] hover:bg-[var(--bg-card-hover)] hover:shadow-lg hover:scale-[1.01]' : ''}
        ${onClick ? 'cursor-pointer' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
}
