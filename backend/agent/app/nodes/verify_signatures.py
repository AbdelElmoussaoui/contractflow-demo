"""Node 7 — verify XAdES signatures and update DB."""
import hashlib
import time
import xml.etree.ElementTree as ET

import structlog

from app.schemas.state import ContractState
from app.services import db as db_svc
from app.services.storage import download_file

logger = structlog.get_logger()


def _verify_xades(signature_xml: str, document_bytes: bytes) -> tuple[bool, bool, str | None, str | None]:
    """
    Simplified XAdES verification:
    - Checks XML parseable
    - Checks presence of SignatureValue element
    - Checks embedded document hash against actual document hash

    Returns (valid, hash_match, cert_subject, error_message)
    """
    try:
        root = ET.fromstring(signature_xml)
        ns = {"ds": "http://www.w3.org/2000/09/xmldsig#", "xades": "http://uri.etsi.org/01903/v1.3.2#"}

        sig_value = root.find(".//ds:SignatureValue", ns) or root.find(".//SignatureValue")
        if sig_value is None:
            return False, False, None, "SignatureValue element missing"

        # Extract embedded digest if present
        digest_el = root.find(".//ds:DigestValue", ns) or root.find(".//DigestValue")
        hash_match = False
        if digest_el is not None and digest_el.text:
            import base64
            actual_hash = hashlib.sha256(document_bytes).digest()
            try:
                embedded_hash = base64.b64decode(digest_el.text.strip())
                hash_match = (actual_hash == embedded_hash)
            except Exception:
                hash_match = False

        # Extract cert subject if available
        cert_el = (
            root.find(".//xades:IssuerSerial/ds:X509IssuerName", ns)
            or root.find(".//X509IssuerName")
        )
        cert_subject = cert_el.text if cert_el is not None else "mock-cert-subject"

        return True, hash_match, cert_subject, None

    except ET.ParseError as exc:
        return False, False, None, f"XML parse error: {exc}"


async def verify_signatures(state: ContractState) -> dict:
    contract_id = state["contract_id"]
    step_id = await db_svc.create_agent_step(contract_id, "verify_signatures")
    t0 = time.monotonic()

    try:
        info = await db_svc.get_contract_minio_info(contract_id)
        if not info:
            raise ValueError("Contract not found")
        bucket, key = info
        document_bytes = download_file(bucket, key)

        sigs = state.get("signatures_data", [])
        verified_count = 0

        for sig in sigs:
            xml = sig.get("signature_xml", "")
            if not xml:
                await db_svc.update_signature_verified(
                    contract_id, sig["email"],
                    valid=False, hash_match=False, error="No signature XML received"
                )
                continue

            valid, hash_match, cert_subject, error = _verify_xades(xml, document_bytes)
            await db_svc.update_signature_verified(
                contract_id, sig["email"],
                valid=valid,
                hash_match=hash_match,
                cert_subject=cert_subject,
                error=error,
            )
            if valid:
                verified_count += 1

        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(
            step_id,
            output_data={"verified": verified_count, "total": len(sigs)},
            duration_ms=dur,
        )
        await db_svc.update_contract_status(contract_id, "verifying")
        logger.info("signatures_verified", contract_id=contract_id, verified=verified_count, total=len(sigs))
        return {}

    except Exception as exc:
        dur = int((time.monotonic() - t0) * 1000)
        await db_svc.complete_agent_step(step_id, status="failed", error_message=str(exc), duration_ms=dur)
        await db_svc.update_contract_status(contract_id, "failed")
        logger.error("verify_signatures_failed", contract_id=contract_id, error=str(exc))
        raise
