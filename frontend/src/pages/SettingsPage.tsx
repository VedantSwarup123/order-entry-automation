import { useState, useEffect } from 'react';
import { Sun, Moon, Key, Globe, Link2, Bell, Route, CheckCircle2, XCircle, Copy, Check } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';
import { useTheme } from '../context/ThemeContext';
import { getIntegrations, getRoutingRules, type IntegrationStatus, type RoutingRule } from '../services/api';

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null);
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    Promise.allSettled([getIntegrations(), getRoutingRules()]).then(([intR, rulesR]) => {
      if (intR.status === 'fulfilled') setIntegrations(intR.value.data);
      if (rulesR.status === 'fulfilled') setRules(rulesR.value.data.rules);
    });
  }, []);

  const copyApiKey = () => {
    navigator.clipboard.writeText('dev-api-key-change-me');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const integrationItems = integrations
    ? [
        { name: 'Gmail', status: integrations.gmail },
        { name: 'Outlook', status: integrations.outlook },
        { name: 'Google Sheets', status: integrations.sheets },
        { name: 'Slack', status: integrations.slack },
      ]
    : [
        { name: 'Gmail', status: 'disconnected' },
        { name: 'Outlook', status: 'disconnected' },
        { name: 'Google Sheets', status: 'disconnected' },
        { name: 'Slack', status: 'disconnected' },
      ];

  return (
    <div className="max-w-4xl space-y-8 animate-fade-in">
      {/* General */}
      <section>
        <h2 className="text-lg font-semibold mb-4">General</h2>
        <GlassCard className="p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Application Name</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Displayed in the sidebar and browser tab</p>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">OrderFlow</p>
          </div>
          <div className="border-t border-[var(--border)]" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Theme</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Switch between dark and light mode</p>
            </div>
            <button
              onClick={toggleTheme}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border)] text-sm font-medium hover:bg-[var(--bg-card-hover)] transition-colors"
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </button>
          </div>
          <div className="border-t border-[var(--border)]" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Timezone</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Used for order timestamps</p>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{Intl.DateTimeFormat().resolvedOptions().timeZone}</p>
          </div>
        </GlassCard>
      </section>

      {/* API */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Key size={18} className="text-[var(--accent-blue)]" />
          API
        </h2>
        <GlassCard className="p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">API Key</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Used for authenticating API requests</p>
            </div>
            <div className="flex items-center gap-2">
              <code className="px-3 py-1.5 rounded-md bg-[var(--bg-secondary)] border border-[var(--border)] text-xs font-mono text-[var(--text-secondary)]">
                dev-api-key-change-me
              </code>
              <button
                onClick={copyApiKey}
                className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card-hover)] transition-colors"
              >
                {copied ? <Check size={14} className="text-[var(--accent-emerald)]" /> : <Copy size={14} />}
              </button>
            </div>
          </div>
          <div className="border-t border-[var(--border)]" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">API Endpoint</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Base URL for the REST API</p>
            </div>
            <div className="flex items-center gap-2">
              <Globe size={14} className="text-[var(--text-muted)]" />
              <code className="text-xs font-mono text-[var(--text-secondary)]">http://localhost:8000/api/v1</code>
            </div>
          </div>
        </GlassCard>
      </section>

      {/* Integrations */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Link2 size={18} className="text-[var(--accent-emerald)]" />
          Integrations
        </h2>
        <GlassCard className="divide-y divide-[var(--border)]">
          {integrationItems.map((item) => (
            <div key={item.name} className="flex items-center justify-between px-6 py-4">
              <p className="text-sm font-medium">{item.name}</p>
              <div className="flex items-center gap-2">
                {item.status === 'connected' ? (
                  <>
                    <CheckCircle2 size={14} className="text-[var(--accent-emerald)]" />
                    <span className="text-xs text-[var(--accent-emerald)]">Connected</span>
                  </>
                ) : (
                  <>
                    <XCircle size={14} className="text-[var(--text-muted)]" />
                    <span className="text-xs text-[var(--text-muted)]">Disconnected</span>
                  </>
                )}
              </div>
            </div>
          ))}
        </GlassCard>
      </section>

      {/* Routing Rules */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Route size={18} className="text-[var(--accent-amber)]" />
          Routing Rules
        </h2>
        <GlassCard className="overflow-hidden">
          {rules.length === 0 ? (
            <div className="p-6 text-center text-sm text-[var(--text-muted)]">
              No routing rules configured. Check config/routing_rules.yaml
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                  <th className="px-6 py-3 font-medium">Rule Name</th>
                  <th className="px-6 py-3 font-medium">Condition</th>
                  <th className="px-6 py-3 font-medium">Destination</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule, i) => (
                  <tr key={i} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-6 py-3">{rule.name}</td>
                    <td className="px-6 py-3 font-mono text-xs text-[var(--text-secondary)]">{rule.condition}</td>
                    <td className="px-6 py-3">
                      <span className="px-2 py-1 rounded-md bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] text-xs font-medium">
                        {rule.destination}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </GlassCard>
      </section>

      {/* Notifications */}
      <section>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Bell size={18} className="text-[var(--accent-rose)]" />
          Notifications
        </h2>
        <GlassCard className="p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Slack Channel</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Order notifications are sent here</p>
            </div>
            <code className="text-xs font-mono text-[var(--text-secondary)]">#orders</code>
          </div>
          <div className="border-t border-[var(--border)]" />
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Email Confirmations</p>
              <p className="text-xs text-[var(--text-muted)] mt-0.5">Send confirmation emails for completed orders</p>
            </div>
            <span className="text-xs text-[var(--text-muted)]">Disabled</span>
          </div>
        </GlassCard>
      </section>
    </div>
  );
}
