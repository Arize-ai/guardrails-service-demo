from typing import Optional, Dict, Any, Annotated, TypedDict
from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from datetime import datetime
import httpx
import os
import json

tracer = trace.get_tracer_provider().get_tracer(__name__)


class GraphState(TypedDict):
    """State for the LangGraph agent"""

    messages: Annotated[list[BaseMessage], add_messages]
    user_input: str
    anomaly_detected: bool
    malicious_detected: bool
    anomaly_reasons: list[str]
    malicious_reasons: list[str]
    anomaly_details: dict[str, Any]
    malicious_details: dict[str, Any]
    anomaly_threshold: float
    malicious_threshold: float
    guardrails_passed: bool
    final_response: str


class ChatService:
    def __init__(self):
        self.agent = ChatOpenAI(
            model="gpt-4o", temperature=0.0, max_completion_tokens=250
        )
        self.guardrails_api_url = os.getenv(
            "GUARDRAILS_API_URL", "http://localhost:8000"
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with guardrails"""
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("check_anomaly", self._check_anomaly)
        workflow.add_node("check_malicious", self._check_malicious)
        workflow.add_node("evaluate_guardrails", self._evaluate_guardrails)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("blocked_response", self._blocked_response)

        # Define edges
        workflow.add_edge(START, "check_malicious")
        workflow.add_edge("check_malicious", "check_anomaly")
        workflow.add_edge("check_anomaly", "evaluate_guardrails")

        # Conditional edge based on guardrails
        workflow.add_conditional_edges(
            "evaluate_guardrails",
            lambda state: "generate" if state["guardrails_passed"] else "blocked",
            {"generate": "generate_response", "blocked": "blocked_response"},
        )

        workflow.add_edge("generate_response", END)
        workflow.add_edge("blocked_response", END)

        return workflow.compile()

    async def _check_anomaly(self, state: GraphState) -> GraphState:
        """Check if the input is anomalous via REST API"""
        request_payload = {
            "text": state["user_input"],
            "timestamp": datetime.now().isoformat(),
            "threshold": state["anomaly_threshold"],
        }

        with tracer.start_as_current_span(
            "check_anomaly",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: "GUARDRAIL",
                SpanAttributes.INPUT_VALUE: state["user_input"],
            },
        ) as span:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.guardrails_api_url}/anomaly/detect",
                        json=request_payload,
                        timeout=10.0,
                    )

                    span.set_attribute("status", response.status_code)
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get("result", {})
                        baseline_stats = data.get("baseline_stats", {})

                        state["anomaly_detected"] = result.get("is_anomaly", False)
                        state["anomaly_reasons"] = result.get("anomaly_reasons", [])

                        # Get current span and add guardrails response as event
                        state["anomaly_details"] = baseline_stats
                    else:
                        # If API fails, don't block
                        state["anomaly_detected"] = False
                        state["anomaly_reasons"] = []
                        state["anomaly_details"] = {}
            except Exception as e:
                # If no baseline exists or API unavailable, don't block
                state["anomaly_detected"] = False
                state["anomaly_reasons"] = []
                state["anomaly_details"] = {}
            finally:
                span.set_attribute(
                    SpanAttributes.OUTPUT_VALUE, state["anomaly_detected"]
                )
                span.set_attribute(
                    SpanAttributes.METADATA, json.dumps(state["anomaly_details"])
                )
            return state

    async def _check_malicious(self, state: GraphState) -> GraphState:
        """Check if the input is malicious via REST API"""
        request_payload = {
            "text": state["user_input"],
            "timestamp": datetime.now().isoformat(),
            "threshold": state["malicious_threshold"],
        }
        with tracer.start_as_current_span(
            "check_malicious",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: "GUARDRAIL",
                SpanAttributes.INPUT_VALUE: state["user_input"],
            },
        ) as span:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.guardrails_api_url}/malicious/detect",
                        json=request_payload,
                        timeout=10.0,
                    )

                    span.set_attribute("status", response.status_code)
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get("result", {})
                        baseline_stats = data.get("baseline_stats", {})

                        state["malicious_detected"] = result.get("is_malicious", False)
                        state["malicious_reasons"] = result.get("malicious_reasons", [])
                        state["malicious_details"] = baseline_stats
                    else:
                        # If API fails, don't block
                        state["malicious_detected"] = False
                        state["malicious_reasons"] = []
                        state["malicious_details"] = {}
            except Exception as e:
                # If no baseline exists or API unavailable, don't block
                state["malicious_detected"] = False
                state["malicious_reasons"] = []
                state["malicious_details"] = {}
            finally:
                span.set_attribute(
                    SpanAttributes.OUTPUT_VALUE, state["malicious_detected"]
                )
                span.set_attribute(
                    SpanAttributes.METADATA, json.dumps(state["malicious_details"])
                )

        return state

    async def _evaluate_guardrails(self, state: GraphState) -> GraphState:
        """Evaluate if guardrails passed"""
        with tracer.start_as_current_span(
            "evaluate_guardrails",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: "CHAIN",
                SpanAttributes.INPUT_VALUE: f"anomaly_detected: {state['anomaly_detected']}, malicious_detected: {state['malicious_detected']}",
            },
        ) as span:
            passed = not (state["anomaly_detected"] or state["malicious_detected"])
            state["guardrails_passed"] = passed
            span.set_attribute(
                SpanAttributes.OUTPUT_VALUE, f"Guardrails passed: {passed}"
            )
            return state

    async def _generate_response(self, state: GraphState) -> GraphState:
        """Generate AI response when guardrails pass"""
        with tracer.start_as_current_span(
            "generate_response",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: "LLM",
                SpanAttributes.INPUT_VALUE: state["user_input"],
            },
        ) as span:
            result = {}
            try:
                input_message = HumanMessage(content=state["user_input"])
                result = await self.agent.ainvoke([input_message])
                state["final_response"] = str(result.content)
                state["messages"].extend(
                    [input_message, AIMessage(content=state["final_response"])]
                )
                span.set_attribute(
                    SpanAttributes.LLM_TOKEN_COUNT_PROMPT,
                    int(result.response_metadata["token_usage"]["prompt_tokens"]),
                )
                span.set_attribute(
                    SpanAttributes.LLM_TOKEN_COUNT_COMPLETION,
                    int(result.response_metadata["token_usage"]["completion_tokens"]),
                )
                span.set_attribute(
                    SpanAttributes.LLM_TOKEN_COUNT_TOTAL,
                    int(result.response_metadata["token_usage"]["total_tokens"]),
                )
                span.set_attribute(
                    SpanAttributes.LLM_MODEL_NAME,
                    result.response_metadata["model_name"],
                )

            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                state["final_response"] = (
                    f"I'm sorry, but I cannot process your request at this time."
                )
            finally:
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, state["final_response"])
                span.set_attribute(
                    SpanAttributes.METADATA, json.dumps(result.response_metadata)
                )
                return state

    async def _blocked_response(self, state: GraphState) -> GraphState:
        """Return canned message when guardrails fail"""
        with tracer.start_as_current_span(
            "blocked_response",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: "CHAIN",
                SpanAttributes.INPUT_VALUE: state["user_input"],
            },
        ) as span:
            reasons = []

            if state["anomaly_detected"]:
                reasons.extend(state["anomaly_reasons"])

            if state["malicious_detected"]:
                reasons.extend(state["malicious_reasons"])

            canned_message = (
                "I'm sorry, but I cannot process your request at this time. "
                "Our safety systems have detected potential issues with your input. "
                "Please rephrase your request or contact support if you believe this is an error."
            )
            span.set_attribute(SpanAttributes.OUTPUT_VALUE, canned_message)

            if reasons:
                canned_message += f"\n\nReasons: {'; '.join(reasons)}"

            span.set_attribute(
                SpanAttributes.METADATA,
                json.dumps(
                    {
                        "malicious_detected": state["malicious_detected"],
                        "anomaly_detected": state["anomaly_detected"],
                        "reasons": reasons,
                    }
                ),
            )

            state["final_response"] = canned_message
            state["messages"].append(AIMessage(content=canned_message))
            return state

    async def chat(
        self,
        message: str,
        anomaly_threshold: float,
        malicious_threshold: float,
    ) -> str:
        # Get tracer and create a span for this operation
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(
            "chat_service",
            attributes={
                SpanAttributes.OPENINFERENCE_SPAN_KIND: "CHAIN",
                SpanAttributes.INPUT_VALUE: message,
                "anomaly_threshold": anomaly_threshold,
                "malicious_threshold": malicious_threshold,
            },
        ) as span:
            final_state = {}
            try:
                # Initialize state with the user input
                initial_state = GraphState(
                    messages=[],
                    user_input=message,
                    anomaly_detected=False,
                    malicious_detected=False,
                    anomaly_reasons=[],
                    malicious_reasons=[],
                    anomaly_details={},
                    malicious_details={},
                    guardrails_passed=True,
                    final_response="",
                    anomaly_threshold=anomaly_threshold,
                    malicious_threshold=malicious_threshold,
                )

                # Run the graph
                final_state = await self.graph.ainvoke(initial_state)

                span.set_status(trace.Status(trace.StatusCode.OK))
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise Exception(f"Chat service error: {str(e)}")
            finally:
                response = final_state.get(
                    "final_response", "An error occurred while processing the request"
                )
                output = (
                    response,
                    final_state.get("anomaly_details", {}),
                    final_state.get("malicious_details", {}),
                )
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, response)
                span.set_attribute(
                    SpanAttributes.METADATA,
                    json.dumps(
                        {
                            "anomaly_details": final_state.get("anomaly_details", {}),
                            "malicious_details": final_state.get(
                                "malicious_details", {}
                            ),
                        }
                    ),
                )
                return output
