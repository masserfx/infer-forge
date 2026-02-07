"""AI agents for email processing in the INFER FORGE platform.

Provides email classification and structured data extraction agents
powered by Anthropic Claude API with tool_use for reliable output.
"""

from app.agents.email_classifier import ClassificationResult, EmailClassifier
from app.agents.email_parser import EmailParser, ParsedInquiry, ParsedItem

__all__ = [
    "ClassificationResult",
    "EmailClassifier",
    "EmailParser",
    "ParsedInquiry",
    "ParsedItem",
]
