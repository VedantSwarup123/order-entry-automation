import { Link } from 'react-router-dom';
import { Home, FileQuestion } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] animate-fade-in">
      <FileQuestion size={64} className="text-[var(--text-muted)] mb-6" />
      <h2 className="text-3xl font-bold mb-2">Page Not Found</h2>
      <p className="text-[var(--text-secondary)] mb-8">The page you're looking for doesn't exist.</p>
      <Link
        to="/"
        className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[var(--accent-blue)] text-white font-medium hover:opacity-90 transition-opacity"
      >
        <Home size={16} />
        Back to Dashboard
      </Link>
    </div>
  );
}
