import { useState } from 'react'
import { Plus, Trash2, GripVertical, Sparkles, CheckCircle2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from './ui/Modal'
import { Spinner } from './ui/Spinner'
import { api } from '../lib/api'
import type { ContractDetail, WorkflowSigner } from '../lib/types'

interface Props {
  open: boolean
  onClose: () => void
  contract: ContractDetail
}

export function ApprovalModal({ open, onClose, contract }: Props) {
  const proposed = contract.metadata?.proposed_workflow
  const justification = proposed?.justification

  const [signers, setSigners] = useState<WorkflowSigner[]>(() =>
    proposed?.signers?.map(s => ({ ...s })) ?? []
  )
  const [success, setSuccess] = useState(false)

  const queryClient = useQueryClient()
  const approve = useMutation({
    mutationFn: () => api.contracts.approve(contract.id, signers),
    onSuccess: (data) => {
      queryClient.setQueryData(['contract', contract.id], data)
      setSuccess(true)
      setTimeout(onClose, 1500)
    },
  })

  function updateSigner(i: number, field: keyof WorkflowSigner, value: string | number) {
    setSigners(prev => prev.map((s, idx) => idx === i ? { ...s, [field]: value } : s))
  }

  function addSigner() {
    setSigners(prev => [...prev, { name: '', email: '', order: prev.length + 1 }])
  }

  function removeSigner(i: number) {
    setSigners(prev => prev.filter((_, idx) => idx !== i).map((s, idx) => ({ ...s, order: idx + 1 })))
  }

  const valid = signers.length > 0 &&
    signers.every(s => s.name.trim() && s.email.includes('@'))

  return (
    <Modal open={open} onClose={onClose} title="Valider le circuit de signature" size="lg">
      <div className="p-6 space-y-6">
        {success ? (
          <div className="flex flex-col items-center gap-3 py-8 text-emerald-600">
            <CheckCircle2 size={48} className="text-emerald-500" />
            <p className="font-semibold text-lg">Circuit validé !</p>
            <p className="text-sm text-slate-500">L'agent reprend le traitement…</p>
          </div>
        ) : (
          <>
            {/* AI justification */}
            {justification && (
              <div className="flex gap-3 p-4 rounded-xl bg-indigo-50 border border-indigo-100">
                <Sparkles size={18} className="text-indigo-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-semibold text-indigo-700 mb-1">Recommandation de l'IA</p>
                  <p className="text-sm text-indigo-900 leading-relaxed">{justification}</p>
                </div>
              </div>
            )}

            {/* Signer list */}
            <div>
              <p className="text-sm font-semibold text-slate-700 mb-3">
                Signataires ({signers.length})
              </p>
              <div className="space-y-2">
                {signers.map((s, i) => (
                  <div key={i} className="flex items-center gap-2 p-3 rounded-xl border border-slate-200 bg-slate-50
                                          hover:border-indigo-200 hover:bg-white transition-colors">
                    {/* Order */}
                    <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center
                                    text-white text-xs font-bold shrink-0">
                      {s.order}
                    </div>
                    {/* Fields */}
                    <input
                      className="input flex-1 min-w-0 text-sm"
                      placeholder="Nom ou rôle"
                      value={s.name}
                      onChange={e => updateSigner(i, 'name', e.target.value)}
                    />
                    <input
                      className="input flex-1 min-w-0 text-sm"
                      placeholder="email@example.com"
                      type="email"
                      value={s.email}
                      onChange={e => updateSigner(i, 'email', e.target.value)}
                    />
                    <button
                      onClick={() => removeSigner(i)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors shrink-0"
                      title="Supprimer"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>

              <button
                onClick={addSigner}
                className="mt-2 flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800
                           font-medium px-3 py-2 rounded-xl hover:bg-indigo-50 transition-colors w-full justify-center border border-dashed border-indigo-200"
              >
                <Plus size={15} />
                Ajouter un signataire
              </button>
            </div>

            {/* Signing order info */}
            {signers.length > 1 && (
              <p className="text-xs text-slate-400 text-center">
                Les signatures seront collectées dans l'ordre indiqué (1 → {signers.length})
              </p>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2 border-t border-slate-100">
              <button onClick={onClose} className="btn-secondary flex-1" disabled={approve.isPending}>
                Annuler
              </button>
              <button
                onClick={() => approve.mutate()}
                disabled={!valid || approve.isPending}
                className="btn-primary flex-1 justify-center"
              >
                {approve.isPending ? (
                  <><Spinner className="w-4 h-4" /> Validation…</>
                ) : (
                  <><CheckCircle2 size={16} /> Approuver le circuit</>
                )}
              </button>
            </div>

            {approve.error && (
              <p className="text-xs text-red-600 text-center">
                Erreur : {(approve.error as Error).message}
              </p>
            )}
          </>
        )}
      </div>
    </Modal>
  )
}
