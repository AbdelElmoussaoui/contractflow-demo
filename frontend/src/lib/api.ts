import type { Contract, ContractDetail, WorkflowSigner } from './types'

const BASE = (import.meta.env.VITE_API_URL as string) || ''

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  contracts: {
    list: () => req<Contract[]>('/contracts'),
    get: (id: string) => req<ContractDetail>(`/contracts/${id}`),
    upload: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return req<Contract>('/contracts', { method: 'POST', body: form })
    },
    delete: (id: string) => req<void>(`/contracts/${id}`, { method: 'DELETE' }),
    approve: (id: string, signers: WorkflowSigner[]) =>
      req<ContractDetail>(`/contracts/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_workflow: signers }),
      }),
    eventsUrl: (id: string) => `${BASE}/contracts/${id}/events`,
  },
}
