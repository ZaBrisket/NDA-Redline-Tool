"""
Edgewater NDA Checklist Rules - Full descriptions for UI display
Maps clause types to user-friendly explanations
"""

CHECKLIST_RULES = {
    "confidentiality_term": {
        "title": "Confidentiality Term Limit",
        "severity": "critical",
        "requirement": "18-24 months maximum",
        "description": "Edgewater never accepts perpetual or indefinite confidentiality terms. All NDAs must expire within 18-24 months from the agreement date.",
        "why": "Perpetual confidentiality creates unlimited liability and restricts future business opportunities.",
        "standard_language": "This Agreement shall expire eighteen (18) months from the date hereof."
    },

    "governing_law": {
        "title": "Governing Law",
        "severity": "moderate",
        "requirement": "State of Delaware",
        "description": "All NDAs should be governed by Delaware law for consistency and favorable legal precedents.",
        "why": "Delaware has well-established business law and provides predictable legal outcomes.",
        "standard_language": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware."
    },

    "document_retention": {
        "title": "Document Retention Carveout",
        "severity": "critical",
        "requirement": "Legal, regulatory, and archival exceptions",
        "description": "Always include exceptions allowing retention of confidential information for legal, regulatory, and archival purposes.",
        "why": "Companies must retain documents for compliance, legal proceedings, and regulatory requirements.",
        "standard_language": "Notwithstanding the foregoing, Recipient may retain copies of Confidential Information as necessary for legal, regulatory, or archival purposes, or as required by regulation or legal process, provided such retained information remains subject to the confidentiality obligations herein."
    },

    "employee_solicitation": {
        "title": "Non-Solicitation Carveouts",
        "severity": "critical",
        "requirement": "4 standard exceptions",
        "description": "Non-solicitation clauses must include four standard exceptions to avoid overly restrictive hiring limitations.",
        "why": "Absolute non-solicits can prevent normal recruiting and hiring practices.",
        "standard_language": """Nothing herein shall prevent Recipient from hiring such persons who:
(i) respond to general advertisements or recruiting efforts not specifically directed at Disclosing Party's employees;
(ii) initiate discussions with Recipient without any direct or indirect solicitation;
(iii) had prior employment discussions with Recipient before receiving Confidential Information; or
(iv) were terminated by the Disclosing Party prior to commencement of discussions with Recipient."""
    },

    "competition_clause": {
        "title": "Competition Safe Harbor",
        "severity": "critical",
        "requirement": "Business freedom disclaimer",
        "description": "Add language clarifying that receiving confidential information does not prevent normal business operations or competition.",
        "why": "Protects Edgewater's ability to invest in or acquire similar/competitive businesses.",
        "standard_language": "Recipient's receipt and use of Confidential Information will not, in and of itself, prevent or restrict Recipient in any way from carrying on its business in the ordinary course, including without limitation, making investments in, acquisitions of, or competing with businesses similar to or competitive with Disclosing Party."
    },

    "affiliate_clause": {
        "title": "Remove Affiliate References",
        "severity": "moderate",
        "requirement": "Limit to named parties",
        "description": "Delete references to 'affiliates', 'subsidiaries', or 'related entities' to limit scope of obligations.",
        "why": "Affiliate language extends obligations to unlimited third parties we don't control.",
        "standard_language": "N/A - Delete affiliate references"
    },

    "legal_modifier": {
        "title": "Legal Modifiers",
        "severity": "moderate",
        "requirement": "Use 'commercially reasonable'",
        "description": "Replace 'best efforts' with 'commercially reasonable efforts' and moderate other absolute language.",
        "why": "'Best efforts' creates an unreasonably high standard; 'commercially reasonable' is more balanced.",
        "standard_language": "commercially reasonable efforts"
    },

    "indemnification": {
        "title": "Remove Indemnification",
        "severity": "high",
        "requirement": "No indemnity clauses",
        "description": "Delete any indemnification or hold harmless provisions related to NDA breaches.",
        "why": "Edgewater does not indemnify for NDA violations; standard confidentiality obligations are sufficient.",
        "standard_language": "N/A - Delete indemnification clauses"
    },

    "injunctive_relief": {
        "title": "Injunctive Relief Limitation",
        "severity": "moderate",
        "requirement": "Require court determination",
        "description": "Add requirement that injunctive relief requires a final binding determination by a court.",
        "why": "Prevents automatic injunctions without judicial review.",
        "standard_language": "upon a final binding determination of a court of competent jurisdiction"
    },

    "broker_clause": {
        "title": "Remove Broker Language",
        "severity": "high",
        "requirement": "Delete broker/commission terms",
        "description": "Remove any references to brokers, commissions, or transaction fees.",
        "why": "Broker and commission language is not relevant to confidentiality agreements.",
        "standard_language": "N/A - Delete broker clauses"
    },

    "representations": {
        "title": "Remove Representations",
        "severity": "moderate",
        "requirement": "No accuracy/ownership warranties",
        "description": "Delete representations and warranties about information accuracy, completeness, or ownership.",
        "why": "Information is provided 'as-is' without warranties; representations create unnecessary liability.",
        "standard_language": "N/A - Delete representation clauses"
    },

    "assignment": {
        "title": "Assignment Rights",
        "severity": "moderate",
        "requirement": "Allow M&A assignments",
        "description": "Modify assignment restrictions to allow transfers in connection with mergers, acquisitions, or asset sales.",
        "why": "Enables flexibility during corporate transactions without requiring counterparty consent.",
        "standard_language": "This Agreement may be assigned to affiliates or in connection with a merger, acquisition, or sale of all or substantially all assets."
    },

    "jurisdiction": {
        "title": "Remove Venue Restrictions",
        "severity": "moderate",
        "requirement": "No specific venue requirements",
        "description": "Delete clauses specifying exclusive jurisdiction or venue in particular courts.",
        "why": "Venue restrictions limit flexibility and may create inconvenient forum requirements.",
        "standard_language": "N/A - Delete jurisdiction clauses"
    },

    "remedies": {
        "title": "Remedies",
        "severity": "moderate",
        "requirement": "Balance remedies language",
        "description": "Ensure remedies provisions are balanced and require appropriate judicial process.",
        "why": "Prevents one-sided remedy provisions that favor the disclosing party.",
        "standard_language": "Varies based on specific clause"
    }
}


def get_rule_explanation(clause_type: str) -> dict:
    """Get the full rule explanation for a clause type"""
    return CHECKLIST_RULES.get(clause_type, {
        "title": clause_type.replace("_", " ").title(),
        "severity": "moderate",
        "requirement": "Standard terms",
        "description": "This clause requires modification per Edgewater standards.",
        "why": "Protects Edgewater's interests and ensures fair terms.",
        "standard_language": "Varies"
    })


def get_all_rules():
    """Get all checklist rules"""
    return CHECKLIST_RULES
