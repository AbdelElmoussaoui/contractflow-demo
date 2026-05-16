SYSTEM = """Tu es un juriste d'entreprise et un expert en gestion des risques contractuels.
Tu analyses des contrats pour les classifier et proposer un circuit de validation adapté.
Sois précis dans ta justification et exhaustif dans la détection des clauses sensibles."""

TOOL: dict = {
    "name": "classify_contract",
    "description": "Classifie le contrat, détecte les clauses sensibles et propose un circuit de signature.",
    "input_schema": {
        "type": "object",
        "properties": {
            "contract_type": {
                "type": "string",
                "enum": ["commercial", "rh", "prestation", "autre"],
                "description": "Type de contrat",
            },
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Niveau de risque global",
            },
            "classification_justification": {
                "type": "string",
                "description": "Justification détaillée de la classification et du niveau de risque",
            },
            "sensitive_clauses": {
                "type": "array",
                "description": "Clauses identifiées comme sensibles ou à risque",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Type de clause (ex: reconduction_tacite, exclusivité, pénalité)"},
                        "description": {"type": "string"},
                        "excerpt": {"type": "string", "description": "Extrait verbatim du contrat"},
                        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    },
                    "required": ["type", "description", "risk_level"],
                },
            },
            "proposed_workflow": {
                "type": "object",
                "description": "Circuit de signature proposé en fonction du type et du risque",
                "properties": {
                    "signers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Nom ou rôle du signataire"},
                                "email": {"type": "string", "description": "Email du signataire (placeholder si inconnu)"},
                                "order": {"type": "integer", "description": "Ordre de signature (1 = premier)"},
                            },
                            "required": ["name", "email", "order"],
                        },
                    },
                    "justification": {"type": "string", "description": "Pourquoi ce circuit de validation"},
                },
                "required": ["signers", "justification"],
            },
        },
        "required": [
            "contract_type",
            "risk_level",
            "classification_justification",
            "sensitive_clauses",
            "proposed_workflow",
        ],
    },
}


def user_prompt(pdf_text: str, metadata: dict) -> str:
    import json
    return (
        f"Voici un contrat à analyser.\n\n"
        f"Métadonnées extraites :\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n\n"
        f"Texte du contrat :\n{pdf_text[:3000]}\n\n"
        "Classe ce contrat, identifie les clauses sensibles et propose un circuit de validation adapté."
    )
