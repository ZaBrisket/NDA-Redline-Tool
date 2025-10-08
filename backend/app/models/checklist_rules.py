"""
Edgewater NDA Checklist Rules - Full descriptions for UI display
Maps clause types to user-friendly explanations
"""

CHECKLIST_RULES = {
    "confidentiality_term": {
        "title": "Confidentiality Term Limit",
        "severity": "moderate",  # Changed from critical - market standards are acceptable
        "requirement": "1-3 years (18-24 months ideal)",
        "must_have": False,  # Not required if existing term is reasonable
        "flexibility": {
            "unacceptable": "Perpetual, indefinite, or >5 years",
            "questionable": "5+ years",
            "acceptable": "12-36 months (1-3 years)",
            "ideal": "18-24 months"
        },
        "description": "Confidentiality terms should be reasonable. NEVER accept perpetual terms. 1-3 years is market standard, 18-24 months is ideal. DO NOT change existing terms if they are already in the acceptable range.",
        "why": "Perpetual confidentiality creates unlimited liability. Market standard terms (1-3 years) balance protection with business flexibility.",
        "standard_language": "This Agreement shall expire two (2) years from the date hereof.",
        "negotiation_notes": "2-year terms are standard and usually accepted. Only push for 18 months if relationship allows."
    },

    "governing_law": {
        "title": "Governing Law",
        "severity": "low",  # Changed from moderate - many jurisdictions are acceptable
        "requirement": "Reasonable US jurisdiction",
        "must_have": False,  # Not required if existing law is acceptable
        "flexibility": {
            "unacceptable": "Foreign law, unusual states",
            "questionable": "Less common US jurisdictions",
            "acceptable": "Delaware, New York, California, Texas, Illinois, Massachusetts",
            "ideal": "Delaware"
        },
        "description": "Governing law should be a familiar US jurisdiction. Delaware, New York, and California are all acceptable. DO NOT change if already set to an acceptable jurisdiction.",
        "why": "Preferred jurisdictions have well-established business law and predictable legal outcomes.",
        "standard_language": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware.",
        "negotiation_notes": "Delaware, NY, and CA are all acceptable - don't insist on changing between them."
    },

    "document_retention": {
        "title": "Document Retention Carveout",
        "severity": "high",  # Changed from critical
        "requirement": "Legal, regulatory, and archival exceptions",
        "must_have": True,  # This is critical for compliance
        "flexibility": {
            "unacceptable": "Absolute return/destroy without exceptions",
            "questionable": "Limited carveouts (only legal, or only regulatory)",
            "acceptable": "Legal, regulatory, OR archival exceptions",
            "ideal": "Legal, regulatory, AND archival exceptions"
        },
        "description": "Include exceptions allowing retention of confidential information for legal, regulatory, and archival purposes. ONLY add if missing - don't modify existing reasonable carveouts.",
        "why": "Companies must retain documents for compliance, legal proceedings, and regulatory requirements. This is legally required in many cases.",
        "standard_language": "Notwithstanding the foregoing, Recipient may retain copies of Confidential Information as necessary for legal, regulatory, or archival purposes, or as required by regulation or legal process, provided such retained information remains subject to the confidentiality obligations herein.",
        "negotiation_notes": "This is standard practice and rarely contested. Essential for compliance."
    },

    "employee_solicitation": {
        "title": "Non-Solicitation Carveouts",
        "severity": "high",  # Changed from critical
        "requirement": "At least 2 standard exceptions",
        "must_have": False,  # Nice to have, not critical
        "flexibility": {
            "unacceptable": "No carveouts on broad non-solicit",
            "questionable": "1 exception only",
            "acceptable": "2-3 standard exceptions",
            "ideal": "All 4 standard exceptions (general ads, employee-initiated, prior discussions, terminated employees)"
        },
        "description": "Non-solicitation clauses should include standard exceptions. ONLY add if fewer than 2 exceptions exist. Don't rewrite entire clause if it already has reasonable carveouts.",
        "why": "Absolute non-solicits can prevent normal recruiting and hiring practices. Standard carveouts are market practice.",
        "standard_language": """Nothing herein shall prevent Recipient from hiring such persons who:
(i) respond to general advertisements or recruiting efforts not specifically directed at Disclosing Party's employees;
(ii) initiate discussions with Recipient without any direct or indirect solicitation;
(iii) had prior employment discussions with Recipient before receiving Confidential Information; or
(iv) were terminated by the Disclosing Party prior to commencement of discussions with Recipient.""",
        "negotiation_notes": "At least general advertising and employee-initiated exceptions are usually accepted. All 4 is ideal but not required."
    },

    "competition_clause": {
        "title": "Competition Safe Harbor",
        "severity": "high",  # Changed from critical - important but not always present
        "requirement": "Business freedom disclaimer",
        "must_have": True,  # Critical for PE firm
        "flexibility": {
            "unacceptable": "Restrictions on competing or investing in similar businesses",
            "questionable": "Ambiguous language that could restrict business activities",
            "acceptable": "General disclaimer about business freedom",
            "ideal": "Explicit safe harbor for investments/acquisitions in competitive businesses"
        },
        "description": "Add language clarifying that receiving confidential information does not prevent normal business operations or competition. ONLY add if missing - don't modify existing safe harbors.",
        "why": "Protects Edgewater's ability to invest in or acquire similar/competitive businesses. Critical for private equity operations.",
        "standard_language": "Recipient's receipt and use of Confidential Information will not, in and of itself, prevent or restrict Recipient in any way from carrying on its business in the ordinary course, including without limitation, making investments in, acquisitions of, or competing with businesses similar to or competitive with Disclosing Party.",
        "negotiation_notes": "This is essential for PE firms. Usually accepted with minor wording adjustments."
    },

    "affiliate_clause": {
        "title": "Remove Affiliate References",
        "severity": "low",  # Changed from moderate - not critical
        "requirement": "Limit to named parties (preferred)",
        "must_have": False,  # Nice to have, not critical
        "flexibility": {
            "unacceptable": "Extensive affiliate obligations",
            "questionable": "Some affiliate references",
            "acceptable": "Minimal affiliate references or named parties only",
            "ideal": "No affiliate references"
        },
        "description": "Prefer to delete references to 'affiliates', 'subsidiaries', or 'related entities' to limit scope. However, this is a low-priority change.",
        "why": "Affiliate language can extend obligations to third parties we don't control. But this is negotiable and often accepted in mutual NDAs.",
        "standard_language": "N/A - Delete affiliate references",
        "negotiation_notes": "Low priority - often accepted in mutual NDAs. Focus on material issues first."
    },

    "legal_modifier": {
        "title": "Legal Modifiers",
        "severity": "low",  # Changed from moderate - minor improvements
        "requirement": "Use 'commercially reasonable' (preferred)",
        "must_have": False,  # Nice to have, not critical
        "flexibility": {
            "unacceptable": "Absolute obligations without qualifiers",
            "questionable": "'Best efforts' without context",
            "acceptable": "'Reasonable efforts' or 'best efforts' with limitations",
            "ideal": "'Commercially reasonable efforts'"
        },
        "description": "Prefer 'commercially reasonable efforts' over 'best efforts'. Low priority change - only modify if easy win.",
        "why": "'Best efforts' can create an unreasonably high standard; 'commercially reasonable' is more balanced and market standard.",
        "standard_language": "commercially reasonable efforts",
        "negotiation_notes": "Very low priority - often not worth negotiating unless other changes are already being made."
    },

    "indemnification": {
        "title": "Remove Indemnification",
        "severity": "high",  # Always remove
        "requirement": "No indemnity clauses",
        "must_have": False,  # Must NOT have
        "flexibility": {
            "unacceptable": "Any indemnification for NDA breaches",
            "questionable": "N/A",
            "acceptable": "No indemnification clauses",
            "ideal": "No indemnification clauses"
        },
        "description": "ALWAYS delete any indemnification or hold harmless provisions related to NDA breaches. This is non-negotiable.",
        "why": "Edgewater does not indemnify for NDA violations; standard confidentiality obligations and remedies are sufficient.",
        "standard_language": "N/A - Delete indemnification clauses",
        "negotiation_notes": "Non-negotiable. Indemnification is not standard for NDAs and creates unnecessary liability."
    },

    "injunctive_relief": {
        "title": "Injunctive Relief Limitation",
        "severity": "moderate",
        "requirement": "Require court determination (preferred)",
        "must_have": False,  # Nice to have
        "flexibility": {
            "unacceptable": "Automatic injunctions without court review",
            "questionable": "Injunctive relief without clear process",
            "acceptable": "Standard injunctive relief language",
            "ideal": "Injunctive relief only upon court determination"
        },
        "description": "Prefer to add requirement that injunctive relief requires a final binding determination by a court. Moderate priority.",
        "why": "Prevents automatic injunctions without judicial review. Ensures due process.",
        "standard_language": "upon a final binding determination of a court of competent jurisdiction",
        "negotiation_notes": "Moderate priority - worth pursuing but not critical. Often accepted as reasonable safeguard."
    },

    "broker_clause": {
        "title": "Remove Broker Language",
        "severity": "high",  # Always remove
        "requirement": "Delete broker/commission terms",
        "must_have": False,  # Must NOT have
        "flexibility": {
            "unacceptable": "Broker/commission language in NDA",
            "questionable": "N/A",
            "acceptable": "No broker clauses",
            "ideal": "No broker clauses"
        },
        "description": "ALWAYS remove any references to brokers, commissions, or transaction fees. Not relevant to NDAs.",
        "why": "Broker and commission language is not relevant to confidentiality agreements and creates confusion.",
        "standard_language": "N/A - Delete broker clauses",
        "negotiation_notes": "Usually not present in NDAs. If present, always remove."
    },

    "representations": {
        "title": "Remove Representations",
        "severity": "moderate",
        "requirement": "No accuracy/ownership warranties (preferred)",
        "must_have": False,  # Nice to have
        "flexibility": {
            "unacceptable": "Broad warranties about accuracy, completeness, ownership",
            "questionable": "Limited representations",
            "acceptable": "No representations, or very narrow scope",
            "ideal": "No representations or warranties"
        },
        "description": "Prefer to delete representations and warranties about information accuracy, completeness, or ownership. Moderate priority.",
        "why": "Information should be provided 'as-is' without warranties. Representations create unnecessary liability and are not standard for NDAs.",
        "standard_language": "N/A - Delete representation clauses",
        "negotiation_notes": "Moderate priority - worth pursuing but acceptable to leave if heavily negotiated."
    },

    "assignment": {
        "title": "Assignment Rights",
        "severity": "moderate",
        "requirement": "Allow M&A assignments (preferred)",
        "must_have": False,  # Nice to have
        "flexibility": {
            "unacceptable": "No assignment permitted at all",
            "questionable": "Assignment only with consent (no M&A exception)",
            "acceptable": "Assignment to affiliates or in M&A",
            "ideal": "Free assignment to affiliates and in M&A transactions"
        },
        "description": "Prefer to allow transfers in connection with mergers, acquisitions, or asset sales. Moderate priority.",
        "why": "Enables flexibility during corporate transactions without requiring counterparty consent. Standard for PE firms.",
        "standard_language": "This Agreement may be assigned to affiliates or in connection with a merger, acquisition, or sale of all or substantially all assets.",
        "negotiation_notes": "Moderate priority - usually accepted. PE firms need M&A assignment rights."
    },

    "jurisdiction": {
        "title": "Remove Venue Restrictions",
        "severity": "low",
        "requirement": "No specific venue requirements (preferred)",
        "must_have": False,  # Nice to have
        "flexibility": {
            "unacceptable": "Highly inconvenient exclusive venue",
            "questionable": "Specific venue requirements",
            "acceptable": "Flexible venue or no specific requirement",
            "ideal": "No venue restrictions"
        },
        "description": "Prefer to delete clauses specifying exclusive jurisdiction or venue. Low priority - only pursue if convenient.",
        "why": "Venue restrictions can create inconvenient forum requirements. But this is a minor issue.",
        "standard_language": "N/A - Delete jurisdiction clauses",
        "negotiation_notes": "Low priority - usually not worth fighting over unless venue is highly inconvenient."
    },

    "remedies": {
        "title": "Remedies",
        "severity": "moderate",
        "requirement": "Balanced remedies language",
        "must_have": False,  # Context dependent
        "flexibility": {
            "unacceptable": "One-sided remedies heavily favoring disclosing party",
            "questionable": "Unbalanced remedy provisions",
            "acceptable": "Standard mutual remedies",
            "ideal": "Balanced remedies with appropriate judicial process"
        },
        "description": "Ensure remedies provisions are balanced and require appropriate judicial process. Context-dependent.",
        "why": "Prevents one-sided remedy provisions that unfairly favor the disclosing party.",
        "standard_language": "Varies based on specific clause",
        "negotiation_notes": "Assess based on specific language - ensure equitable relief language is balanced."
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
