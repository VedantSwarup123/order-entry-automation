import { Mail, FileSpreadsheet, Globe, PenLine, FileImage } from 'lucide-react';

interface SourceBadgeProps {
  source: string;
  className?: string;
}

const sourceConfig: Record<string, { icon: typeof Mail; color: string }> = {
  email: { icon: Mail, color: 'var(--accent-blue)' },
  csv: { icon: FileSpreadsheet, color: 'var(--accent-emerald)' },
  api: { icon: Globe, color: 'var(--accent-purple)' },
  manual: { icon: PenLine, color: 'var(--accent-amber)' },
  fax: { icon: FileImage, color: 'var(--accent-rose)' },
  sheets: { icon: FileSpreadsheet, color: '#34A853' },
};

export default function SourceBadge({ source, className = '' }: SourceBadgeProps) {
  const config = sourceConfig[source] || sourceConfig.api;
  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium capitalize ${className}`}
      style={{ backgroundColor: `color-mix(in srgb, ${config.color} 15%, transparent)`, color: config.color }}
    >
      <Icon size={12} />
      {source}
    </span>
  );
}
