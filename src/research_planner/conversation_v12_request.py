from research_planner.conversation_v12_schema import ResearchConversationContextV12
from research_planner.schemas import PlanRequest


class ConversationPlanRequestV12(PlanRequest):
    conversation_context: ResearchConversationContextV12 | None = None
