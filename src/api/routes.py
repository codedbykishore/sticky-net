"""API route definitions."""

import random
import structlog
from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EngagementMetrics,
    ErrorResponse,
    ExtractedIntelligence,
    OtherIntelItem,
    ScamType,
    SenderType,
    StatusType,
)
from src.detection.detector import ScamDetector
from src.agents.honeypot_agent import HoneypotAgent
from src.agents.policy import EngagementPolicy
from src.intelligence.extractor import IntelligenceExtractor
from src.exceptions import StickyNetError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        200: {"model": AnalyzeResponse, "description": "Successful analysis"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_message(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze incoming message for scam detection and engagement.

    This endpoint:
    1. Analyzes the message for scam indicators
    2. If scam detected, activates AI agent for engagement
    3. Extracts intelligence from conversation
    4. Returns structured response with metrics
    """
    log = logger.bind(
        channel=request.metadata.channel,
        history_length=len(request.conversationHistory),
    )
    log.info("Processing analyze request")

    try:
        # Step 1: Detect scam
        detector = ScamDetector()
        detection_result = await detector.analyze(
            message=request.message.text,
            history=request.conversationHistory,
            metadata=request.metadata,
        )

        if not detection_result.is_scam:
            log.info("Message not detected as scam")
            
            # Generate a simple conversational response for non-scam messages
            normal_responses = [
                "Hello! How can I help you today?",
                "Hi there! Is everything alright?",
                "Hey! What can I do for you?",
                "Hello! Yes, I'm here. What's up?",
                "Hi! I'm listening. What did you want to tell me?",
            ]
            
            return AnalyzeResponse(
                status=StatusType.SUCCESS,
                scamDetected=False,
                scamType=None,
                confidence=detection_result.confidence,
                agentNotes="No scam indicators detected",
                agentResponse=random.choice(normal_responses),
            )

        log.info("Scam detected", confidence=detection_result.confidence)

        # Step 2: Extract intelligence FIRST to check for exit condition
        # Only extract from SCAMMER messages (not from user/AI responses)
        extractor = IntelligenceExtractor()
        scammer_messages_text = " ".join([
            m.text for m in request.conversationHistory if m.sender == SenderType.SCAMMER
        ] + [request.message.text])  # Include current scammer message
        
        intelligence = extractor.extract(scammer_messages_text)
        
        # Calculate correct turn number: count scammer messages in history + current message
        # Turn = number of scammer messages (each scammer message = 1 turn)
        scammer_messages_in_history = sum(
            1 for m in request.conversationHistory if m.sender == SenderType.SCAMMER
        )
        current_turn = scammer_messages_in_history + 1  # +1 for current scammer message
        
        # Check if high-value intelligence is complete (exit condition)
        policy = EngagementPolicy()
        high_value_complete = policy.is_high_value_intelligence_complete(
            bank_accounts=intelligence.bank_accounts,
            phone_numbers=intelligence.phone_numbers,
            upi_ids=intelligence.upi_ids,
            beneficiary_names=intelligence.beneficiary_names,
        )
        
        # Get missing intelligence for targeted extraction
        missing_intel = policy.get_missing_intelligence(
            bank_accounts=intelligence.bank_accounts,
            phone_numbers=intelligence.phone_numbers,
            upi_ids=intelligence.upi_ids,
            beneficiary_names=intelligence.beneficiary_names,
        )
        
        # Exit responses when high-value intelligence is extracted
        exit_responses = [
            # Original responses
            "okay i am calling that number now, hold on...",
            "wait my son just came home, let me ask him to help me with this",
            "one second, someone is at the door, i will call you back",
            "okay i sent the money, now my phone is dying, i need to charge it",
            "hold on, i am getting another call from my bank, let me check",
            # New variety - domestic interruptions
            "oh no my doorbell is ringing, someone is at the door... i will do this later",
            "sorry my neighbor aunty just came, i have to go help her with something urgent",
            "arey my grandson is crying, i need to check on him... one minute",
            "oh god my cooking is burning on the stove! i smell smoke!! wait wait",
            "wait my daughter-in-law is calling me for lunch, i have to go eat first",
            "oh the milk is boiling over! wait wait i have to go to kitchen!!",
            # New variety - health/personal
            "my blood pressure medicine time ho gaya, i feel dizzy... let me take rest",
            "ji actually i just remembered i have doctor appointment today, need to leave now",
            "sorry sir power cut ho gaya, my phone battery is only 2%... will call you back",
            # New variety - skepticism/confusion
            "wait i am getting another call, it shows BANK on my phone... should i pick up??",
            "hold on my beti is asking who i am talking to, she looks worried...",
            "one second, my husband just came and he is asking what i am doing on phone",
        ]
        
        if high_value_complete:
            log.info(
                "High-value intelligence complete, triggering exit",
                bank_accounts=len(intelligence.bank_accounts),
                phone_numbers=len(intelligence.phone_numbers),
                upi_ids=len(intelligence.upi_ids),
                beneficiary_names=len(intelligence.beneficiary_names),
                ifsc_codes=len(intelligence.ifsc_codes),
                phishing_links=len(intelligence.phishing_links),
                whatsapp_numbers=len(intelligence.whatsapp_numbers),
            )
            # Use exit response instead of engaging further
            exit_response = random.choice(exit_responses)
            
            # Generate proper exit notes with all intelligence
            # Use the same format as shown during conversation
            from src.agents.honeypot_agent import get_agent
            from src.agents.persona import EmotionalState
            from src.agents.policy import EngagementMode
            
            agent = get_agent()
            # Create a minimal persona for exit notes
            class ExitPersona:
                emotional_state = EmotionalState.CALM
            
            # Determine engagement mode based on confidence (same logic as policy)
            engagement_mode = EngagementMode.AGGRESSIVE if detection_result.confidence > 0.85 else EngagementMode.CAUTIOUS
            
            merged_intel = ExtractedIntelligence(
                bankAccounts=intelligence.bank_accounts,
                upiIds=intelligence.upi_ids,
                phoneNumbers=intelligence.phone_numbers,
                phishingLinks=intelligence.phishing_links,
                emails=intelligence.emails,
                beneficiaryNames=intelligence.beneficiary_names,
                bankNames=intelligence.bank_names,
                ifscCodes=intelligence.ifsc_codes,
                whatsappNumbers=intelligence.whatsapp_numbers,
            )
            
            # Use the same mode as would have been used during conversation
            exit_notes = agent._generate_notes(
                detection=detection_result,
                persona=ExitPersona(),
                mode=engagement_mode,
                turn_number=current_turn,
                extracted_intel=merged_intel,
            )
            
            # Convert scam_type string to ScamType enum
            scam_type_enum = None
            if detection_result.scam_type:
                try:
                    scam_type_enum = ScamType(detection_result.scam_type)
                except ValueError:
                    scam_type_enum = ScamType.OTHERS
            
            return AnalyzeResponse(
                status=StatusType.SUCCESS,
                scamDetected=True,
                scamType=scam_type_enum,
                confidence=detection_result.confidence,
                engagementMetrics=EngagementMetrics(
                    engagementDurationSeconds=0,
                    totalMessagesExchanged=current_turn,
                ),
                extractedIntelligence=ExtractedIntelligence(
                    bankAccounts=intelligence.bank_accounts,
                    upiIds=intelligence.upi_ids,
                    phoneNumbers=intelligence.phone_numbers,
                    phishingLinks=intelligence.phishing_links,
                    emails=intelligence.emails,
                    beneficiaryNames=intelligence.beneficiary_names,
                    bankNames=intelligence.bank_names,
                    ifscCodes=intelligence.ifsc_codes,
                    whatsappNumbers=intelligence.whatsapp_numbers,
                ),
                agentNotes=exit_notes,
                agentResponse=exit_response,
            )

        # Step 3: Engage with AI agent (only if not exiting)
        agent = HoneypotAgent()
        engagement_result = await agent.engage(
            message=request.message,
            history=request.conversationHistory,
            metadata=request.metadata,
            detection=detection_result,
            turn_number=current_turn,  # Pass calculated turn number
            missing_intel=missing_intel,  # Tell agent what to extract
            extracted_intel={
                "upi_ids": intelligence.upi_ids,
                "bank_accounts": intelligence.bank_accounts,
                "phone_numbers": intelligence.phone_numbers,
                "beneficiary_names": intelligence.beneficiary_names,
            },
        )

        # Log the raw agent response for debugging
        log.info(
            "Agent engagement complete",
            agent_response=engagement_result.response if engagement_result.response else None,
            has_extracted_intel=engagement_result.extracted_intelligence is not None,
        )
        
        # Log LLM-extracted intelligence if available (for debugging)
        if engagement_result.extracted_intelligence:
            llm_intel = engagement_result.extracted_intelligence
            log.info(
                "LLM extracted intelligence (raw)",
                bank_accounts=llm_intel.bankAccounts,
                upi_ids=llm_intel.upiIds,
                phone_numbers=llm_intel.phoneNumbers,
                beneficiary_names=llm_intel.beneficiaryNames,
                urls=llm_intel.phishingLinks,
                whatsapp_numbers=llm_intel.whatsappNumbers,
                ifsc_codes=llm_intel.ifscCodes,
                other_critical_info=[item.model_dump() for item in llm_intel.other_critical_info] if llm_intel.other_critical_info else [],
            )

        # Step 4: Merge LLM-extracted intelligence with regex extraction
        # This combines the best of both worlds:
        # - Regex: Fast, deterministic, catches standard formats
        # - LLM: Flexible, catches obfuscated data, contextual references
        if engagement_result.extracted_intelligence:
            merged_intel = extractor.merge_intelligence(
                regex_intel=intelligence,
                llm_intel=engagement_result.extracted_intelligence,
            )
            log.info(
                "Merged LLM + regex intelligence",
                bank_accounts=len(merged_intel.bankAccounts),
                upi_ids=len(merged_intel.upiIds),
                phone_numbers=len(merged_intel.phoneNumbers),
                beneficiary_names=len(merged_intel.beneficiaryNames),
                other_info=len(merged_intel.other_critical_info),
            )
        else:
            # Fallback to regex-only extraction
            merged_intel = ExtractedIntelligence(
                bankAccounts=intelligence.bank_accounts,
                upiIds=intelligence.upi_ids,
                phoneNumbers=intelligence.phone_numbers,
                phishingLinks=intelligence.phishing_links,
                emails=intelligence.emails,
                beneficiaryNames=intelligence.beneficiary_names,
                bankNames=intelligence.bank_names,
                ifscCodes=intelligence.ifsc_codes,
                whatsappNumbers=intelligence.whatsapp_numbers,
                other_critical_info=[],
            )

        # Step 5: Build response
        # Convert scam_type string to ScamType enum
        scam_type_enum = None
        if detection_result.scam_type:
            try:
                scam_type_enum = ScamType(detection_result.scam_type)
            except ValueError:
                scam_type_enum = ScamType.OTHERS
        
        # Ensure agentResponse is never None
        agent_response = engagement_result.response
        if not agent_response:
            agent_response = "Sorry, I'm having trouble understanding. Can you repeat that?"
            log.warning("Agent response was None, using fallback")
        
        # Regenerate agent notes with merged intelligence counts
        from src.agents.honeypot_agent import get_agent
        agent = get_agent()
        final_notes = agent._generate_notes(
            detection=detection_result,
            persona=agent.persona_manager.get_or_create_persona(engagement_result.conversation_id),
            mode=engagement_result.engagement_mode,
            turn_number=current_turn,
            extracted_intel=merged_intel,
        )
        
        return AnalyzeResponse(
            status=StatusType.SUCCESS,
            scamDetected=True,
            scamType=scam_type_enum,
            confidence=detection_result.confidence,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=engagement_result.duration_seconds,
                totalMessagesExchanged=current_turn,
            ),
            extractedIntelligence=merged_intel,
            agentNotes=final_notes,
            agentResponse=agent_response,
        )

    except StickyNetError as e:
        log.error("Application error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        log.exception("Unexpected error")
        raise HTTPException(status_code=500, detail="Internal server error")