import { useState } from 'react'
import { Archive, Copy, Check, FileJson } from 'lucide-react'
import { cn, formatDateTime } from '../lib/utils'
import type { Archive as ArchiveType } from '../lib/types'

interface Props { archive: ArchiveType }

function CopyHash({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="flex items-center gap-2 group">
      <code className="flex-1 text-xs font-mono text-slate-600 bg-slate-50 px-3 py-2 rounded-lg border border-slate-200 truncate">
        {value.slice(0, 16)}…{value.slice(-8)}
      </code>
      <button
        onClick={copy}
        title="Copier le hash"
        className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
      >
        {copied ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
      </button>
    </div>
  )
}

export function ArchivePanel({ archive: a }: Props) {
  const [receiptOpen, setReceiptOpen] = useState(false)

  return (
    <div className="space-y-4">
      {/* Seal confirmed */}
      <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-50 border border-emerald-200">
        <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center shrink-0">
          <Archive size={17} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-emerald-800">Archivé avec sceau</p>
          <p className="text-xs text-emerald-600">{formatDateTime(a.archive_timestamp)}</p>
        </div>
      </div>

      {/* Hashes */}
      <div className="space-y-3">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Hash du document</p>
          <CopyHash value={a.document_hash} />
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Sceau d'intégrité</p>
          <CopyHash value={a.seal_hash} />
        </div>
      </div>

      {/* Receipt toggle */}
      <button
        onClick={() => setReceiptOpen(!receiptOpen)}
        className="w-full flex items-center gap-2 text-sm text-slate-600 hover:text-indigo-600
                   px-3 py-2.5 rounded-xl border border-slate-200 hover:border-indigo-200 hover:bg-indigo-50
                   transition-colors font-medium"
      >
        <FileJson size={15} />
        {receiptOpen ? 'Masquer' : 'Voir'} le reçu complet
      </button>

      {receiptOpen && (
        <pre className="text-xs bg-slate-900 text-emerald-400 p-4 rounded-xl overflow-x-auto
                        border border-slate-700 leading-relaxed max-h-64">
          {JSON.stringify(a.receipt_data, null, 2)}
        </pre>
      )}
    </div>
  )
}
