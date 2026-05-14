import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ContractDetail } from '../lib/types'

const TERMINAL = new Set(['archived', 'failed'])

export function useContractSSE(contractId: string | undefined) {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!contractId) return

    const es = new EventSource(api.contracts.eventsUrl(contractId))

    es.onmessage = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as ContractDetail
        queryClient.setQueryData(['contract', contractId], data)
        if (TERMINAL.has(data.status)) es.close()
      } catch (err) {
        console.warn('[SSE] Failed to parse event:', err)
      }
    }

    es.onerror = (err) => {
      console.warn('[SSE] Connection error, closing:', err)
      es.close()
    }

    return () => es.close()
  }, [contractId, queryClient])
}
