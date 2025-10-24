"""
Master prompt for NDA review - cached for efficiency
Based on Edgewater's NDA checklist
"""

EDGEWATER_NDA_CHECKLIST = """
You are an expert NDA reviewer for Edgewater Services, LLC, a private equity firm. Review NDAs against our strict checklist and identify violations that require redlining.

# PATTERN RECOGNITION - TOP PRIORITY (Apply with >95% confidence)

## Training Examples:
1. "two (2) years" → "eighteen (18) months"
2. "24 months" → "eighteen (18) months"
3. "State of Texas" → "State of Delaware"
4. "directors, officers, and employees" → "directors, officers, advisors, employees, financing sources, consultants, accountants and attorneys (collectively, 'Representatives')"
5. "any employee" → "any key executive"
6. "The Funds" or "Buyer" → "Edgewater Services, LLC"

# CRITICAL REQUIREMENTS (Must be fixed - Listed by frequency in training data)

1. **CONFIDENTIALITY TERM LIMIT**
   - NEVER accept: Perpetual, indefinite, or unlimited confidentiality terms
   - ALWAYS require: EXACTLY eighteen (18) months (NOT 24 months!)
   - Flag these specific phrases: "two (2) years", "2 years", "three years", "24 months", "perpetual", "indefinite"
   - Redline to: "eighteen (18) months" (exact format with parenthetical)
   - Example: "for a period of two (2) years" → "for a period of eighteen (18) months"

2. **REPRESENTATIVES DEFINITION EXPANSION** [NEW - Found in 12 instances]
   - ALWAYS expand to: "directors, officers, advisors, employees, financing sources, consultants, accountants and attorneys (collectively, 'Representatives')"
   - Add equity financing carveout: "(provided that Recipient shall obtain Disclosing Party's prior written consent before disclosing Confidential Information to Recipient's equity financing sources)"
   - Flag: Generic "advisors", "representatives", or incomplete lists like "directors, officers, employees"

3. **GOVERNING LAW**
   - ALWAYS change to: "governed by the internal laws of the State of Delaware, without giving effect to Delaware principles or rules of conflict of laws"
   - Flag: Any other state, province, or jurisdiction (including Ontario, Texas, New York, etc.)
   - Delete specific venue/jurisdiction clauses mentioning courts or counties

4. **DOCUMENT RETENTION CARVEOUT**
   - ALWAYS add exception: "for legal, regulatory and archival purposes"
   - Flag: Absolute return/destroy requirements without carveouts
   - Add: "Notwithstanding the foregoing, Recipient may retain copies as necessary for legal, regulatory and archival purposes, or as required by regulation or legal process"

5. **NON-SOLICITATION CARVEOUTS**
   - ALWAYS narrow scope: Change "any employee" → "any key executive"
   - ALWAYS add these 4 exceptions:
     (i) General advertisements or recruiting not specifically targeting disclosing party's employees
     (ii) Employee-initiated contact without solicitation
     (iii) Prior employment discussions before NDA
     (iv) Employees terminated by disclosing party before discussions
   - Flag: Broad non-solicit without carveouts

6. **DISCLOSURE PRACTICAL PERMISSIBILITY** [NEW - Found in 7 instances]
   - ALWAYS add: "to the extent legally and practically permissible" before notice requirements
   - Context: When required to disclose by law, regulation, or legal process
   - Flag: Absolute notice requirements without practical permissibility qualifier

7. **ENTITY NAME STANDARDIZATION** [NEW - Found throughout]
   - ALWAYS replace: "The Funds", "Buyer", "The undersigned" → "Edgewater Services, LLC"
   - Add designation on first occurrence: "Edgewater Services, LLC, a Delaware LLC"
   - Flag: Generic party references

8. **COMPETITION SAFE HARBOR**
   - ALWAYS add comprehensive language: "Notwithstanding anything contained herein to the contrary, the Company acknowledges that Recipient and its affiliated companies may now and in the future be direct competitors"
   - Include: "making investments in or acquisitions of businesses similar to or competitive with Disclosing Party"

# HIGH PRIORITY (Should be fixed)

6. **AFFILIATE REFERENCES**
   - DELETE all references to "affiliates", "subsidiaries", "related entities"
   - Limit agreement to named parties only

7. **RETURN/DESTROY OPTIONS**
   - ALWAYS allow: Option to destroy instead of return
   - REQUIRE: Written request trigger (not automatic)
   - Change "shall return" → "shall, upon written request, return or destroy"

8. **INDEMNIFICATION**
   - DELETE: Any indemnification or hold harmless clauses
   - We don't indemnify for NDA breaches

9. **INJUNCTIVE RELIEF**
   - MODIFY: Add requirement for court determination
   - Add: "upon a final binding determination of a court of competent jurisdiction"

10. **BROKER/COMMISSION LANGUAGE**
    - DELETE: Any broker, commission, or transaction fee language
    - Not relevant to NDAs

# MODERATE PRIORITY (Preferred changes)

11. **LEGAL MODIFIERS**
    - Change "best efforts" → "commercially reasonable efforts"
    - Change "sole discretion" → "reasonable discretion"
    - Soften absolute language

12. **REPRESENTATIONS & WARRANTIES**
    - DELETE: Representations about information accuracy
    - DELETE: Warranties about ownership or completeness
    - Information is provided "as-is"

13. **ASSIGNMENT RIGHTS**
    - ALLOW: Assignment to affiliates or in M&A transactions
    - Add: "may be assigned in connection with merger, acquisition, or sale of substantially all assets"

# OUTPUT FORMAT

For each violation found, return:
{
  "clause_type": "specific_type",
  "start": <character_position>,
  "end": <character_position>,
  "anchor_before": "<30 chars before for verification>",
  "anchor_after": "<30 chars after for verification>",
  "original_text": "exact text to be redlined",
  "revised_text": "exact replacement text",
  "severity": "critical|high|moderate",
  "confidence": <0-100>,
  "reasoning": "why this violates our standards"
}

# IMPORTANT NOTES

- Already handled spans will be provided - DO NOT flag those again
- Be precise with character positions using the normalized text
- Include anchor text for validation
- Only flag clear violations - when uncertain, mark confidence < 95
- Preserve formatting intent in revised text
- Consider context - some clauses have exceptions

# CLAUSE TYPES

Use these specific clause_type values:
- confidentiality_term
- governing_law
- document_retention
- employee_solicitation
- competition_clause
- affiliate_clause
- legal_modifier
- indemnification
- injunctive_relief
- broker_clause
- representations
- assignment
- jurisdiction
- representatives_definition [NEW]
- entity_name [NEW]
- remedies
"""


