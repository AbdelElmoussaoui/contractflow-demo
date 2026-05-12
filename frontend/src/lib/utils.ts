import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow } from 'date-fns'
import { fr } from 'date-fns/locale'
import type { ContractStatus, RiskLevel } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return format(new Date(iso), 'dd MMM yyyy', { locale: fr })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return format(new Date(iso), "dd MMM yyyy 'à' HH:mm", { locale: fr })
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: fr })
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} s`
}

export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}

export function formatAmount(amount: number | null, currency?: string | null): string {
  if (amount == null) return '—'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: currency || 'EUR',
  }).format(amount)
}

export const STATUS_LABEL: Record<ContractStatus, string> = {
  uploaded: 'Uploadé',
  processing: 'En traitement',
  awaiting_approval: "En attente d'approbation",
  awaiting_signatures: 'En attente de signatures',
  verifying: 'Vérification',
  archived: 'Archivé',
  failed: 'Erreur',
}

export const RISK_LABEL: Record<RiskLevel, string> = {
  low: 'Faible',
  medium: 'Moyen',
  high: 'Élevé',
}

export const CONTRACT_TYPE_LABEL: Record<string, string> = {
  commercial: 'Commercial',
  rh: 'Ressources Humaines',
  prestation: 'Prestation de services',
  autre: 'Autre',
}

export const STEP_LABEL: Record<string, string> = {
  load_pdf: 'Chargement du document',
  extract_metadata: 'Extraction des métadonnées',
  classify: 'Classification & analyse des risques',
  human_review: 'Validation humaine',
  create_envelope: 'Envoi pour signature',
  wait_signatures: 'Attente des signatures',
  verify_signatures: 'Vérification des signatures',
  archive: 'Archivage sécurisé',
}

export const ACTIVE_STATUSES: ContractStatus[] = [
  'processing',
  'awaiting_approval',
  'awaiting_signatures',
  'verifying',
]

export function isActiveStatus(s: ContractStatus): boolean {
  return ACTIVE_STATUSES.includes(s)
}
