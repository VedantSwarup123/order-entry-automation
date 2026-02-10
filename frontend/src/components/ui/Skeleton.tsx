interface SkeletonProps {
  className?: string;
}

export default function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`rounded-lg bg-gradient-to-r from-[var(--bg-card)] via-[var(--bg-card-hover)] to-[var(--bg-card)] bg-[length:200%_100%] ${className}`}
      style={{ animation: 'shimmer 1.5s infinite linear' }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-10 w-10" />
        <Skeleton className="h-5 w-12" />
      </div>
      <Skeleton className="h-4 w-20 mb-2" />
      <Skeleton className="h-8 w-28" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-14 w-full" />
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return <Skeleton className="h-64 w-full" />;
}
