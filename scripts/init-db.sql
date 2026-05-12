-- ============================================================
-- ContractFlow Demo — Schéma PostgreSQL initial
-- Exécuté automatiquement au premier démarrage du container
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- pour gen_random_uuid()

-- ──────────────────────────────────────────────────────────────
-- Table principale des contrats
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contracts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename      VARCHAR(255) NOT NULL,           -- nom stocké dans MinIO
    original_name VARCHAR(255) NOT NULL,           -- nom original uploadé
    minio_bucket  VARCHAR(100) NOT NULL DEFAULT 'contracts',
    minio_key     VARCHAR(500) NOT NULL,           -- chemin dans le bucket
    status        VARCHAR(50)  NOT NULL DEFAULT 'uploaded',
    -- Valeurs possibles :
    -- uploaded → processing → awaiting_approval → awaiting_signatures
    -- → verifying → archived | failed
    file_size_bytes BIGINT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);

-- ──────────────────────────────────────────────────────────────
-- Métadonnées extraites par l'agent
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS contract_metadata (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    -- Parties identifiées (JSON array)
    parties         JSONB,
    -- Ex: [{"name": "Acme SAS", "role": "prestataire", "address": "..."}]
    amount          NUMERIC(15, 2),
    currency        VARCHAR(10) DEFAULT 'EUR',
    start_date      DATE,
    end_date        DATE,
    duration_months INTEGER,
    jurisdiction    VARCHAR(255),
    payment_terms   TEXT,
    -- Classification
    contract_type   VARCHAR(100),   -- commercial, rh, prestation, autre
    risk_level      VARCHAR(20),    -- low, medium, high
    classification_justification TEXT,
    -- Clauses sensibles détectées (JSON array)
    sensitive_clauses JSONB,
    -- Ex: [{"type": "reconduction_tacite", "description": "...", "excerpt": "...", "risk_level": "high"}]
    -- Circuit de signature proposé puis validé
    proposed_workflow JSONB,
    approved_workflow JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_contract_metadata_contract ON contract_metadata(contract_id);

-- ──────────────────────────────────────────────────────────────
-- Étapes de l'agent (pour la timeline et le SSE)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_steps (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id   UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    step_name     VARCHAR(100) NOT NULL,
    -- pending | running | done | failed | waiting (pour human-in-the-loop)
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending',
    input_data    JSONB,
    output_data   JSONB,
    error_message TEXT,
    tokens_input  INTEGER,
    tokens_output INTEGER,
    duration_ms   INTEGER,
    started_at    TIMESTAMPTZ,
    completed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_steps_contract ON agent_steps(contract_id);
CREATE INDEX IF NOT EXISTS idx_agent_steps_status   ON agent_steps(status);

-- ──────────────────────────────────────────────────────────────
-- Enveloppes de signature (côté mock DocuSign)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signing_envelopes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL,   -- référence non-FK car mock est un service séparé
    document_hash   VARCHAR(64) NOT NULL,  -- SHA-256 du PDF original
    filename        VARCHAR(255) NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- pending | partially_signed | completed
    callback_url    TEXT,            -- URL de callback vers l'agent
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS signing_envelope_signers (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    envelope_id   UUID NOT NULL REFERENCES signing_envelopes(id) ON DELETE CASCADE,
    signer_name   VARCHAR(255) NOT NULL,
    signer_email  VARCHAR(255) NOT NULL,
    signing_order INTEGER NOT NULL DEFAULT 1,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | signed
    signing_token VARCHAR(64) UNIQUE,  -- token URL pour le lien de signature
    signed_at     TIMESTAMPTZ,
    signature_xml TEXT,               -- XAdES signature XML (générée par signxml)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signers_envelope  ON signing_envelope_signers(envelope_id);
CREATE INDEX IF NOT EXISTS idx_signers_token     ON signing_envelope_signers(signing_token);

-- ──────────────────────────────────────────────────────────────
-- Signatures reçues et vérifiées (côté agent)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signatures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    envelope_id     VARCHAR(255),       -- ID de l'enveloppe dans le mock
    signer_name     VARCHAR(255) NOT NULL,
    signer_email    VARCHAR(255) NOT NULL,
    signing_order   INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending | sent | signed | verified | failed
    signing_url     TEXT,
    signed_at       TIMESTAMPTZ,
    signature_xml   TEXT,               -- XAdES signature XML complète
    -- Résultats de vérification
    verification_valid        BOOLEAN,
    verification_hash_match   BOOLEAN,
    verification_cert_subject VARCHAR(500),
    verification_error        TEXT,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signatures_contract ON signatures(contract_id);

-- ──────────────────────────────────────────────────────────────
-- Archives avec sceau chaîné (Merkle léger)
-- ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS archives (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id         UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    minio_bucket        VARCHAR(100) NOT NULL DEFAULT 'archives',
    minio_key           VARCHAR(500) NOT NULL,
    -- Hachage du document PDF signé final
    document_hash       VARCHAR(64) NOT NULL,
    -- Sceau précédent dans la chaîne (NULL pour le premier)
    previous_seal_hash  VARCHAR(64),
    -- Sceau = SHA-256(document_hash || previous_seal_hash || archive_timestamp)
    seal_hash           VARCHAR(64) NOT NULL,
    archive_timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Reçu complet au format JSON (exportable, partageable)
    receipt_data        JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_archives_contract ON archives(contract_id);

-- ──────────────────────────────────────────────────────────────
-- Trigger pour mettre à jour updated_at sur contracts
-- ──────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contracts_updated_at
    BEFORE UPDATE ON contracts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Note : les tables LangGraph (checkpoints, checkpoint_blobs, checkpoint_writes)
-- sont créées automatiquement par checkpointer.setup() au démarrage de l'agent.

-- Création de la database Langfuse (si le profil observability est activé)
-- Langfuse utilise la même instance Postgres avec une DB séparée.
-- Cette commande est ignorée si la DB existe déjà.
SELECT 'CREATE DATABASE langfuse' WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'langfuse'
)\gexec
