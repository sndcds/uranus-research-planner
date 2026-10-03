from research_planner.conversation_schema import ResearchConversationContext
from research_planner.schemas import PlanRequest


class ConversationPlanRequest(PlanRequest):
    conversation_context: ResearchConversationContext | None = None
