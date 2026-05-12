import { useState } from 'react'
import { Building2, Calendar, Scale, CreditCard, AlertTriangle, ChevronDown, ChevronRight } from 'lucide-react'
import { cn, formatDate, formatAmount, CONTRACT_TYPE_LABEL } from '../lib/utils'
import { RiskBadge } from './ui/Badge'
import type { ContractMetadata } from '../lib/types'

interface Props { metadata: ContractMetadata }

export function MetadataPanel({ metadata: m }: Props) {
  const [clausesOpen, setClausesOpen] = useState(false)

  return (
    <div className="space-y-4">
      {/* Type + risk */}
      {(m.contract_type || m.risk_level) && (
        <div className="flex flex-wrap gap-2">
          {m.contract_type && (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700">
              {CONTRACT_TYPE_LABEL[m.contract_type] ?? m.contract_type}
            </span>
          )}
          {m.risk_level && <RiskBadge level={m.risk_level} />}
        </div>
      )}

      {/* Justification */}
      {m.classification_justification && (
        <p className="text-xs text-slate-500 leading-relaxed bg-slate-50 rounded-xl p-3 border border-slate-100">
          {m.classification_justification}
        </p>
      )}

      {/* Key details */}
      <div className="grid grid-cols-2 gap-3">
        {m.amount != null && (
          <Detail icon={CreditCard} label="Montant" value={formatAmount(m.amount, m.currency)} />
        )}
        {m.start_date && (
          <Detail icon={Calendar} label="Début" value={formatDate(m.start_date)} />
        )}
        {m.end_date && (
          <Detail icon={Calendar} label="Fin" value={formatDate(m.end_date)} />
        )}
        {m.duration_months != null && (
          <Detail icon={Calendar} label="Durée" value={`${m.duration_months} mois`} />
        )}
        {m.jurisdiction && (
          <Detail icon={Scale} label="Juridiction" value={m.jurisdiction} />
        )}
        {m.payment_terms && (
          <Detail icon={CreditCard} label="Paiement" value={m.payment_terms} />
        )}
      </div>

      {/* Parties */}
      {m.parties && m.parties.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Parties</p>
          <div className="space-y-2">
            {m.parties.map((p, i) => (
              <div key={i} className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
                  <Building2 size={14} className="text-indigo-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{p.name}</p>
                  <p className="text-xs text-slate-500 capitalize">{p.role}</p>
                  {p.address && <p className="text-xs text-slate-400 truncate mt-0.5">{p.address}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sensitive clauses */}
      {m.sensitive_clauses && m.sensitive_clauses.length > 0 && (
        <div>
          <button
            onClick={() => setClausesOpen(!clausesOpen)}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-amber-50 border border-amber-200
                       hover:bg-amber-100 transition-colors group"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle size={15} className="text-amber-600" />
              <span className="text-sm font-semibold text-amber-800">
                {m.sensitive_clauses.length} clause{m.sensitive_clauses.length > 1 ? 's' : ''} sensible{m.sensitive_clauses.length > 1 ? 's' : ''}
              </span>
            </div>
            {clausesOpen ? <ChevronDown size={15} className="text-amber-600" /> : <ChevronRight size={15} className="text-amber-600" />}
          </button>
          {clausesOpen && (
            <div className="mt-2 space-y-2">
              {m.sensitive_clauses.map((c, i) => (
                <div key={i} className={cn(
                  'p-3 rounded-xl border text-xs',
                  c.risk_level === 'high' ? 'bg-red-50 border-red-200' :
                  c.risk_level === 'medium' ? 'bg-amber-50 border-amber-200' :
                  'bg-slate-50 border-slate-200',
                )}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-700 capitalize">{c.type.replace(/_/g, ' ')}</span>
                    <RiskBadge level={c.risk_level} />
                  </div>
                  <p className="text-slate-600">{c.description}</p>
                  {c.excerpt && (
                    <p className="mt-1.5 italic text-slate-400 border-l-2 border-slate-200 pl-2">
                      « {c.excerpt} »
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function Detail({ icon: Icon, label, value }: { icon: typeof Building2; label: string; value: string }) {
  return (
    <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon size={12} className="text-slate-400" />
        <span className="text-xs text-slate-400">{label}</span>
      </div>
      <p className="text-sm font-medium text-slate-800 truncate">{value}</p>
    </div>
  )
}
