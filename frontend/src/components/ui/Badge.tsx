import { cn } from '../../lib/utils'
import type { ContractStatus, RiskLevel, StepStatus } from '../../lib/types'
import { STATUS_LABEL, RISK_LABEL } from '../../lib/utils'

// ── Status badge ──────────────────────────────────────────────────────────────

const statusStyles: Record<ContractStatus, string> = {
  uploaded: 'bg-slate-100 text-slate-600',
  processing: 'bg-blue-100 text-blue-700 animate-pulse-soft',
  awaiting_approval: 'bg-amber-100 text-amber-700 animate-pulse-soft',
  awaiting_signatures: 'bg-violet-100 text-violet-700 animate-pulse-soft',
  verifying: 'bg-sky-100 text-sky-700 animate-pulse-soft',
  archived: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
}

const statusDot: Record<ContractStatus, string> = {
  uploaded: 'bg-slate-400',
  processing: 'bg-blue-500',
  awaiting_approval: 'bg-amber-500',
  awaiting_signatures: 'bg-violet-500',
  verifying: 'bg-sky-500',
  archived: 'bg-emerald-500',
  failed: 'bg-red-500',
}

export function StatusBadge({ status }: { status: ContractStatus }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold', statusStyles[status])}>
      <span className={cn('w-1.5 h-1.5 rounded-full', statusDot[status])} />
      {STATUS_LABEL[status]}
    </span>
  )
}

// ── Risk badge ────────────────────────────────────────────────────────────────

const riskStyles: Record<RiskLevel, string> = {
  low: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  high: 'bg-red-100 text-red-700 border-red-200',
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border', riskStyles[level])}>
      {RISK_LABEL[level]}
    </span>
  )
}

// ── Step status badge ─────────────────────────────────────────────────────────

const stepStyles: Record<StepStatus, string> = {
  pending: 'bg-slate-100 text-slate-500',
  running: 'bg-blue-100 text-blue-600',
  waiting: 'bg-amber-100 text-amber-600',
  done: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-600',
}

const stepLabel: Record<StepStatus, string> = {
  pending: 'En attente',
  running: 'En cours',
  waiting: 'Suspendu',
  done: 'Terminé',
  failed: 'Échec',
}

export function StepBadge({ status }: { status: StepStatus }) {
  return (
    <span className={cn('px-2 py-0.5 rounded-md text-xs font-medium', stepStyles[status])}>
      {stepLabel[status]}
    </span>
  )
}
