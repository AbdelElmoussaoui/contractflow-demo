SYSTEM = """Tu es un expert juridique spécialisé dans l'analyse de contrats.
Ta mission est d'extraire avec précision les informations structurées d'un document contractuel.
Si une information n'est pas présente dans le document, ne l'invente pas — omets le champ ou retourne null."""

TOOL: dict = {
    "name": "extract_contract_metadata",
    "description": "Extrait les métadonnées structurées d'un contrat.",
    "input_schema": {
        "type": "object",
        "properties": {
            "parties": {
                "type": "array",
                "description": "Parties identifiées dans le contrat.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Raison sociale ou nom complet"},
                        "role": {"type": "string", "description": "Rôle dans le contrat (ex: prestataire, client, bailleur)"},
                        "address": {"type": "string"},
                    },
                    "required": ["name", "role"],
                },
            },
            "amount": {"type": "number", "description": "Montant principal du contrat (null si non précisé)"},
            "currency": {"type": "string", "description": "Code devise ISO 4217 (EUR par défaut)", "default": "EUR"},
            "start_date": {"type": "string", "description": "Date de début au format YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "Date de fin au format YYYY-MM-DD"},
            "duration_months": {"type": "integer", "description": "Durée en mois si explicitement mentionnée"},
            "jurisdiction": {"type": "string", "description": "Tribunal ou droit applicable"},
            "payment_terms": {"type": "string", "description": "Conditions de paiement (délai, modalités)"},
        },
        "required": ["parties"],
    },
}


def user_prompt(pdf_text: str) -> str:
    return f"Analyse ce contrat et extrait les métadonnées demandées :\n\n{pdf_text[:12000]}"
