import { useState, useCallback } from 'react';
import { Mail, FileSpreadsheet, FileImage, Sheet, Upload, RefreshCw, CheckCircle2, Clock, AlertTriangle, Inbox } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import { uploadCsv } from '../services/api';

const TABS = [
  { id: 'email', label: 'Email', icon: Mail },
  { id: 'csv', label: 'CSV / Excel', icon: FileSpreadsheet },
  { id: 'fax', label: 'Fax', icon: FileImage },
  { id: 'sheets', label: 'Google Sheets', icon: Sheet },
];

interface InboxItem {
  id: string;
  from?: string;
  subject?: string;
  filename?: string;
  date: string;
  status: 'processed' | 'pending' | 'failed';
  detail?: string;
}

const mockEmails: InboxItem[] = [
  { id: '1', from: 'purchasing@example-distributor.com', subject: 'PO-2024-0891 - Monthly Order', date: '2024-03-15T10:30:00Z', status: 'processed', detail: '3 line items extracted' },
  { id: '2', from: 'orders@acme-corp.com', subject: 'RE: PO-2024-0445 Revised', date: '2024-03-14T16:20:00Z', status: 'processed', detail: '5 line items extracted' },
  { id: '3', from: 'john@bigretailer.com', subject: 'Urgent: PO-8832 ASAP', date: '2024-03-14T09:15:00Z', status: 'pending', detail: 'Awaiting review' },
  { id: '4', from: 'procurement@techcorp.io', subject: 'PO-TC-2024-112', date: '2024-03-13T14:00:00Z', status: 'failed', detail: 'No line items found' },
];

const mockCsvFiles: InboxItem[] = [
  { id: '1', filename: 'march_orders_batch1.csv', date: '2024-03-15T08:00:00Z', status: 'processed', detail: '45 rows, 12 orders created' },
  { id: '2', filename: 'q1_orders.xlsx', date: '2024-03-14T11:30:00Z', status: 'processed', detail: '120 rows, 28 orders created' },
  { id: '3', filename: 'weekly_restock.csv', date: '2024-03-13T09:00:00Z', status: 'processed', detail: '18 rows, 6 orders created' },
];

const mockFaxes: InboxItem[] = [
  { id: '1', filename: 'fax_20240315_001.pdf', date: '2024-03-15T11:45:00Z', status: 'processed', detail: 'OCR confidence: 94%' },
  { id: '2', filename: 'fax_20240314_003.pdf', date: '2024-03-14T15:20:00Z', status: 'pending', detail: 'OCR confidence: 52% — needs review' },
];

export default function InboxPage() {
  const [activeTab, setActiveTab] = useState('email');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true);
    setUploadResult(null);
    try {
      await uploadCsv(file);
      setUploadResult(`Successfully processed ${file.name}`);
    } catch {
      setUploadResult(`Failed to process ${file.name}`);
    } finally {
      setUploading(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }, [handleUpload]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const statusIcon = (status: string) => {
    if (status === 'processed') return <CheckCircle2 size={14} className="text-[var(--accent-emerald)]" />;
    if (status === 'pending') return <Clock size={14} className="text-[var(--accent-amber)]" />;
    return <AlertTriangle size={14} className="text-[var(--accent-rose)]" />;
  };

  const renderItems = (items: InboxItem[], type: 'email' | 'file') => (
    <div className="divide-y divide-[var(--border)]">
      {items.map(item => (
        <div key={item.id} className="flex items-center gap-4 px-6 py-4 hover:bg-[var(--bg-card-hover)] transition-colors cursor-pointer">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {type === 'email' ? item.subject : item.filename}
            </p>
            {type === 'email' && (
              <p className="text-xs text-[var(--text-muted)] mt-0.5">{item.from}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {statusIcon(item.status)}
            <span className="text-xs text-[var(--text-muted)] capitalize">{item.status}</span>
          </div>
          <span className="text-xs text-[var(--text-muted)] whitespace-nowrap">
            {new Date(item.date).toLocaleDateString()}
          </span>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] w-fit">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
              activeTab === tab.id
                ? 'bg-[var(--accent-blue)] text-white'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'email' && (
        <GlassCard className="overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--border)] flex items-center justify-between">
            <h3 className="text-sm font-semibold">Recent Emails</h3>
            <button className="flex items-center gap-1.5 text-xs text-[var(--accent-blue)] hover:underline">
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
          {mockEmails.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-[var(--text-muted)]">
              <Inbox size={40} className="mb-3 opacity-40" />
              <p className="text-sm">No emails received</p>
            </div>
          ) : (
            renderItems(mockEmails, 'email')
          )}
        </GlassCard>
      )}

      {activeTab === 'csv' && (
        <div className="space-y-6">
          {/* Upload Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 ${
              dragOver
                ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)]/5'
                : 'border-[var(--border)] hover:border-[var(--border-hover)]'
            }`}
          >
            <Upload size={32} className="mx-auto mb-4 text-[var(--text-muted)]" />
            <p className="text-sm font-medium mb-1">
              {uploading ? 'Processing...' : 'Drop a CSV or Excel file here'}
            </p>
            <p className="text-xs text-[var(--text-muted)] mb-4">or click to browse</p>
            <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--accent-blue)] text-white text-sm font-medium cursor-pointer hover:opacity-90 transition-opacity">
              <Upload size={14} />
              Browse Files
              <input type="file" accept=".csv,.xlsx,.xls" onChange={handleFileInput} className="hidden" />
            </label>
            {uploadResult && (
              <p className={`mt-4 text-sm ${uploadResult.startsWith('Success') ? 'text-[var(--accent-emerald)]' : 'text-[var(--accent-rose)]'}`}>
                {uploadResult}
              </p>
            )}
          </div>

          {/* Recent Files */}
          <GlassCard className="overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--border)]">
              <h3 className="text-sm font-semibold">Recently Processed Files</h3>
            </div>
            {renderItems(mockCsvFiles, 'file')}
          </GlassCard>
        </div>
      )}

      {activeTab === 'fax' && (
        <GlassCard className="overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--border)]">
            <h3 className="text-sm font-semibold">Processed Fax Documents</h3>
          </div>
          {mockFaxes.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-[var(--text-muted)]">
              <FileImage size={40} className="mb-3 opacity-40" />
              <p className="text-sm">No fax documents</p>
            </div>
          ) : (
            renderItems(mockFaxes, 'file')
          )}
        </GlassCard>
      )}

      {activeTab === 'sheets' && (
        <GlassCard className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-semibold">Google Sheets Integration</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--bg-secondary)]/50 border border-[var(--border)]">
              <div>
                <p className="text-sm font-medium">Connected Spreadsheet</p>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">Orders — Last polled 5 min ago</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[var(--accent-emerald)]" />
                <span className="text-xs text-[var(--accent-emerald)]">Connected</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--text-muted)]">Rows processed today</span>
              <span>24</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--text-muted)]">Orders created today</span>
              <span>8</span>
            </div>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border)] text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] transition-colors">
              <RefreshCw size={14} />
              Poll Now
            </button>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
