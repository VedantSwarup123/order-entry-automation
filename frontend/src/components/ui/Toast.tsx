import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { CheckCircle2, AlertTriangle, X, Info } from 'lucide-react';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface ToastContextType {
  toast: (type: Toast['type'], message: string) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: Toast['type'], message: string) => {
    const id = Math.random().toString(36).slice(2);
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  const icons = {
    success: <CheckCircle2 size={16} className="text-[var(--accent-emerald)]" />,
    error: <AlertTriangle size={16} className="text-[var(--accent-rose)]" />,
    info: <Info size={16} className="text-[var(--accent-blue)]" />,
  };

  const borderColors = {
    success: 'border-l-[var(--accent-emerald)]',
    error: 'border-l-[var(--accent-rose)]',
    info: 'border-l-[var(--accent-blue)]',
  };

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      {/* Toast Container */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] border-l-4 ${borderColors[t.type]} shadow-xl backdrop-blur-xl animate-slide-left min-w-[300px] max-w-[420px]`}
          >
            {icons[t.type]}
            <p className="text-sm flex-1">{t.message}</p>
            <button
              onClick={() => removeToast(t.id)}
              className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