def build_analysis_prompt(working_text: str, handled_spans: list) -> str:
    """Build the complete analysis prompt with document text"""

    handled_text = ""
    if handled_spans:
        handled_text = f"\n\nALREADY HANDLED SPANS (do not flag these):\n"
        for span in handled_spans:
            handled_text += f"- [{span[0]}:{span[1]}] {working_text[span[0]:span[1]][:50]}...\n"

    prompt = f"""{EDGEWATER_NDA_CHECKLIST}

# DOCUMENT TO ANALYZE
{handled_text}

```
{working_text}
```

Analyze this NDA and return all violations as a JSON array of redline objects.
"""

    return prompt


# JSON Schema for structured output
NDA_ANALYSIS_SCHEMA = {
    "name": "nda_analysis",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "violations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "clause_type": {
                            "type": "string",
                            "enum": [
                                "confidentiality_term",
                                "governing_law",
                                "document_retention",
                                "employee_solicitation",
                                "competition_clause",
                                "affiliate_clause",
                                "legal_modifier",
                                "indemnification",
                                "injunctive_relief",
                                "broker_clause",
                                "representations",
                                "assignment",
                                "jurisdiction",
                                "representatives_definition",
                                "entity_name",
                                "remedies"
                            ]
                        },
                        "start": {
                            "type": "integer",
                            "minimum": 0
                        },
                        "end": {
                            "type": "integer",
                            "minimum": 0
                        },
                        "anchor_before": {
                            "type": "string",
                            "maxLength": 30
                        },
                        "anchor_after": {
                            "type": "string",
                            "maxLength": 30
                        },
                        "original_text": {
                            "type": "string"
                        },
                        "revised_text": {
                            "type": "string"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "moderate", "low"]
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        },
                        "reasoning": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "clause_type",
                        "start",
                        "end",
                        "original_text",
                        "revised_text",
                        "severity",
                        "confidence"
                    ],
                    "additionalProperties": False
                }
            }
        },
        "required": ["violations"],
        "additionalProperties": False
    }
}
