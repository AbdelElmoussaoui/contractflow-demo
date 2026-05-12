import { CheckCircle2, Clock, ExternalLink, ShieldCheck, ShieldX, User } from 'lucide-react'
import { cn, formatDateTime } from '../lib/utils'
import type { Signature } from '../lib/types'

interface Props { signatures: Signature[] }

const signerStatusConfig = {
  pending: { label: 'En attente', icon: Clock, cls: 'text-slate-400', bg: 'bg-slate-100' },
  sent: { label: 'Envoyé', icon: Clock, cls: 'text-amber-500', bg: 'bg-amber-100' },
  signed: { label: 'Signé', icon: CheckCircle2, cls: 'text-emerald-600', bg: 'bg-emerald-100' },
  verified: { label: 'Vérifié ✓', icon: ShieldCheck, cls: 'text-emerald-700', bg: 'bg-emerald-100' },
  failed: { label: 'Échec', icon: ShieldX, cls: 'text-red-600', bg: 'bg-red-100' },
} as const

function initials(name: string) {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function avatarColor(i: number) {
  const colors = [
    'from-indigo-400 to-violet-500',
    'from-sky-400 to-blue-500',
    'from-emerald-400 to-teal-500',
    'from-amber-400 to-orange-500',
  ]
  return colors[i % colors.length]
}

export function SignaturesPanel({ signatures }: Props) {
  if (signatures.length === 0) {
    return (
      <div className="text-center py-6 text-slate-400 text-sm">
        Aucun signataire configuré
      </div>
    )
  }

  const signed = signatures.filter(s => ['signed', 'verified'].includes(s.status)).length

  return (
    <div className="space-y-3">
      {/* Progress */}
      <div>
        <div className="flex items-center justify-between mb-1.5 text-xs text-slate-500">
          <span>{signed} / {signatures.length} signatures</span>
          <span>{Math.round((signed / signatures.length) * 100)}%</span>
        </div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 rounded-full transition-all duration-700"
            style={{ width: `${(signed / signatures.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Signers */}
      {signatures.map((sig, i) => {
        const cfg = signerStatusConfig[sig.status as keyof typeof signerStatusConfig] ??
          signerStatusConfig.pending
        const Icon = cfg.icon

        return (
          <div key={sig.id} className="flex items-start gap-3 p-3 rounded-xl border border-slate-100 bg-white">
            {/* Avatar */}
            <div className={cn(
              'w-9 h-9 rounded-xl bg-gradient-to-br flex items-center justify-center shrink-0 text-white text-xs font-bold',
              avatarColor(i),
            )}>
              {initials(sig.signer_name)}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-slate-800 truncate">{sig.signer_name}</p>
                  <p className="text-xs text-slate-400 truncate">{sig.signer_email}</p>
                </div>
                <div className={cn('flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium', cfg.bg)}>
                  <Icon size={12} className={cfg.cls} />
                  <span className={cfg.cls}>{cfg.label}</span>
                </div>
              </div>

              {sig.signed_at && (
                <p className="mt-1 text-xs text-slate-400">
                  Signé le {formatDateTime(sig.signed_at)}
                </p>
              )}
              {sig.signing_url && sig.status === 'sent' && (
                <a
                  href={sig.signing_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 mt-1 text-xs text-indigo-600 hover:underline"
                >
                  <ExternalLink size={11} />
                  Lien de signature
                </a>
              )}
              {sig.verification_valid === false && (
                <p className="mt-1 text-xs text-red-600">Vérification échouée</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
