"""RSA-based XML-DSig / XAdES-like signature generation for the mock service.

The key pair is generated once at module import and kept in memory for the
lifetime of the process. In a production signing service you would use a real
HSM-backed certificate; here we just need something the agent verifier can
parse and check.
"""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# One demo CA key for all mock signatures
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()


def _rsa_sign(data: bytes) -> str:
    """Return base64-encoded RSA-SHA256 signature."""
    sig = _PRIVATE_KEY.sign(data, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode()


def generate_signature_xml(
    document_hash_hex: str,
    signer_name: str,
    signer_email: str,
    signed_at: datetime | None = None,
) -> str:
    """
    Build a simplified XAdES-compatible XML-DSig document.

    Structure compatible with the agent's verify_signatures node:
      - ds:DigestValue  → base64(sha256(document_bytes))
      - ds:SignatureValue → RSA-SHA256 signature over (digest + email + time)
      - xades:IssuerSerial/ds:X509IssuerName → signer identity
    """
    ts = (signed_at or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # DigestValue: base64 of the raw SHA-256 bytes (same as what verifier computes)
    doc_hash_bytes = bytes.fromhex(document_hash_hex)
    digest_value = base64.b64encode(doc_hash_bytes).decode()

    # Signature over meaningful data
    signed_data = f"{digest_value}|{signer_email}|{ts}".encode()
    signature_value = _rsa_sign(signed_data)

    issuer_name = f"CN={signer_name}, E={signer_email}, O=ContractFlow Demo Mock"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
              xmlns:xades="http://uri.etsi.org/01903/v1.3.2#">
  <ds:SignedInfo>
    <ds:CanonicalizationMethod
        Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
    <ds:SignatureMethod
        Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
    <ds:Reference>
      <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
      <ds:DigestValue>{digest_value}</ds:DigestValue>
    </ds:Reference>
  </ds:SignedInfo>
  <ds:SignatureValue>{signature_value}</ds:SignatureValue>
  <ds:KeyInfo>
    <ds:X509Data>
      <xades:IssuerSerial>
        <ds:X509IssuerName>{issuer_name}</ds:X509IssuerName>
        <ds:X509SerialNumber>1</ds:X509SerialNumber>
      </xades:IssuerSerial>
    </ds:X509Data>
  </ds:KeyInfo>
  <ds:Object>
    <xades:QualifyingProperties>
      <xades:SignedProperties>
        <xades:SignedSignatureProperties>
          <xades:SigningTime>{ts}</xades:SigningTime>
          <xades:SignerRole>
            <xades:ClaimedRoles>
              <xades:ClaimedRole>{signer_name}</xades:ClaimedRole>
            </xades:ClaimedRoles>
          </xades:SignerRole>
        </xades:SignedSignatureProperties>
      </xades:SignedProperties>
    </xades:QualifyingProperties>
  </ds:Object>
</ds:Signature>"""
