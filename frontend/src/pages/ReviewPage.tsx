import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Eye,
  ChevronRight,
  Brain,
  FileText,
  Shield,
  Clock,
  Edit3,
} from 'lucide-react';
import { getReviewItems, actionReviewItem, type ReviewItem } from '../services/api';
import { useToast } from '../components/ui/Toast';

const confidenceColor = (c: number) => {
  if (c >= 0.8) return 'text-[var(--accent-emerald)]';
  if (c >= 0.6) return 'text-[var(--accent-amber)]';
  return 'text-[var(--accent-rose)]';
};

const confidenceBg = (c: number) => {
  if (c >= 0.8) return 'bg-[var(--accent-emerald)]/10 border-[var(--accent-emerald)]/20';
  if (c >= 0.6) return 'bg-[var(--accent-amber)]/10 border-[var(--accent-amber)]/20';
  return 'bg-[var(--accent-rose)]/10 border-[var(--accent-rose)]/20';
};

const statusStyles: Record<string, string> = {
  pending: 'bg-[var(--accent-amber)]/10 text-[var(--accent-amber)] border-[var(--accent-amber)]/20',
  approved: 'bg-[var(--accent-emerald)]/10 text-[var(--accent-emerald)] border-[var(--accent-emerald)]/20',
  rejected: 'bg-[var(--accent-rose)]/10 text-[var(--accent-rose)] border-[var(--accent-rose)]/20',
  modified: 'bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] border-[var(--accent-blue)]/20',
};

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('pending');
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const { toast } = useToast();
  const navigate = useNavigate();

  const fetchItems = async () => {
    setLoading(true);
    try {
      const { data } = await getReviewItems({ status: filter || undefined });
      setItems(data.items);
    } catch {
      setItems([]);
    }
    setLoading(false);
  };

  useEffect(() => { fetchItems(); }, [filter]);

  const handleAction = async (item: ReviewItem, action: string) => {
    setActionLoading(true);
    try {
      await actionReviewItem(item.id, { action, notes: reviewNotes });
      toast('success', `Order ${action}ed successfully`);
      setSelectedItem(null);
      setReviewNotes('');
      fetchItems();
    } catch {
      toast('error', `Failed to ${action} order`);
    }
    setActionLoading(false);
  };

  const pendingCount = items.filter(i => i.status === 'pending').length;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Review Queue</h2>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Orders requiring human verification before processing
          </p>
        </div>
        {filter === 'pending' && pendingCount > 0 && (
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-amber)]/10 border border-[var(--accent-amber)]/20">
            <AlertTriangle size={16} className="text-[var(--accent-amber)]" />
            <span className="text-sm font-medium text-[var(--accent-amber)]">
              {pendingCount} pending review{pendingCount !== 1 ? 's' : ''}
            </span>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {['pending', 'approved', 'rejected', 'modified', ''].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 border ${
              filter === f
                ? 'bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] border-[var(--accent-blue)]/20'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--bg-card)] border-[var(--border)] hover:bg-[var(--bg-card-hover)]'
            }`}
          >
            {f || 'All'}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-[var(--text-muted)]">
          <Shield size={48} className="mb-4 opacity-40" />
          <p className="text-lg font-medium">No items in queue</p>
          <p className="text-sm mt-1">All orders have been reviewed</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className={`rounded-xl border bg-[var(--bg-card)] backdrop-blur-xl transition-all duration-200 hover:shadow-lg ${
                selectedItem?.id === item.id ? 'border-[var(--accent-blue)] ring-1 ring-[var(--accent-blue)]/20' : 'border-[var(--border)]'
              }`}
            >
              {/* Item Header */}
              <div
                className="flex items-center gap-4 px-6 py-4 cursor-pointer"
                onClick={() => setSelectedItem(selectedItem?.id === item.id ? null : item)}
              >
                {/* Confidence Indicator */}
                <div className={`flex items-center justify-center w-12 h-12 rounded-xl border ${confidenceBg(item.confidence)}`}>
                  <span className={`text-lg font-bold ${confidenceColor(item.confidence)}`}>
                    {Math.round(item.confidence * 100)}
                  </span>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-[var(--text-primary)]">
                      {item.customer_name || 'Unknown Customer'}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${statusStyles[item.status] || statusStyles.pending}`}>
                      {item.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-sm text-[var(--text-secondary)]">
                    <span>PO: {item.po_number || 'N/A'}</span>
                    <span className="flex items-center gap-1">
                      <Brain size={12} />
                      {item.extraction_method}
                    </span>
                    <span className="flex items-center gap-1">
                      <FileText size={12} />
                      {item.source}
                    </span>
                    {item.anomalies.length > 0 && (
                      <span className="flex items-center gap-1 text-[var(--accent-rose)]">
                        <AlertTriangle size={12} />
                        {item.anomalies.length} anomal{item.anomalies.length === 1 ? 'y' : 'ies'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); navigate(`/orders/${item.order_id}`); }}
                    className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors"
                    title="View Order"
                  >
                    <Eye size={16} />
                  </button>
                  <ChevronRight
                    size={16}
                    className={`text-[var(--text-muted)] transition-transform duration-200 ${
                      selectedItem?.id === item.id ? 'rotate-90' : ''
                    }`}
                  />
                </div>
              </div>

              {/* Expanded Detail */}
              {selectedItem?.id === item.id && (
                <div className="border-t border-[var(--border)] px-6 py-5 space-y-5 animate-fade-in">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Left: Original Text */}
                    <div>
                      <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-2 flex items-center gap-2">
                        <FileText size={14} />
                        Original Text
                      </h4>
                      <pre className="text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] rounded-lg p-4 overflow-auto max-h-64 border border-[var(--border)] whitespace-pre-wrap font-mono">
                        {item.original_text || 'No original text available'}
                      </pre>
                    </div>

                    {/* Right: Extracted Data */}
                    <div>
                      <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-2 flex items-center gap-2">
                        <Brain size={14} />
                        Extracted Data
                      </h4>
                      <pre className="text-xs text-[var(--text-secondary)] bg-[var(--bg-secondary)] rounded-lg p-4 overflow-auto max-h-64 border border-[var(--border)] whitespace-pre-wrap font-mono">
                        {JSON.stringify(item.extracted_data, null, 2)}
                      </pre>
                    </div>
                  </div>

                  {/* Anomalies */}
                  {item.anomalies.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-[var(--accent-rose)] mb-2 flex items-center gap-2">
                        <AlertTriangle size={14} />
                        Anomalies Detected
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {item.anomalies.map((a, i) => (
                          <span
                            key={i}
                            className="px-3 py-1.5 text-xs rounded-lg bg-[var(--accent-rose)]/10 text-[var(--accent-rose)] border border-[var(--accent-rose)]/20"
                          >
                            {a}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Confidence Bar */}
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-[var(--text-secondary)]">Extraction Confidence</span>
                      <span className={`font-semibold ${confidenceColor(item.confidence)}`}>
                        {Math.round(item.confidence * 100)}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-[var(--bg-secondary)] overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          item.confidence >= 0.8 ? 'bg-[var(--accent-emerald)]' :
                          item.confidence >= 0.6 ? 'bg-[var(--accent-amber)]' :
                          'bg-[var(--accent-rose)]'
                        }`}
                        style={{ width: `${item.confidence * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Review Actions */}
                  {item.status === 'pending' && (
                    <div className="space-y-3">
                      <textarea
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        placeholder="Add review notes (optional)..."
                        className="w-full px-4 py-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none focus:border-[var(--accent-blue)] transition-colors resize-none"
                        rows={2}
                      />
                      <div className="flex gap-3">
                        <button
                          onClick={() => handleAction(item, 'approve')}
                          disabled={actionLoading}
                          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--accent-emerald)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                        >
                          <CheckCircle2 size={16} />
                          Approve
                        </button>
                        <button
                          onClick={() => handleAction(item, 'reject')}
                          disabled={actionLoading}
                          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--accent-rose)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                        >
                          <XCircle size={16} />
                          Reject
                        </button>
                        <button
                          onClick={() => handleAction(item, 'modify')}
                          disabled={actionLoading}
                          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--accent-blue)] text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
                        >
                          <Edit3 size={16} />
                          Modify & Approve
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Already reviewed */}
                  {item.status !== 'pending' && item.reviewed_at && (
                    <div className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                      <Clock size={14} />
                      Reviewed {new Date(item.reviewed_at).toLocaleString()}
                      {item.reviewer_notes && (
                        <span className="ml-2 text-[var(--text-muted)]">
                          — {item.reviewer_notes}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
