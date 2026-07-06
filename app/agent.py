import os
import re
import json
import logging
from typing import Any, AsyncGenerator

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from google.genai import types
# pyrefly: ignore [missing-import]
from google.adk.agents import LlmAgent
# pyrefly: ignore [missing-import]
from google.adk.apps import App
# pyrefly: ignore [missing-import]
from google.adk.workflow import Workflow, START, Edge, node, JoinNode
# pyrefly: ignore [missing-import]
from google.adk.events.event import Event
# pyrefly: ignore [missing-import]
from google.adk.events.request_input import RequestInput
# pyrefly: ignore [missing-import]
from google.adk.agents.context import Context
# pyrefly: ignore [missing-import]
from google.adk.tools import McpToolset, AgentTool
# pyrefly: ignore [missing-import]
from mcp import StdioServerParameters

from app.config import config

# Set up logging
logger = logging.getLogger("smart_community_di")
logging.basicConfig(level=logging.INFO)

# =========================================================
# 1. Pydantic Output Schemas
# =========================================================

class TrafficOutput(BaseModel):
    traffic_summary: str = Field(description="Summary of current traffic conditions")
    travel_prediction: str = Field(description="Congestion or travel time predictions")
    route_recommendation: str = Field(description="Recommended route or public transit options")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")

class HealthcareOutput(BaseModel):
    healthcare_recommendation: str = Field(description="Health advice or wellness recommendations")
    nearby_facilities: list[str] = Field(description="List of nearby clinics, hospitals, or emergency rooms")
    priority_level: str = Field(description="Priority level: low, medium, or high")
    explanation: str = Field(description="Brief explanation of findings")

class EnvironmentOutput(BaseModel):
    environmental_summary: str = Field(description="Summary of AQI, weather, and pollution")
    risk_level: str = Field(description="Risk level: low, moderate, or high")
    prediction: str = Field(description="Predicted environmental changes")
    recommendations: list[str] = Field(description="Actionable sustainability recommendations")

class EmergencyOutput(BaseModel):
    emergency_status: str = Field(description="Active emergency conditions or warning status")
    severity: str = Field(description="Severity: none, low, moderate, major, or critical")
    immediate_actions: list[str] = Field(description="Immediate safety steps for citizens")
    evacuation_plan: str = Field(description="Evacuation route or shelters if applicable")

class PublicServicesOutput(BaseModel):
    relevant_services: list[str] = Field(description="Eligible schemes, benefits, or programs")
    eligibility: str = Field(description="Explanation of citizen eligibility")
    next_steps: list[str] = Field(description="How to apply or participate")
    explanation: str = Field(description="Detailed overview of public services advice")

class DecisionIntelligenceOutput(BaseModel):
    decision_summary: str = Field(description="High-level summary of the final intelligence decision")
    factors_considered: list[str] = Field(description="Key variables and risks analyzed")
    recommended_action: str = Field(description="Final prioritized actionable plan")
    confidence_score: float = Field(description="Confidence score for this decision")
    explanation: str = Field(description="Detailed reasoning for this recommendation")
    future_prediction: str = Field(description="Long-term forecasts or trends expected")

# =========================================================
# 2. MCP Toolset Setup (Wired into specialized agents)
# =========================================================

# Stdio server parameters to launch the local mcp_server.py
mcp_server_params = StdioServerParameters(
    command="uv",
    args=["run", "app/mcp_server.py"],
)

# Connect toolsets with specific tool filters
traffic_mcp_toolset = McpToolset(
    connection_params=mcp_server_params,
    tool_filter=["get_traffic_conditions"]
)

healthcare_mcp_toolset = McpToolset(
    connection_params=mcp_server_params,
    tool_filter=["get_healthcare_facilities"]
)

environment_mcp_toolset = McpToolset(
    connection_params=mcp_server_params,
    tool_filter=["get_environmental_data"]
)

public_services_mcp_toolset = McpToolset(
    connection_params=mcp_server_params,
    tool_filter=["get_citizen_programs"]
)

# =========================================================
# 3. Specialized Sub-Agents
# =========================================================

traffic_agent = LlmAgent(
    name="traffic_agent",
    model=config.model,
    instruction=(
        "You are the Traffic Intelligence Agent. Analyze traffic conditions, "
        "predict congestion, suggest the fastest routes/public transit, and "
        "estimate travel time. Use the get_traffic_conditions tool to fetch real-time data.\n"
        "CRITICAL: You must ALWAYS return a JSON object matching TrafficOutput. Never return "
        "conversational text. If details like destination are missing, assume a general travel query "
        "for the user's location and state that in the traffic_summary."
    ),
    tools=[traffic_mcp_toolset],
    output_schema=TrafficOutput,
)

