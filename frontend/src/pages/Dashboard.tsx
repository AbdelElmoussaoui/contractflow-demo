import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FileText, Plus, Trash2, ChevronRight,
  LayoutDashboard, CheckCircle, Clock, Archive, AlertTriangle,
} from 'lucide-react'
import { api } from '../lib/api'
import { cn, formatRelative, formatFileSize, STATUS_LABEL, isActiveStatus } from '../lib/utils'
import { StatusBadge } from '../components/ui/Badge'
import { UploadZone } from '../components/UploadZone'
import { PageLoader } from '../components/ui/Spinner'
import type { Contract, ContractStatus } from '../lib/types'

const STAT_GROUPS: { label: string; icon: typeof Clock; statuses: ContractStatus[]; color: string }[] = [
  { label: 'Total', icon: FileText, statuses: ['uploaded', 'processing', 'awaiting_approval', 'awaiting_signatures', 'verifying', 'archived', 'failed'], color: 'text-indigo-600 bg-indigo-100' },
  { label: 'En cours', icon: Clock, statuses: ['processing', 'awaiting_approval', 'awaiting_signatures', 'verifying'], color: 'text-amber-600 bg-amber-100' },
  { label: 'Archivés', icon: Archive, statuses: ['archived'], color: 'text-emerald-600 bg-emerald-100' },
  { label: 'Erreurs', icon: AlertTriangle, statuses: ['failed'], color: 'text-red-500 bg-red-100' },
]

export default function Dashboard() {
  const [showUpload, setShowUpload] = useState(false)
  const queryClient = useQueryClient()

  const { data: contracts = [], isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: api.contracts.list,
    refetchInterval: 8000,
  })

  const del = useMutation({
    mutationFn: api.contracts.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['contracts'] }),
  })

  function handleDelete(e: React.MouseEvent, id: string) {
    e.preventDefault()
    if (confirm('Supprimer ce contrat ?')) del.mutate(id)
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-100 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center">
              <LayoutDashboard size={16} className="text-white" />
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
              ContractFlow
            </span>
          </div>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className={cn('btn-primary', showUpload && 'bg-indigo-700')}
          >
            <Plus size={16} />
            Importer un contrat
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {STAT_GROUPS.map(({ label, icon: Icon, statuses, color }) => {
            const count = contracts.filter(c => (statuses as string[]).includes(c.status)).length
            return (
              <div key={label} className="card p-4 flex items-center gap-3">
                <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center shrink-0', color)}>
                  <Icon size={18} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-800">{count}</p>
                  <p className="text-xs text-slate-500">{label}</p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Upload zone */}
        {(showUpload || contracts.length === 0) && (
          <div className="mb-8 animate-slide-up">
            <UploadZone />
          </div>
        )}

        {/* Contract list */}
        <div>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">
            Contrats ({contracts.length})
          </h2>

          {isLoading ? (
            <PageLoader />
          ) : contracts.length === 0 ? (
            <div className="card flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                <FileText size={28} className="text-slate-300" />
              </div>
              <p className="text-slate-600 font-medium">Aucun contrat</p>
              <p className="text-sm text-slate-400 mt-1">Importez votre premier contrat PDF ci-dessus</p>
            </div>
          ) : (
            <div className="space-y-3">
              {contracts.map(contract => (
                <ContractRow
                  key={contract.id}
                  contract={contract}
                  onDelete={handleDelete}
                  deleting={del.isPending && del.variables === contract.id}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function ContractRow({
  contract: c,
  onDelete,
  deleting,
}: {
  contract: Contract
  onDelete: (e: React.MouseEvent, id: string) => void
  deleting: boolean
}) {
  return (
    <Link
      to={`/contracts/${c.id}`}
      className="card flex items-center gap-4 px-5 py-4 hover:shadow-md hover:border-indigo-100 transition-all group"
    >
      {/* Icon */}
      <div className={cn(
        'w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-colors',
        isActiveStatus(c.status) ? 'bg-indigo-100' : c.status === 'archived' ? 'bg-emerald-100' : c.status === 'failed' ? 'bg-red-100' : 'bg-slate-100',
      )}>
        <FileText size={18} className={cn(
          isActiveStatus(c.status) ? 'text-indigo-600' : c.status === 'archived' ? 'text-emerald-600' : c.status === 'failed' ? 'text-red-500' : 'text-slate-400',
        )} />
      </div>

      {/* Name + meta */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-800 truncate group-hover:text-indigo-700 transition-colors">
          {c.original_name}
        </p>
        <p className="text-xs text-slate-400 mt-0.5">
          {formatFileSize(c.file_size_bytes)} · {formatRelative(c.created_at)}
        </p>
      </div>

      {/* Status */}
      <StatusBadge status={c.status} />

      {/* Actions */}
      <div className="flex items-center gap-1 ml-2">
        <button
          onClick={(e) => onDelete(e, c.id)}
          disabled={deleting}
          className="p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
          title="Supprimer"
        >
          <Trash2 size={15} />
        </button>
        <ChevronRight size={16} className="text-slate-300 group-hover:text-indigo-400 transition-colors" />
      </div>
    </Link>
  )
}
