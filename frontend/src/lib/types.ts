export type ContractStatus =
  | 'uploaded'
  | 'processing'
  | 'awaiting_approval'
  | 'awaiting_signatures'
  | 'verifying'
  | 'archived'
  | 'failed'

export type RiskLevel = 'low' | 'medium' | 'high'
export type StepStatus = 'pending' | 'running' | 'waiting' | 'done' | 'failed'

export interface Party {
  name: string
  role: string
  address?: string
}

export interface SensitiveClause {
  type: string
  description: string
  excerpt?: string
  risk_level: RiskLevel
}

export interface WorkflowSigner {
  name: string
  email: string
  order: number
}

export interface Workflow {
  signers: WorkflowSigner[]
  justification?: string
}

export interface ContractMetadata {
  id: string
  parties: Party[] | null
  amount: number | null
  currency: string | null
  start_date: string | null
  end_date: string | null
  duration_months: number | null
  jurisdiction: string | null
  payment_terms: string | null
  contract_type: string | null
  risk_level: RiskLevel | null
  classification_justification: string | null
  sensitive_clauses: SensitiveClause[] | null
  proposed_workflow: Workflow | null
  approved_workflow: Workflow | null
}

export interface AgentStep {
  id: string
  step_name: string
  status: StepStatus
  output_data: Record<string, unknown> | null
  error_message: string | null
  tokens_input: number | null
  tokens_output: number | null
  duration_ms: number | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface Signature {
  id: string
  signer_name: string
  signer_email: string
  signing_order: number
  status: string
  signing_url: string | null
  signed_at: string | null
  verification_valid: boolean | null
}

export interface Archive {
  id: string
  document_hash: string
  seal_hash: string
  archive_timestamp: string
  receipt_data: Record<string, unknown>
}

export interface Contract {
  id: string
  original_name: string
  status: ContractStatus
  file_size_bytes: number | null
  created_at: string
  updated_at: string
}

export interface ContractDetail extends Contract {
  metadata: ContractMetadata | null
  steps: AgentStep[]
  signatures: Signature[]
  archive: Archive | null
}
