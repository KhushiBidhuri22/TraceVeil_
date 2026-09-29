import { api } from '../services/traceveil-api.js';
import { isConnected } from '../services/http.js';
import { text, PENDING } from '../utils/display.js';

export const EXPORT_FORMATS = ['csv', 'json', 'pdf'];

export function exportFilename(disposition, actor, format) {
  const match = /filename="?([^";]+)"?/i.exec(disposition ?? '');
  const safe = match?.[1]?.replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_');
  if (safe) return safe;
  return `traceveil-${String(actor.id || actor.handle || 'dossier').replace(/[^a-z0-9_-]/gi, '_')}.${format}`;
}

function generateClientCsv(actor) {
  const rows = [
    ['Category', 'Type', 'Identifier / Value', 'Relation', 'Confidence (%)', 'Observed Date', 'Source', 'Detail'],
    ['Profile', 'primary_handle', actor.handle || actor.id, 'PRIMARY', actor.confidence ?? 85, actor.lastSeen || '', 'TraceVeil Intelligence', `Actor ID: ${actor.id}`],
  ];

  for (const alias of actor.aliases || []) {
    rows.push(['Alias', 'handle', alias.handle || alias.name || '', 'ALIAS_OF', alias.confidence ?? 90, actor.lastSeen || '', 'Forum / Market Crawl', alias.detail || '']);
  }
  for (const key of actor.keys || []) {
    rows.push(['PGP Key', 'pgp_key', key.value || key.title || '', 'USES_PGP', key.confidence ?? 95, key.date || '', key.source || 'Public Keyserver', key.algorithm || key.detail || '']);
  }
  for (const wallet of actor.wallets || []) {
    rows.push(['Wallet', 'crypto_wallet', wallet.value || wallet.title || '', 'USES_WALLET', wallet.confidence ?? 85, wallet.date || '', wallet.source || 'Darkweb Ledger', wallet.network || wallet.detail || '']);
  }
  for (const source of actor.sources || []) {
    rows.push(['Source', 'source_feed', source.name || source.title || '', 'OBSERVED_ON', source.confidence ?? 80, source.observedAt || source.date || '', source.name || '', source.detail || '']);
  }
  for (const ev of actor.evidence || []) {
    rows.push(['Evidence', 'evidence_item', ev.detail || ev.title || '', 'EVIDENCE_FOR', ev.confidence ?? 85, ev.date || '', ev.source || '', ev.method || '']);
  }
  for (const event of actor.events || []) {
    rows.push(['Timeline Event', event.label || 'POST', event.title || '', 'POSTED_ON', event.confidence ?? 80, event.date || '', event.source || '', event.detail || '']);
  }

  return rows.map(r => r.map(field => `"${String(field ?? '').replace(/"/g, '""')}"`).join(',')).join('\r\n');
}

function generateClientJson(actor) {
  return JSON.stringify({
    report_type: 'traceveil_account_intelligence_record',
    version: '2.0.0',
    exported_at: new Date().toISOString(),
    actor: actor,
    note: 'Authorized threat intelligence export generated from TraceVeil Platform.',
  }, null, 2);
}

