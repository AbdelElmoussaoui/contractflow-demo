"""Node 1 — download PDF from MinIO and extract text.

Les appels MinIO et PyMuPDF sont synchrones et bloquants.
On les exécute via run_in_executor pour ne pas geler l'event loop asyncio,
ce qui permettrait aux autres coroutines (DB, healthcheck) de continuer.
"""
import asyncio
import time

import fitz  # PyMuPDF
import structlog

from app.schemas.state import ContractState
from app.services import db as db_svc
from app.services.storage import download_file

logger = structlog.get_logger()


def _extract_text(pdf_bytes: bytes) -> tuple[list[str], int]:
    """Extraction de texte PyMuPDF — exécutée dans un thread séparé."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [page.get_text() for page in doc]
    n = len(pages)
    doc.close()
    return pages, n


def _download(bucket: str, key: str) -> bytes:
    """Téléchargement MinIO — exécuté dans un thread séparé."""
    return download_file(bucket, key)


async def load_pdf(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "load_pdf")
    t0 = time.monotonic()

    try:
        await db_svc.update_contract_status(contract_id, "processing")

        info = await db_svc.get_contract_minio_info(contract_id)
        if not info:
            raise ValueError(f"Contrat {contract_id} introuvable en base")
        bucket, key = info

        # Téléchargement non-bloquant
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(None, _download, bucket, key)

        # Extraction de texte non-bloquante
        pages, n_pages = await loop.run_in_executor(None, _extract_text, pdf_bytes)
        pdf_text = "\n\n".join(pages).strip()

        # Fallback pour documents scannés (images uniquement, pas de texte)
        if not pdf_text:
            filename = key.split("/")[-1]
            pdf_text = (
                f"[Document scanné — extraction de texte impossible. "
                f"Fichier : {filename}, {n_pages} page(s). "
                f"Analyse basée sur le nom du fichier uniquement.]"
            )
            logger.warning("pdf_no_text", contract_id=contract_id, filename=filename)

        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id,
            output_data={"pages": n_pages, "chars": len(pdf_text)},
            duration_ms=dur,
        )
        logger.info("pdf_loaded", contract_id=contract_id, pages=n_pages, chars=len(pdf_text))
        return {"pdf_text": pdf_text, "minio_key": key, "minio_bucket": bucket}

    except Exception as exc:
        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id, status="failed", error_message=str(exc), duration_ms=dur
        )
        await db_svc.update_contract_status(contract_id, "failed")
        logger.error("pdf_load_failed", contract_id=contract_id, error=str(exc))
        raise
