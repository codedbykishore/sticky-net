"""Pre-defined scam test scenarios with planted fake intelligence.

10 unique scenarios covering the full range of Indian scam types.
DEFAULT_SUITE  = exact rubric simulation  (3 scenarios, weights 35/35/30)
EXTENDED_SUITE = full stress-test         (all 10 scenarios, 10% each)
"""

from dataclasses import dataclass, field


@dataclass
class FakeData:
    """Fake intelligence pre-planted in a scenario."""
    phone_numbers: list[str] = field(default_factory=list)
    bank_accounts: list[str] = field(default_factory=list)
    upi_ids: list[str] = field(default_factory=list)
    phishing_links: list[str] = field(default_factory=list)
    email_addresses: list[str] = field(default_factory=list)
    case_ids: list[str] = field(default_factory=list)
    policy_numbers: list[str] = field(default_factory=list)
    order_numbers: list[str] = field(default_factory=list)

    def all_items(self) -> dict[str, list[str]]:
        return {
            "phoneNumbers": self.phone_numbers,
            "bankAccounts": self.bank_accounts,
            "upiIds": self.upi_ids,
            "phishingLinks": self.phishing_links,
            "emailAddresses": self.email_addresses,
            "caseIds": self.case_ids,
            "policyNumbers": self.policy_numbers,
            "orderNumbers": self.order_numbers,
        }

    def total_fields(self) -> int:
        return sum(len(v) for v in self.all_items().values())


@dataclass
class Scenario:
    """A complete scam test scenario."""
    id: str
    name: str
    scam_type: str
    weight: float          # Percentage weight in scored suite
    initial_message: str
    max_turns: int
    fake_data: FakeData
    metadata: dict[str, str]
    persona_context: str   # Gemini scammer persona instructions


