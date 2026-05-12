import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, FileText, LayoutDashboard, CheckSquare,
  Clock, PenLine, ShieldCheck, Boxes, AlertTriangle,
} from 'lucide-react'
import { api } from '../lib/api'
import { useContractSSE } from '../hooks/useContractSSE'
import { cn, formatFileSize, formatDateTime } from '../lib/utils'
import { StatusBadge } from '../components/ui/Badge'
import { AgentTimeline } from '../components/AgentTimeline'
import { MetadataPanel } from '../components/MetadataPanel'
import { SignaturesPanel } from '../components/SignaturesPanel'
import { ApprovalModal } from '../components/ApprovalModal'
import { ArchivePanel } from '../components/ArchivePanel'
import { PageLoader } from '../components/ui/Spinner'

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>()
  const [approvalOpen, setApprovalOpen] = useState(false)

  const { data: contract, isLoading, error } = useQuery({
    queryKey: ['contract', id],
    queryFn: () => api.contracts.get(id!),
    enabled: !!id,
  })

  useContractSSE(id)

  if (isLoading) return <Layout><PageLoader /></Layout>
  if (error || !contract) return (
    <Layout>
      <div className="card p-12 text-center text-slate-500">
        Contrat introuvable.{' '}
        <Link to="/" className="text-indigo-600 hover:underline">Retour</Link>
      </div>
    </Layout>
  )

  const needsApproval = contract.status === 'awaiting_approval'
  const hasSignatures = contract.signatures.length > 0
  const isArchived = contract.status === 'archived'

  return (
    <Layout>
      {/* Back + breadcrumb */}
      <div className="mb-6">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-indigo-600 transition-colors mb-4">
          <ArrowLeft size={15} />
          Tous les contrats
        </Link>

        {/* Hero */}
        <div className="card px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4 min-w-0">
              <div className={cn(
                'w-12 h-12 rounded-2xl flex items-center justify-center shrink-0',
                isArchived ? 'bg-emerald-100' : needsApproval ? 'bg-amber-100' : 'bg-indigo-100',
              )}>
                <FileText size={22} className={cn(
                  isArchived ? 'text-emerald-600' : needsApproval ? 'text-amber-600' : 'text-indigo-600',
                )} />
              </div>
              <div className="min-w-0">
                <h1 className="text-xl font-bold text-slate-900 truncate">{contract.original_name}</h1>
                <div className="flex flex-wrap items-center gap-3 mt-1.5">
                  <StatusBadge status={contract.status} />
                  {contract.file_size_bytes != null && (
                    <span className="text-xs text-slate-400">{formatFileSize(contract.file_size_bytes)}</span>
                  )}
                  <span className="text-xs text-slate-400">{formatDateTime(contract.created_at)}</span>
                </div>
              </div>
            </div>

            {/* Approval CTA */}
            {needsApproval && (
              <button
                onClick={() => setApprovalOpen(true)}
                className="btn-primary shrink-0 shadow-lg shadow-indigo-200"
              >
                <CheckSquare size={16} />
                Valider le circuit
              </button>
            )}
          </div>

          {/* Approval alert banner */}
          {needsApproval && (
            <div className="mt-4 flex items-center gap-3 p-3 rounded-xl bg-amber-50 border border-amber-200">
              <AlertTriangle size={16} className="text-amber-600 shrink-0" />
              <p className="text-sm text-amber-800">
                L'agent a proposé un circuit de signature. Veuillez le valider pour continuer le traitement.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — Timeline */}
        <div className="lg:col-span-2 space-y-6">
          <Section title="Pipeline agent" icon={Boxes}>
            <AgentTimeline steps={contract.steps} />
          </Section>
        </div>

        {/* Right column — Metadata, Signatures, Archive */}
        <div className="space-y-6">
          {contract.metadata && (
            <Section title="Analyse du contrat" icon={FileText}>
              <MetadataPanel metadata={contract.metadata} />
            </Section>
          )}

          {hasSignatures && (
            <Section title="Signatures" icon={PenLine}>
              <SignaturesPanel signatures={contract.signatures} />
            </Section>
          )}

          {isArchived && contract.archive && (
            <Section title="Archive sécurisée" icon={ShieldCheck}>
              <ArchivePanel archive={contract.archive} />
            </Section>
          )}

          {/* Processing placeholder */}
          {!contract.metadata && !hasSignatures && !isArchived && (
            <div className="card p-6 text-center text-sm text-slate-400">
              <Clock size={28} className="mx-auto mb-2 text-slate-200" />
              L'analyse débutera dans quelques instants…
            </div>
          )}
        </div>
      </div>

      {/* Approval modal */}
      <ApprovalModal
        open={approvalOpen}
        onClose={() => setApprovalOpen(false)}
        contract={contract}
      />
    </Layout>
  )
}

// ── Layout wrapper ─────────────────────────────────────────────────────────────

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-100 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center">
              <LayoutDashboard size={16} className="text-white" />
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              ContractFlow
            </span>
          </Link>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
    </div>
  )
}

// ── Section card ───────────────────────────────────────────────────────────────

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: typeof FileText
  children: React.ReactNode
}) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-slate-50">
        <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center">
          <Icon size={14} className="text-indigo-600" />
        </div>
        <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}