healthcare_agent = LlmAgent(
    name="healthcare_agent",
    model=config.model,
    instruction=(
        "You are the Healthcare & Wellness Agent. Recommend nearby hospitals, "
        "analyze healthcare availability, and monitor community wellness. "
        "Use the get_healthcare_facilities tool to fetch data. "
        "CRITICAL: Never diagnose diseases or prescribe medicines. Prioritize safety.\n"
        "CRITICAL: You must ALWAYS return a JSON object matching HealthcareOutput. Never return "
        "conversational text. If details are missing, state that in the healthcare_recommendation."
    ),
    tools=[healthcare_mcp_toolset],
    output_schema=HealthcareOutput,
)

environment_agent = LlmAgent(
    name="environment_agent",
    model=config.model,
    instruction=(
        "You are the Environment & Sustainability Agent. Monitor AQI, weather, "
        "pollution levels, and recommend sustainability actions. "
        "Use the get_environmental_data tool to fetch data.\n"
        "CRITICAL: You must ALWAYS return a JSON object matching EnvironmentOutput. Never return "
        "conversational text. If details are missing, state that in the environmental_summary."
    ),
    tools=[environment_mcp_toolset],
    output_schema=EnvironmentOutput,
)

emergency_agent = LlmAgent(
    name="emergency_agent",
    model=config.model,
    instruction=(
        "You are the Emergency Response Agent. Detect emergency situations, suggest "
        "evacuation routes, shelters, and immediate actions to stay safe. "
        "Provide critical status updates when severe weather or hazards are mentioned.\n"
        "CRITICAL: You must ALWAYS return a JSON object matching EmergencyOutput. Never return "
        "conversational text. If no active emergency is detected, return none/low severity with appropriate status."
    ),
    tools=[],
    output_schema=EmergencyOutput,
)

public_services_agent = LlmAgent(
    name="public_services_agent",
    model=config.model,
    instruction=(
        "You are the Public Services & Citizen Support Agent. Provide guidance on "
        "government schemes, public citizen support programs, and eligibility. "
        "Use the get_citizen_programs tool to query eligible schemes.\n"
        "CRITICAL: You must ALWAYS return a JSON object matching PublicServicesOutput. Never return "
        "conversational text. If details like age or income are missing, use defaults and state this in the explanation."
    ),
    tools=[public_services_mcp_toolset],
    output_schema=PublicServicesOutput,
)

# =========================================================
# 4. Root Orchestrator Agent
# =========================================================

orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=config.model,
    instruction=(
        "You are the Root Orchestrator Agent of the Smart Community Decision Intelligence Platform. "
        "Your task is to receive the user's request, analyze their intent, and call the relevant "
        "specialized agents (Traffic, Healthcare, Environment, Emergency, or Public Services) using your tools. "
        "Gather all of their responses, consolidate them, and summarize the findings. "
        "Never invent data. If a domain is not relevant to the user request, do not call its tool. "
        "Explain in your response which specialized agents you invoked."
    ),
    tools=[
        AgentTool(traffic_agent),
        AgentTool(healthcare_agent),
        AgentTool(environment_agent),
        AgentTool(emergency_agent),
        AgentTool(public_services_agent),
    ],
)

# =========================================================
# 5. Decision Intelligence Agent
# =========================================================

decision_agent = LlmAgent(
    name="decision_agent",
    model=config.model,
    instruction=(
        "You are the Decision Intelligence Agent. Read the consolidated results of "
        "the Root Orchestrator and the specialized agents. Analyze patterns, identify "
        "risks, conflicts, and opportunities, and generate one final intelligent recommendation."
    ),
    output_schema=DecisionIntelligenceOutput,
)

# =========================================================
# 6. Workflow Function Nodes
# =========================================================

@node
def security_checkpoint(ctx: Context, node_input: types.Content) -> Event:
    """Security Checkpoint node for PII scrubbing and injection detection."""
    text_content = ""
    if node_input.parts:
        text_content = "".join([part.text for part in node_input.parts if part.text])
    
    # 1. PII Scrubbing (Regex for phone numbers and email addresses)
    phone_pattern = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    
    scrubbed_text = phone_pattern.sub("[REDACTED_PHONE]", text_content)
    scrubbed_text = email_pattern.sub("[REDACTED_EMAIL]", scrubbed_text)
    
    # 2. Prompt Injection Detection (Keyword search)
    injection_keywords = ["ignore previous instructions", "system prompt", "override rules", "bypass security"]
    is_injection = any(kw in scrubbed_text.lower() for kw in injection_keywords)
    
    # 3. Domain-specific rule: Prevent harmful or medical diagnostic prompts
    harmful_keywords = ["make a bomb", "prescribe medicine", "diagnose disease"]
    is_harmful = any(kw in scrubbed_text.lower() for kw in harmful_keywords)
    
    # Audit logging
    audit_log = {
        "event": "security_checkpoint_evaluation",
        "pii_detected": (scrubbed_text != text_content),
        "injection_detected": is_injection,
        "harmful_content_detected": is_harmful,
        "severity": "CRITICAL" if (is_injection or is_harmful) else "INFO"
    }
    logger.info("AUDIT LOG: %s", json.dumps(audit_log))
    
    if is_injection or is_harmful:
        return Event(
            output="Security Violation: The prompt contains unauthorized keywords or injection attempts.",
            route="security_alert"
        )
    
    # Save the scrubbed input to context state
    ctx.state["cleaned_input"] = scrubbed_text
    
    # Continue to orchestrator
    # Convert scrubbed_text back to Content for the downstream LLM agent
    content_input = types.Content(role="user", parts=[types.Part.from_text(text=scrubbed_text)])
    return Event(output=content_input, route="normal")