function generatePdfReport(actor) {
  const handle = text(actor.handle || actor.id);
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow popups to generate and print the PDF Intelligence Report.');
    return;
  }

  const aliasesHtml = (actor.aliases || []).map(a => `<li><strong>${text(a.handle || a.name)}</strong> ${a.confidence ? `(${a.confidence}% confidence)` : ''} - ${text(a.detail || '')}</li>`).join('') || '<li>No aliases recorded</li>';
  const keysHtml = (actor.keys || []).map(k => `<li><code>${text(k.value || k.title)}</code> (${text(k.algorithm || 'PGP')}) - Confidence: ${k.confidence ?? 95}%</li>`).join('') || '<li>No signing keys recorded</li>';
  const walletsHtml = (actor.wallets || []).map(w => `<li><code>${text(w.value || w.title)}</code> (${text(w.network || 'Cryptocurrency')}) - Confidence: ${w.confidence ?? 85}%</li>`).join('') || '<li>No wallet references recorded</li>';
  const sourcesHtml = (actor.sources || []).map(s => `<li><strong>${text(s.name || s.title)}</strong> observed at ${text(s.observedAt || s.date || 'N/A')}</li>`).join('') || '<li>No source records</li>';
  const eventsHtml = (actor.events || []).map(e => `<tr><td>${text(e.date || 'Undated')}</td><td><strong>${text(e.label || 'EVENT')}</strong></td><td>${text(e.title || e.detail)}</td><td>${text(e.source || '')}</td></tr>`).join('') || '<tr><td colspan="4">No timeline events recorded</td></tr>';

  printWindow.document.write(`
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>TraceVeil Intelligence Dossier - ${handle}</title>
      <style>
        body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; padding: 40px; color: #111; line-height: 1.5; background: #fff; }
        .header { border-bottom: 2px solid #044b35; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-end; }
        .header h1 { margin: 0; font-size: 26px; color: #044b35; letter-spacing: 0.05em; }
        .header .badge { font-size: 11px; background: #044b35; color: #fff; padding: 4px 8px; font-weight: bold; border-radius: 3px; }
        .meta-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 25px; background: #f4f8f6; padding: 18px; border-radius: 6px; border: 1px solid #d8e6df; }
        .meta-grid div strong { display: block; font-size: 11px; color: #555; text-transform: uppercase; letter-spacing: 0.05em; }
        .meta-grid div span { font-size: 16px; font-weight: 600; color: #111; }
        h2 { font-size: 16px; color: #044b35; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 25px; text-transform: uppercase; letter-spacing: 0.05em; }
        ul { padding-left: 20px; font-size: 13px; }
        li { margin-bottom: 6px; }
        code { background: #eee; padding: 2px 5px; font-family: monospace; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #eaf2ee; color: #044b35; }
        .footer { margin-top: 40px; border-top: 1px solid #ddd; padding-top: 10px; font-size: 10px; color: #777; display: flex; justify-content: space-between; }
        @media print {
          body { padding: 15px; }
          button { display: none; }
        }
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          <h1>TRACEVEIL / ACCOUNT INTELLIGENCE DOSSIER</h1>
          <p style="margin: 4px 0 0; font-size: 13px; color: #666;">Automated Darkweb Entity & Attribution Report</p>
        </div>
        <div>
          <span class="badge">CONFIDENTIAL / ANALYST ACCESS</span>
        </div>
      </div>

      <div class="meta-grid">
        <div><strong>Primary Handle / Actor</strong><span>${handle}</span></div>
        <div><strong>Actor ID</strong><span>${text(actor.id)}</span></div>
        <div><strong>Link Confidence Score</strong><span>${actor.confidence ?? 85}%</span></div>
        <div><strong>Last Observed Activity</strong><span>${text(actor.lastSeen || 'Recently Active')}</span></div>
      </div>

      <h2>Possible Aliases & Connected Profiles</h2>
      <ul>${aliasesHtml}</ul>

      <h2>Signing Keys (PGP)</h2>
      <ul>${keysHtml}</ul>

      <h2>Cryptocurrency Wallets</h2>
      <ul>${walletsHtml}</ul>

      <h2>Intelligence Sources Observed</h2>
      <ul>${sourcesHtml}</ul>

      <h2>Activity Timeline</h2>
      <table>
        <thead><tr><th>Timestamp</th><th>Type</th><th>Detail</th><th>Source</th></tr></thead>
        <tbody>${eventsHtml}</tbody>
      </table>

      <div class="footer">
        <span>Generated by TraceVeil Account Intelligence Platform</span>
        <span>Export Date: ${new Date().toUTCString()}</span>
      </div>

      <script>
        window.onload = function() { window.print(); };
      </script>
    </body>
    </html>
  `);
  printWindow.document.close();
}

export class ExportView {
  constructor({ dialogs, getActor, canRead, onStatus }) {
    Object.assign(this, { dialogs, getActor, canRead, onStatus });
    this.controller = null;
    document.querySelectorAll('[data-open-export]').forEach(button => button.addEventListener('click', () => this.open()));
    document.querySelectorAll('[data-export]').forEach(button => button.addEventListener('click', () => this.download(button.dataset.export)));
    document.querySelector('#export-dialog')?.addEventListener('close', () => this.cancel());
  }

  refresh(message) {
    const ready = this.canRead() && Boolean(this.getActor()?.id);
    document.querySelectorAll('[data-export]').forEach(button => {
      button.disabled = !ready || Boolean(this.controller);
      const span = button.querySelector('span');
      if (span) {
        span.textContent = ready ? ({
          csv: 'CSV · Connection records →',
          json: 'JSON · Intelligence record →',
          pdf: 'PDF · Printable dossier report →',
        }[button.dataset.export] || 'Export record →') : PENDING;
      }
    });
    const statusEl = document.querySelector('#export-status');
    if (statusEl) {
      statusEl.textContent = message ?? (ready ? 'Choose a format.' : PENDING);
    }
  }

  open() {
    this.refresh();
    const dialog = document.querySelector('#export-dialog');
    if (dialog) this.dialogs.open(dialog);
  }

  cancel() {
    this.controller?.abort();
    this.controller = null;
  }

  async download(format) {
    if (!EXPORT_FORMATS.includes(format)) {
      this.refresh('Choose CSV, JSON, or PDF.');
      return;
    }
    const actor = this.getActor();
    if (!actor || this.controller || !this.canRead()) return;

    if (format === 'pdf') {
      this.refresh('Generating PDF intelligence report…');
      generatePdfReport(actor);
      this.refresh('Report generated.');
      return;
    }

    const controller = new AbortController();
    this.controller = controller;
    this.refresh('Preparing download…');

    try {
      let fileBlob = null;
      let fileDisposition = null;

      if (isConnected('export')) {
        try {
          const result = await api.export(actor.id, format, controller.signal);
          if (controller.signal.aborted) return;
          if (result.status === 'ready' && result.data?.blob) {
            fileBlob = result.data.blob;
            fileDisposition = result.data.disposition;
          }
        } catch (apiErr) {
          // Fall back to client generation if endpoint unavailable
        }
      }

      if (!fileBlob) {
        const textContent = format === 'csv' ? generateClientCsv(actor) : generateClientJson(actor);
        const mimeType = format === 'csv' ? 'text/csv;charset=utf-8;' : 'application/json;charset=utf-8;';
        fileBlob = new Blob([textContent], { type: mimeType });
      }

      this.controller = null;
      const url = URL.createObjectURL(fileBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = exportFilename(fileDisposition, actor, format);
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      this.refresh('Download started.');
    } catch (error) {
      if (!controller.signal.aborted) {
        this.controller = null;
        this.refresh(error.message || 'Export could not be completed.');
      }
    }
  }
}
