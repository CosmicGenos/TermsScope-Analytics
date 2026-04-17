"""Category-specific analyser prompt instructions."""

PRIVACY_INSTRUCTION = """\
## Category: Privacy Analysis

Focus ONLY on privacy-related clauses. Look for:
- What personal data is collected (name, email, location, browsing, biometrics, etc.)
- How data is used (advertising, profiling, AI training, analytics)
- Third-party data sharing or selling
- Data retention periods (how long they keep your data)
- User rights: can you access, download, correct, or delete your data?
- Tracking technologies: cookies, pixels, fingerprinting
- Children's privacy protections
- Cross-border data transfers

For each clause found, classify its risk level and explain the practical \
implication for the user.\
"""

FINANCIAL_INSTRUCTION = """\
## Category: Financial Risk Analysis

Focus ONLY on financial and payment-related clauses. Look for:
- Auto-renewal / automatic billing clauses
- Hidden fees or surcharges
- Price change rights (can they increase prices without notice?)
- Refund and cancellation policies
- Free trial to paid conversion terms
- Currency and tax handling
- Payment method requirements
- Late payment penalties
- Subscription tiers and feature gating

For each clause found, classify its risk level and explain the practical \
implication for the user.\
"""

DATA_RIGHTS_INSTRUCTION = """\
## Category: Data Rights & Content Ownership Analysis

Focus ONLY on data rights and content ownership clauses. Look for:
- Who owns content you create or upload?
- License grants: do they get a license to use your content? How broad?
- Can they use your content for AI training or marketing?
- Data portability: can you export your data?
- What happens to your content if you delete your account?
- Intellectual property assignment clauses
- User-generated content moderation rights
- Right to use your name, likeness, or testimonials

For each clause found, classify its risk level and explain the practical \
implication for the user.\
"""

CANCELLATION_INSTRUCTION = """\
## Category: Cancellation & Account Control Analysis

Focus ONLY on account control and cancellation clauses. Look for:
- Account termination: can they close your account without reason?
- Notice period for termination (by either side)
- What happens to your data after account closure?
- Service modification rights: can they change or discontinue features?
- Account suspension conditions
- Inactivity policies
- Migration or transition support if service shuts down
- Multi-device or account-sharing restrictions

For each clause found, classify its risk level and explain the practical \
implication for the user.\
"""

LIABILITY_INSTRUCTION = """\
## Category: Liability & Legal Clauses Analysis

Focus ONLY on liability and legal protection clauses. Look for:
- Limitation of liability: what damages do they exclude?
- Indemnification: must you defend them against claims?
- Forced arbitration: are you giving up the right to sue in court?
- Class-action waiver: can you join group lawsuits?
- Dispute resolution process and jurisdiction
- Warranty disclaimers ("as-is" service)
- Force majeure / act-of-God clauses
- Governing law and venue
- Unilateral right to change terms without notice

For each clause found, classify its risk level and explain the practical \
implication for the user.\
"""

# Mapping from category name to instruction text
CATEGORY_INSTRUCTIONS = {
    "privacy": PRIVACY_INSTRUCTION,
    "financial": FINANCIAL_INSTRUCTION,
    "data_rights": DATA_RIGHTS_INSTRUCTION,
    "cancellation": CANCELLATION_INSTRUCTION,
    "liability": LIABILITY_INSTRUCTION,
}