# ─────────────────────────────────────────────────────────────────────────────
# 1. Bank Fraud – Account Compromise (Official 35%)
# ─────────────────────────────────────────────────────────────────────────────
BANK_FRAUD_SCENARIO = Scenario(
    id="bank_fraud_001",
    name="Bank Fraud – Account Compromise",
    scam_type="bank_fraud",
    weight=35.0,
    initial_message=(
        "URGENT: Your SBI account ending 4521 has been flagged for suspicious "
        "activity and will be blocked within 2 hours. To prevent this, "
        "call us back immediately or share your OTP for verification. "
        "This is regarding your account security."
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9876543210"],
        bank_accounts=["4521876309124521"],
        upi_ids=["sbi.verify.kyc@fakebank"],
        email_addresses=["fraud.dept@sbi-secure-verify.in"],
    ),
    metadata={"channel": "SMS", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating SBI fraud department officer "
        "'Rajesh Kumar', employee ID 'SBI-FR-48291'. "
        "Goal: convince the victim their account is compromised and gather OTP/details. "
        "Reveal naturally when asked: phone +91-9876543210 as 'direct line', "
        "bank account 4521876309124521 as 'verification account', "
        "UPI sbi.verify.kyc@fakebank as 'safe transfer ID', "
        "email fraud.dept@sbi-secure-verify.in as your official email. "
        "Use urgency, authority, fear. Reveal fake data only when asked or natural."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. UPI Cashback Scam (Official 35%)
# ─────────────────────────────────────────────────────────────────────────────
UPI_FRAUD_SCENARIO = Scenario(
    id="upi_fraud_001",
    name="UPI Cashback Scam",
    scam_type="upi_fraud",
    weight=35.0,
    initial_message=(
        "Congratulations! You have won Rs.15,000 cashback from PhonePe "
        "annual lucky draw. Your number was selected from 2 lakh users. "
        "To claim your cashback, you need to verify your UPI account within "
        "24 hours. Reply YES to proceed."
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-8765432109"],
        upi_ids=["cashback.claim2024@fakeupi", "phonepe.reward@scamwallet"],
        phishing_links=["http://phonepe-cashback-claim.fake-rewards.in/claim?id=PP2024LKY"],
    ),
    metadata={"channel": "WhatsApp", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating PhonePe cashback agent "
        "'Priya Sharma', agent ID 'PP-CB-7821'. "
        "Goal: get the victim to send a small 'verification fee' or click a phishing link. "
        "Reveal: phone +91-8765432109 as 'PhonePe helpline', "
        "UPI cashback.claim2024@fakeupi for 'verification payment', "
        "UPI phonepe.reward@scamwallet as 'alternative transfer', "
        "link http://phonepe-cashback-claim.fake-rewards.in/claim?id=PP2024LKY to 'complete KYC'. "
        "Create excitement and urgency. Act like a real government-approved lottery."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Phishing / Fake Product Offer (Official 30%)
# ─────────────────────────────────────────────────────────────────────────────
PHISHING_SCENARIO = Scenario(
    id="phishing_001",
    name="Fake Product Offer / Phishing Link",
    scam_type="phishing",
    weight=30.0,
    initial_message=(
        "Amazon Sale Alert! You have an unclaimed reward package worth Rs.5,000. "
        "As an Amazon Prime member, you qualify for our exclusive Feb offer. "
        "Claim now before offer expires: http://amaz0n-deals.fake-site.com/claim?id=AMZ12345 "
        "Limited time offer valid for 12 hours only!"
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-7654321098"],
        phishing_links=[
            "http://amaz0n-deals.fake-site.com/claim?id=AMZ12345",
            "http://secure-amazon-kyc.fakestore.in/verify",
        ],
        email_addresses=["offers@fake-amazon-deals.in"],
        order_numbers=["AMZ-ORD-2024-IND-98745"],
    ),
    metadata={"channel": "SMS", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating Amazon support 'Ankit Verma'. "
        "Goal: get the victim to click a phishing link and enter payment details. "
        "Reveal: phone +91-7654321098 as 'Amazon support direct line', "
        "link http://amaz0n-deals.fake-site.com/claim?id=AMZ12345 as 'claim portal', "
        "link http://secure-amazon-kyc.fakestore.in/verify as 'KYC verification', "
        "email offers@fake-amazon-deals.in as 'official Amazon offers email', "
        "order AMZ-ORD-2024-IND-98745 as 'pending reward order'. "
        "Use fake order IDs and urgency."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Tech Support Scam – Fake Microsoft Alert
# ─────────────────────────────────────────────────────────────────────────────
TECH_SUPPORT_SCENARIO = Scenario(
    id="tech_support_001",
    name="Tech Support – Fake Microsoft Security Alert",
    scam_type="tech_support",
    weight=10.0,
    initial_message=(
        "ALERT from Microsoft Security: Your Windows PC has been infected with "
        "Trojan virus. Your personal banking data is at risk. "
        "Call our certified technician immediately: +91-9123456780. "
        "Do NOT shut down your computer. Case ID: MS-TICK-20241847."
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9123456780"],
        phishing_links=["http://microsoft-pc-fix.remote-support-india.com/session?id=MS20241847"],
        email_addresses=["support@microsoft-secure-helpdesk.in"],
        case_ids=["MS-TICK-20241847"],
    ),
    metadata={"channel": "Email", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating a Microsoft certified technician "
        "'Kevin D'Souza', tech ID 'MSFT-IN-5532'. "
        "Goal: get remote access to their computer and charge a fee for 'virus removal'. "
        "Reveal: phone +91-9123456780 as 'Microsoft India helpline', "
        "link http://microsoft-pc-fix.remote-support-india.com/session?id=MS20241847 as 'remote fix tool', "
        "email support@microsoft-secure-helpdesk.in as your official email, "
        "case ID MS-TICK-20241847 as 'your open support ticket'. "
        "Stress urgency about data theft and banking loss."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Job Offer Scam – Fake Work-From-Home Job
# ─────────────────────────────────────────────────────────────────────────────
JOB_SCAM_SCENARIO = Scenario(
    id="job_scam_001",
    name="Fake Work-From-Home Job Offer",
    scam_type="job_scam",
    weight=10.0,
    initial_message=(
        "Hi! We found your profile on Naukri.com. We are hiring for a "
        "Data Entry executive role – Work From Home. Salary Rs.25,000/month. "
        "No experience required. Registration fee of Rs.500 only. "
        "Reply INTERESTED and we will share the offer letter."
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9234567801"],
        bank_accounts=["2301987654321098"],
        upi_ids=["jobrecruitment.fees@scampay"],
        email_addresses=["hr@workhome-india-jobs.net"],
    ),
    metadata={"channel": "WhatsApp", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating an HR recruiter 'Neha Kapoor' "
        "from 'DataServe India Pvt Ltd', company ID 'DS-HR-90021'. "
        "Goal: collect a registration/security deposit fee. "
        "Reveal: phone +91-9234567801 as 'HR direct number', "
        "bank account 2301987654321098 in name of 'DataServe India' for 'registration fee', "
        "UPI jobrecruitment.fees@scampay as 'faster payment option', "
        "email hr@workhome-india-jobs.net as official HR email. "
        "Promise offer letter within 24 hours of payment."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 6. SIM KYC Scam – Jio Expiry Warning
# ─────────────────────────────────────────────────────────────────────────────
SIM_KYC_SCENARIO = Scenario(
    id="sim_kyc_001",
    name="SIM Card KYC Deadline Scam",
    scam_type="sim_kyc",
    weight=10.0,
    initial_message=(
        "Your Jio SIM card services will be deactivated within 24 hours due to "
        "incomplete KYC verification as per TRAI guidelines. "
        "To avoid disconnection, complete KYC immediately by clicking: "
        "http://jio-kyc-update.trai-compliance.in/verify?mobile=XXXXXXXX "
        "Contact: +91-9345678012 for assistance."
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9345678012"],
        phishing_links=["http://jio-kyc-update.trai-compliance.in/verify?mobile=9876543210"],
        email_addresses=["kyc@jio-trai-india-services.in"],
        case_ids=["TRAI-KYC-2024-MH-334421"],
    ),
    metadata={"channel": "SMS", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating Jio KYC officer 'Vikram Singh', "
        "TRAI compliance ID 'TRAI-KYC-2024-MH-334421'. "
        "Goal: get the victim to visit a phishing page and enter Aadhaar/OTP details. "
        "Reveal: phone +91-9345678012 as 'Jio KYC helpdesk', "
        "link http://jio-kyc-update.trai-compliance.in/verify?mobile=9876543210 as 'official KYC portal', "
        "email kyc@jio-trai-india-services.in as official TRAI communication email, "
        "case ID TRAI-KYC-2024-MH-334421 as 'your non-compliance reference'. "
        "Use official TRAI/DoT language. Create urgency about disconnection."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 7. Courier Package Scam – Fake Customs Fee
# ─────────────────────────────────────────────────────────────────────────────
COURIER_SCAM_SCENARIO = Scenario(
    id="courier_scam_001",
    name="Courier Package – Fake Customs Duty Scam",
    scam_type="courier_scam",
    weight=10.0,
    initial_message=(
        "FedEx India: Your international package (tracking ID FDX-IN-20248812) "
        "has been held at customs. A customs duty of Rs.1,850 must be paid "
        "within 48 hours to release your parcel. "
        "Pay now: http://fedex-india-customs.fake-delivery.in/pay?ref=FDX8812 "
        "Helpline: +91-9456789023"
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9456789023"],
        phishing_links=["http://fedex-india-customs.fake-delivery.in/pay?ref=FDX8812"],
        email_addresses=["customs@fedex-india-clearance.net"],
        order_numbers=["FDX-IN-20248812"],
    ),
    metadata={"channel": "SMS", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating FedEx India customs agent "
        "'Arjun Nair', agent ID 'FDX-CUST-7712'. "
        "Goal: collect fake customs duty payment. "
        "Reveal: phone +91-9456789023 as 'FedEx India customs helpline', "
        "link http://fedex-india-customs.fake-delivery.in/pay?ref=FDX8812 as 'payment portal', "
        "email customs@fedex-india-clearance.net as official FedEx email, "
        "order FDX-IN-20248812 as 'your shipment tracking ID'. "
        "Warn that parcel will be returned after 48 hours without payment."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 8. Electricity Disconnection Scam
# ─────────────────────────────────────────────────────────────────────────────
ELECTRICITY_SCAM_SCENARIO = Scenario(
    id="electricity_scam_001",
    name="Electricity Bill – Fake Disconnection Threat",
    scam_type="utility_scam",
    weight=10.0,
    initial_message=(
        "BESCOM Electricity: Your electricity connection will be permanently "
        "disconnected tonight at 9:30 PM due to outstanding bill default. "
        "To avoid disconnection, pay Rs.3,240 immediately. "
        "Contact our billing officer: +91-9567890134. "
        "Consumer No: BESC-20249981."
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9567890134"],
        upi_ids=["bescom.billpay@utilityscam"],
        bank_accounts=["5512345678901234"],
        case_ids=["BESC-CONS-20249981"],
    ),
    metadata={"channel": "SMS", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating BESCOM billing officer 'Ramesh Babu', "
        "employee ID 'BESC-EMP-44521'. "
        "Goal: collect a fake outstanding electricity bill payment. "
        "Reveal: phone +91-9567890134 as 'BESCOM billing direct line', "
        "UPI bescom.billpay@utilityscam as 'official BESCOM payment ID', "
        "bank account 5512345678901234 for 'bulk payment', "
        "case ID BESC-CONS-20249981 as 'pending consumer default reference'. "
        "Be authoritative. Threaten reconnection charges after disconnection."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 9. Fake Loan App Scam
# ─────────────────────────────────────────────────────────────────────────────
LOAN_SCAM_SCENARIO = Scenario(
    id="loan_scam_001",
    name="Instant Loan App – Upfront Fee Scam",
    scam_type="loan_scam",
    weight=10.0,
    initial_message=(
        "RapidCash Loans: You are pre-approved for a personal loan of Rs.2,00,000 "
        "at just 0.5% interest! No CIBIL check required. "
        "Loan disbursed in 2 hours after a refundable processing fee of Rs.2,000. "
        "Apply: http://rapidcash-loan-india.fakeapp.in/apply?ref=RC2024PRE "
        "Call: +91-9678901245"
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9678901245"],
        phishing_links=["http://rapidcash-loan-india.fakeapp.in/apply?ref=RC2024PRE"],
        upi_ids=["rapidcash.process@loanscam"],
        email_addresses=["loans@rapidcash-rbi-approved.in"],
    ),
    metadata={"channel": "WhatsApp", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer impersonating RapidCash loan officer 'Sanjay Mehta', "
        "employee ID 'RC-LOAN-29812'. Claim RBI registration number 'RBI-NBFC-RC-2024'. "
        "Goal: collect a 'processing/insurance fee' before loan disbursal. "
        "Reveal: phone +91-9678901245 as 'loan processing helpline', "
        "link http://rapidcash-loan-india.fakeapp.in/apply?ref=RC2024PRE as 'official RapidCash portal', "
        "UPI rapidcash.process@loanscam for 'processing fee payment', "
        "email loans@rapidcash-rbi-approved.in as official RBI-approved lender email. "
        "Promise Rs.2L in bank within 2 hours after fee payment."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 10. Investment / Crypto Doubling Scam
# ─────────────────────────────────────────────────────────────────────────────
INVESTMENT_SCAM_SCENARIO = Scenario(
    id="investment_scam_001",
    name="Crypto Investment – Money Doubling Scam",
    scam_type="investment_scam",
    weight=10.0,
    initial_message=(
        "Exclusive Offer: Invest Rs.10,000 in our BitGrow AI trading bot and "
        "earn guaranteed Rs.50,000 in 7 days! 500% returns verified by 2,000+ investors. "
        "WhatsApp group: +91-9789012356. "
        "Join now: http://bitgrow-ai-trading.cryptoscam.in/join?ref=BG2024ELITE "
        "Limited slots: only 10 remaining today!"
    ),
    max_turns=10,
    fake_data=FakeData(
        phone_numbers=["+91-9789012356"],
        phishing_links=["http://bitgrow-ai-trading.cryptoscam.in/join?ref=BG2024ELITE"],
        bank_accounts=["6623456789012345"],
        email_addresses=["invest@bitgrow-official-india.com"],
    ),
    metadata={"channel": "WhatsApp", "language": "English", "locale": "IN"},
    persona_context=(
        "You are a scammer running a crypto investment fraud as 'Rohan Gupta', "
        "CEO of 'BitGrow AI Trading', company registration 'SEBI-REG-BG-2024-FAKE'. "
        "Goal: get the victim to invest money into a fake trading platform. "
        "Reveal: phone +91-9789012356 as 'BitGrow WhatsApp helpline', "
        "link http://bitgrow-ai-trading.cryptoscam.in/join?ref=BG2024ELITE as 'official investment portal', "
        "bank account 6623456789012345 for 'direct investment transfer', "
        "email invest@bitgrow-official-india.com as official company email. "
        "Show fake testimonials and profit screenshots. Create FOMO about limited slots."
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# Registries & Suites
# ─────────────────────────────────────────────────────────────────────────────

SCENARIO_REGISTRY: dict[str, Scenario] = {
    s.id: s for s in [
        BANK_FRAUD_SCENARIO,
        UPI_FRAUD_SCENARIO,
        PHISHING_SCENARIO,
        TECH_SUPPORT_SCENARIO,
        JOB_SCAM_SCENARIO,
        SIM_KYC_SCENARIO,
        COURIER_SCAM_SCENARIO,
        ELECTRICITY_SCAM_SCENARIO,
        LOAN_SCAM_SCENARIO,
        INVESTMENT_SCAM_SCENARIO,
    ]
}

# Exact simulation of the hackathon rubric (3 scenarios, weights 35/35/30)
DEFAULT_SUITE: list[str] = [
    "bank_fraud_001",
    "upi_fraud_001",
    "phishing_001",
]

# Extended stress-test (all 10 scenarios at equal 10% weight each)
# Weights are temporarily overridden in the runner – each scenario contributes 10%
EXTENDED_SUITE: list[str] = list(SCENARIO_REGISTRY.keys())
