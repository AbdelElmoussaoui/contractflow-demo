"""Node 1 — download PDF from MinIO and extract text."""
import time

import fitz  # PyMuPDF
import structlog

from app.schemas.state import ContractState
from app.services import db as db_svc
from app.services.storage import download_file

logger = structlog.get_logger()


async def load_pdf(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "load_pdf")
    t0 = time.monotonic()

    try:
        await db_svc.update_contract_status(contract_id, "processing")

        info = await db_svc.get_contract_minio_info(contract_id)
        if not info:
            raise ValueError(f"Contract {contract_id} not found in DB")
        bucket, key = info

        pdf_bytes = download_file(bucket, key)

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        doc.close()
        pdf_text = "\n\n".join(pages).strip()

        if not pdf_text:
            raise ValueError("PDF text extraction returned empty content")

        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id,
            output_data={"pages": len(pages), "chars": len(pdf_text)},
            duration_ms=dur,
        )
        logger.info("pdf_loaded", contract_id=contract_id, pages=len(pages), chars=len(pdf_text))
        return {"pdf_text": pdf_text, "minio_key": key, "minio_bucket": bucket}

    except Exception as exc:
        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(step_id, status="failed", error_message=str(exc), duration_ms=dur)
        await db_svc.update_contract_status(contract_id, "failed")
        logger.error("pdf_load_failed", contract_id=contract_id, error=str(exc))
        raise
