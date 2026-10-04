"""Server-owned advisory context. No transcript, rows, identity or locations."""

from research_planner.conversation_v12_request import ConversationPlanRequestV12
from research_planner.conversation_v12_schema import ResearchPlanSummaryV12
from research_planner.research_v13_schema import AnswerLanguage


class ConversationPlanRequestV13(ConversationPlanRequestV12):
    conversation_language: AnswerLanguage | None = None
    pending_clarification: ResearchPlanSummaryV12 | None = None
    previous_answer_available: bool = False
