import {
  FileText, Search, Tag, UserCheck, Mail,
  PenLine, ShieldCheck, Archive, Clock, Zap,
} from 'lucide-react'
import { cn, STEP_LABEL, formatDuration } from '../lib/utils'
import { StepBadge } from './ui/Badge'
import { Spinner } from './ui/Spinner'
import type { AgentStep, StepStatus } from '../lib/types'

const STEP_ICON: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  load_pdf: FileText,
  extract_metadata: Search,
  classify: Tag,
  human_review: UserCheck,
  create_envelope: Mail,
  wait_signatures: PenLine,
  verify_signatures: ShieldCheck,
  archive: Archive,
}

const NODE_STYLE: Record<StepStatus, string> = {
  pending: 'bg-slate-100 text-slate-400 border-slate-200',
  running: 'bg-blue-100 text-blue-600 border-blue-300 animate-pulse-soft',
  waiting: 'bg-amber-100 text-amber-600 border-amber-300 animate-pulse-soft',
  done: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  failed: 'bg-red-100 text-red-600 border-red-300',
}

const LINE_STYLE: Record<StepStatus, string> = {
  pending: 'bg-slate-200',
  running: 'bg-blue-300',
  waiting: 'bg-amber-300',
  done: 'bg-emerald-300',
  failed: 'bg-red-300',
}

interface Props {
  steps: AgentStep[]
}

export function AgentTimeline({ steps }: Props) {
  if (steps.length === 0) {
    return (
      <div className="flex items-center gap-3 py-6 text-slate-400 text-sm">
        <Spinner className="w-4 h-4 text-indigo-400" />
        L'agent démarre…
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {steps.map((step, i) => {
        const Icon = STEP_ICON[step.step_name] ?? FileText
        const isLast = i === steps.length - 1
        const tokens = (step.tokens_input ?? 0) + (step.tokens_output ?? 0)

        return (
          <div key={step.id} className="flex gap-4">
            {/* Left: icon + line */}
            <div className="flex flex-col items-center">
              <div className={cn(
                'w-9 h-9 rounded-xl border-2 flex items-center justify-center shrink-0 z-10',
                NODE_STYLE[step.status],
              )}>
                {step.status === 'running' ? (
                  <Spinner className="w-4 h-4" />
                ) : (
                  <Icon size={16} />
                )}
              </div>
              {!isLast && (
                <div className={cn('w-0.5 flex-1 my-1 min-h-[20px]', LINE_STYLE[step.status])} />
              )}
            </div>

            {/* Right: content */}
            <div className={cn('pb-5 flex-1 min-w-0', isLast && 'pb-0')}>
              <div className="flex items-start justify-between gap-2 mt-1.5">
                <p className="text-sm font-medium text-slate-800 leading-tight">
                  {STEP_LABEL[step.step_name] ?? step.step_name}
                </p>
                <StepBadge status={step.status} />
              </div>

              {/* Metrics */}
              <div className="flex flex-wrap gap-3 mt-1.5">
                {step.duration_ms != null && (
                  <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                    <Clock size={11} />
                    {formatDuration(step.duration_ms)}
                  </span>
                )}
                {tokens > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                    <Zap size={11} />
                    {tokens.toLocaleString('fr-FR')} tokens
                  </span>
                )}
              </div>

              {/* Error */}
              {step.error_message && (
                <p className="mt-1.5 text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
                  {step.error_message}
                </p>
              )}

              {/* Output summary */}
              {step.status === 'done' && step.output_data && Object.keys(step.output_data).length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {Object.entries(step.output_data).map(([k, v]) => (
                    <span key={k} className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-md">
                      {k}: <strong className="text-slate-700">{String(v)}</strong>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