@node
async def human_approval(ctx: Context, node_input: Any) -> AsyncGenerator[Event, None]:
    """Human-in-the-Loop Node. Pauses for approval if critical risks are detected."""
    # Convert node_input to string to check for critical keywords
    input_str = str(node_input).lower()
    
    # Determine if this contains a critical alert (emergency or high-severity)
    is_critical = any(kw in input_str for kw in ["emergency", "evacuation", "disaster", "critical", "severe", "hazard", "red alert"])
    
    if is_critical:
        if not ctx.resume_inputs:
            logger.info("Pausing workflow for Human-in-the-Loop approval due to critical situation.")
            yield RequestInput(
                interrupt_id="admin_approval",
                message="⚠️ CRITICAL COMMUNITY ALERTS FOUND. Do you authorize final decision intelligence recommendations? (yes/no)"
            )
            return
        
        approval_response = ctx.resume_inputs.get("admin_approval", "").strip().lower()
        if approval_response == "yes":
            logger.info("HITL approval GRANTED by administrator.")
            yield Event(output=node_input, route="approved")
        else:
            logger.warning("HITL approval DENIED by administrator.")
            yield Event(output="Emergency decision recommendations blocked by administrator approval rejection.", route="rejected")
    else:
        # Auto-approve if no critical conditions are present
        yield Event(output=node_input, route="approved")

@node
def security_block(node_input: str) -> str:
    """Formats security or HITL rejection message."""
    return f"Execution Blocked: {node_input}"

@node
def final_output(node_input: Any) -> AsyncGenerator[Event, None]:
    """Formats and yields output for rendering in the Web UI, then completes."""
    if isinstance(node_input, str):
        # Already formatted string (e.g. from security block)
        markdown_text = f"### System Message\n\n{node_input}"
        yield Event(content=types.Content(role="model", parts=[types.Part.from_text(text=markdown_text)]))
        yield Event(output=node_input)
    else:
        # Decision Intelligence Output (BaseModel)
        try:
            di_dict = node_input.model_dump()
        except AttributeError:
            di_dict = dict(node_input)
            
        factors_li = "\n".join([f"- {f}" for f in di_dict.get('factors_considered', [])])
        
        markdown_text = (
            f"# 🧠 Smart Community Decision Intelligence Report\n\n"
            f"## 📋 Decision Summary\n"
            f"{di_dict.get('decision_summary', 'N/A')}\n\n"
            f"## 🛠️ Recommended Action\n"
            f"**{di_dict.get('recommended_action', 'N/A')}**\n\n"
            f"## 📊 Confidence Score: `{di_dict.get('confidence_score', 0.0) * 100:.1f}%`\n\n"
            f"## 🔍 Explanation\n"
            f"{di_dict.get('explanation', 'N/A')}\n\n"
            f"## ⚖️ Factors Considered\n"
            f"{factors_li}\n\n"
            f"## 🔮 Future Prediction\n"
            f"{di_dict.get('future_prediction', 'N/A')}"
        )
        yield Event(content=types.Content(role="model", parts=[types.Part.from_text(text=markdown_text)]))
        yield Event(output=di_dict)

# =========================================================
# 7. Workflow Graph Setup
# =========================================================

workflow_edges = [
    # Start through Security Checkpoint
    Edge(from_node=START, to_node=security_checkpoint),
    
    # Security checkpoint branches
    Edge(from_node=security_checkpoint, to_node=orchestrator_agent, route="normal"),
    Edge(from_node=security_checkpoint, to_node=security_block, route="security_alert"),
    
    # Orchestrator goes to human approval verification
    Edge(from_node=orchestrator_agent, to_node=human_approval),
    
    # Human approval branches
    Edge(from_node=human_approval, to_node=decision_agent, route="approved"),
    Edge(from_node=human_approval, to_node=security_block, route="rejected"),
    
    # Final outputs
    Edge(from_node=decision_agent, to_node=final_output),
    Edge(from_node=security_block, to_node=final_output)
]

root_agent = Workflow(
    name="smart_community_decision_workflow",
    edges=workflow_edges,
    description="Automated Secure Decision Intelligence Platform for Smart Communities."
)

app = App(
    root_agent=root_agent,
    name="app",
)
