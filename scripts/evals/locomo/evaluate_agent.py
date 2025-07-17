"""
EvaluateAgent - Specialized Agent for Answer and Memory Evaluation

This agent provides comprehensive evaluation capabilities:
1. Evaluate generated answers against standard answers (yes/no)
2. Evaluate retrieved events against standard answers (relevance check for each event)
3. Analyze reasons why generated answers are incorrect
4. Provide detailed evaluation reports
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

import dotenv
dotenv.load_dotenv()

from memu.llm import AzureOpenAIClient
from memu.utils import get_logger, setup_logging

# Add prompts directory to path and import prompt loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'prompts'))
from prompt_loader import get_prompt_loader

logger = setup_logging(__name__, enable_flush=True)


class EvaluateAgent:
    """
    Specialized evaluation agent for answer and memory evaluation.
    
    Provides tools for:
    - Answer comparison and evaluation
    - Retrieved events relevance checking
    - Error analysis and reasoning
    - Detailed evaluation reporting
    """
    
    def __init__(
        self,
        azure_endpoint: str = None,
        api_key: str = None,
        chat_deployment: str = "gpt-4.1-mini",
        use_entra_id: bool = False,
        api_version: str = "2024-02-15-preview"
    ):
        """Initialize EvaluateAgent with LLM configuration"""
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.chat_deployment = chat_deployment
        self.use_entra_id = use_entra_id
        self.api_version = api_version
        
        # Initialize prompt loader
        self.prompt_loader = get_prompt_loader()
        
        # Initialize LLM client
        self.llm_client = self._init_llm_client()
        
        logger.info("EvaluateAgent initialized")

    def _init_llm_client(self):
        """Initialize the LLM client"""
        try:
            return AzureOpenAIClient(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                chat_deployment=self.chat_deployment,
                use_entra_id=self.use_entra_id,
                api_version=self.api_version
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            raise

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available evaluation tools"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "evaluate_answer_accuracy",
                    "description": "Evaluate if a generated answer matches the standard answer (yes/no evaluation)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The original question being answered"
                            },
                            "generated_answer": {
                                "type": "string",
                                "description": "The AI-generated answer to evaluate"
                            },
                            "standard_answer": {
                                "type": "string",
                                "description": "The reference/standard answer to compare against"
                            }
                        },
                        "required": ["question", "generated_answer", "standard_answer"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "evaluate_retrieved_events",
                    "description": "Evaluate each retrieved event for relevance to the standard answer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The original question"
                            },
                            "standard_answer": {
                                "type": "string",
                                "description": "The standard/expected answer"
                            },
                            "retrieved_events": {
                                "type": "array",
                                "description": "List of retrieved events to evaluate",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "character": {"type": "string"},
                                        "event": {"type": "string"},
                                        "score": {"type": "number"},
                                        "rank": {"type": "integer"}
                                    }
                                }
                            }
                        },
                        "required": ["question", "standard_answer", "retrieved_events"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_answer_errors",
                    "description": "Analyze why a generated answer is incorrect and provide detailed reasoning",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The original question"
                            },
                            "generated_answer": {
                                "type": "string",
                                "description": "The incorrect AI-generated answer"
                            },
                            "standard_answer": {
                                "type": "string",
                                "description": "The correct standard answer"
                            },
                            "retrieved_events": {
                                "type": "array",
                                "description": "Retrieved events that were used to generate the answer",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "character": {"type": "string"},
                                        "event": {"type": "string"},
                                        "score": {"type": "number"},
                                        "rank": {"type": "integer"}
                                    }
                                }
                            }
                        },
                        "required": ["question", "generated_answer", "standard_answer"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "comprehensive_evaluation",
                    "description": "Perform comprehensive evaluation including answer accuracy, event relevance, and error analysis",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The original question"
                            },
                            "generated_answer": {
                                "type": "string",
                                "description": "The AI-generated answer to evaluate"
                            },
                            "standard_answer": {
                                "type": "string",
                                "description": "The reference/standard answer"
                            },
                            "retrieved_events": {
                                "type": "array",
                                "description": "Retrieved events used for answer generation",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "character": {"type": "string"},
                                        "event": {"type": "string"},
                                        "score": {"type": "number"},
                                        "rank": {"type": "integer"}
                                    }
                                }
                            }
                        },
                        "required": ["question", "generated_answer", "standard_answer"]
                    }
                }
            }
        ]

    def evaluate_answer_accuracy(self, question: str, generated_answer: str, standard_answer: str) -> Dict[str, Any]:
        """Evaluate if a generated answer matches the standard answer using locomo_grader format"""
        try:
            # System prompt
            system_prompt = """
            You are an expert grader that determines if answers to questions match a gold standard answer
            """

            # Accuracy evaluation prompt
            accuracy_prompt = f"""
Your task is to label an answer to a question as 'CORRECT' or 'WRONG'. You will be given the following data:
    (1) a question (posed by one user to another user),
    (2) a 'gold' (ground truth) answer,
    (3) a generated answer
which you will score as CORRECT/WRONG.

The point of the question is to ask about something one user should know about the other user based on their prior conversations.
The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
Question: Do you remember what I got the last time I went to Hawaii?
Gold answer: A shell necklace
The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT.

For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

Now it's time for the real question:
Question: {question}
Gold answer: {standard_answer}
Generated answer: {generated_answer}

First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG.
Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

Just return the label CORRECT or WRONG in a json format with the key as "label".
"""

            # Get evaluation from LLM with system message
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": accuracy_prompt}
            ]
            llm_response = self.llm_client.chat_completion(messages, max_tokens=500, temperature=0.1)
            
            if not llm_response.success:
                raise Exception(f"LLM evaluation failed: {llm_response.error}")
                
            evaluation_text = llm_response.content.strip()
            
            # Parse the JSON response
            is_correct = False
            explanation = evaluation_text
            
            try:
                # Try to parse as JSON
                import json
                # Look for JSON content
                if "{" in evaluation_text and "}" in evaluation_text:
                    json_start = evaluation_text.find("{")
                    json_end = evaluation_text.rfind("}") + 1
                    json_text = evaluation_text[json_start:json_end]
                    result = json.loads(json_text)
                    label = result.get("label", "").upper()
                    is_correct = label == "CORRECT"
                    
                    # Extract explanation from text before JSON
                    explanation_part = evaluation_text[:json_start].strip()
                    if explanation_part:
                        explanation = explanation_part
                    else:
                        explanation = f"Evaluation result: {label}"
                else:
                    # Fallback: look for CORRECT/WRONG in text
                    text_upper = evaluation_text.upper()
                    if "CORRECT" in text_upper and "WRONG" not in text_upper:
                        is_correct = True
                    elif "WRONG" in text_upper:
                        is_correct = False
                    explanation = evaluation_text
                    
            except json.JSONDecodeError:
                # Fallback: look for CORRECT/WRONG in text
                text_upper = evaluation_text.upper()
                if "CORRECT" in text_upper and "WRONG" not in text_upper:
                    is_correct = True
                elif "WRONG" in text_upper:
                    is_correct = False
                explanation = evaluation_text
            
            return {
                "success": True,
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "is_correct": is_correct,
                "explanation": explanation,
                "evaluation_text": evaluation_text
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate answer accuracy: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "is_correct": False,
                "explanation": f"Evaluation failed: {e}",
                "evaluation_text": ""
            }

    def evaluate_retrieved_events(self, question: str, standard_answer: str, retrieved_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate each retrieved event for relevance to the standard answer"""
        try:
            if not retrieved_events:
                return {
                    "success": True,
                    "question": question,
                    "standard_answer": standard_answer,
                    "total_events": 0,
                    "event_evaluations": [],
                    "relevant_count": 0,
                    "irrelevant_count": 0
                }
            
            event_evaluations = []
            relevant_count = 0
            irrelevant_count = 0
            
            for i, event_data in enumerate(retrieved_events):
                try:
                    event_text = event_data.get('event', '')
                    character = event_data.get('character', 'Unknown')
                    score = event_data.get('score', 0)
                    rank = event_data.get('rank', i + 1)
                    
                    # Create evaluation prompt for this event
                    event_evaluation_prompt = f"""You are an expert evaluator. Your task is to determine if a retrieved event is relevant to answering a question.

Question: {question}

Standard Answer: {standard_answer}

Retrieved Event (from {character}): {event_text}

Instructions:
1. Determine if this event contains information that is relevant to the standard answer
2. Answer with "YES" if the event is relevant, "NO" if it's not relevant
3. Provide a brief explanation of your reasoning

Response format:
Relevance: [YES/NO]
Explanation: [Your reasoning]"""

                    # Get evaluation from LLM
                    messages = [{"role": "user", "content": event_evaluation_prompt}]
                    llm_response = self.llm_client.chat_completion(messages, max_tokens=300, temperature=0.1)
                    
                    if not llm_response.success:
                        raise Exception(f"LLM evaluation failed for event {i}: {llm_response.error}")
                    
                    evaluation_text = llm_response.content.strip()
                    
                    # Parse the evaluation result
                    is_relevant = False
                    explanation = evaluation_text
                    
                    # Look for relevance decision
                    lines = evaluation_text.split('\n')
                    for line in lines:
                        if line.strip().startswith('Relevance:'):
                            relevance_text = line.split(':', 1)[1].strip().upper()
                            is_relevant = 'YES' in relevance_text
                            break
                    else:
                        # Fallback: look for yes/no in text
                        text_lower = evaluation_text.lower()
                        if "yes" in text_lower and "no" not in text_lower:
                            is_relevant = True
                        elif "no" in text_lower:
                            is_relevant = False
                    
                    # Extract explanation
                    explanation_lines = []
                    capture_explanation = False
                    for line in lines:
                        if line.strip().startswith('Explanation:'):
                            explanation_lines.append(line.split(':', 1)[1].strip())
                            capture_explanation = True
                        elif capture_explanation:
                            explanation_lines.append(line.strip())
                    
                    if explanation_lines:
                        explanation = ' '.join(explanation_lines)
                    
                    # Count relevance
                    if is_relevant:
                        relevant_count += 1
                    else:
                        irrelevant_count += 1
                    
                    event_evaluations.append({
                        "rank": rank,
                        "character": character,
                        "event": event_text,
                        "original_score": score,
                        "is_relevant": is_relevant,
                        "explanation": explanation,
                        "evaluation_text": evaluation_text
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to evaluate event {i}: {e}")
                    event_evaluations.append({
                        "rank": event_data.get('rank', i + 1),
                        "character": event_data.get('character', 'Unknown'),
                        "event": event_data.get('event', ''),
                        "original_score": event_data.get('score', 0),
                        "is_relevant": False,
                        "explanation": f"Evaluation failed: {e}",
                        "evaluation_text": ""
                    })
                    irrelevant_count += 1
            
            return {
                "success": True,
                "question": question,
                "standard_answer": standard_answer,
                "total_events": len(retrieved_events),
                "event_evaluations": event_evaluations,
                "relevant_count": relevant_count,
                "irrelevant_count": irrelevant_count,
                "relevance_rate": relevant_count / len(retrieved_events) if retrieved_events else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate retrieved events: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "standard_answer": standard_answer,
                "total_events": len(retrieved_events) if retrieved_events else 0,
                "event_evaluations": [],
                "relevant_count": 0,
                "irrelevant_count": 0,
                "relevance_rate": 0
            }

    def analyze_answer_errors(self, question: str, generated_answer: str, standard_answer: str, retrieved_events: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze why a generated answer is incorrect and provide detailed reasoning"""
        try:
            # Prepare retrieved events context
            events_context = ""
            if retrieved_events:
                events_context = "\nRetrieved Events Used:\n"
                for i, event_data in enumerate(retrieved_events[:5]):  # Limit to top 5 events
                    character = event_data.get('character', 'Unknown')
                    event_text = event_data.get('event', '')
                    score = event_data.get('score', 0)
                    events_context += f"{i+1}. [{character}] {event_text} (score: {score:.3f})\n"
            
            # Create error analysis prompt
            error_analysis_prompt = f"""You are an expert evaluator tasked with analyzing why an AI-generated answer is incorrect.

Question: {question}

Generated Answer: {generated_answer}

Standard Answer: {standard_answer}

{events_context}

Instructions:
1. Compare the generated answer with the standard answer
2. Identify the specific errors or omissions in the generated answer
3. Analyze potential reasons for these errors (e.g., insufficient information, misinterpretation, irrelevant events)
4. Provide recommendations for improvement

Response format:
Error Type: [Type of error - e.g., Missing Information, Incorrect Facts, Misinterpretation, etc.]
Specific Issues: [List the specific problems with the generated answer]
Root Cause: [Why do you think these errors occurred?]
Missing Information: [What key information was missing or ignored?]
Recommendations: [How could the answer be improved?]"""

            # Get analysis from LLM
            messages = [{"role": "user", "content": error_analysis_prompt}]
            llm_response = self.llm_client.chat_completion(messages, max_tokens=800, temperature=0.2)
            
            if not llm_response.success:
                raise Exception(f"LLM error analysis failed: {llm_response.error}")
                
            analysis_text = llm_response.content.strip()
            
            # Parse the analysis result
            parsed_analysis = {}
            current_section = None
            current_content = []
            
            lines = analysis_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.endswith(':') and any(section in line for section in [
                    'Error Type', 'Specific Issues', 'Root Cause', 'Missing Information', 'Recommendations'
                ]):
                    # Save previous section
                    if current_section and current_content:
                        parsed_analysis[current_section] = ' '.join(current_content).strip()
                    
                    # Start new section
                    current_section = line[:-1].lower().replace(' ', '_')
                    current_content = []
                elif current_section and line:
                    current_content.append(line)
            
            # Save last section
            if current_section and current_content:
                parsed_analysis[current_section] = ' '.join(current_content).strip()
            
            return {
                "success": True,
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "error_type": parsed_analysis.get('error_type', 'Unknown'),
                "specific_issues": parsed_analysis.get('specific_issues', ''),
                "root_cause": parsed_analysis.get('root_cause', ''),
                "missing_information": parsed_analysis.get('missing_information', ''),
                "recommendations": parsed_analysis.get('recommendations', ''),
                "full_analysis": analysis_text,
                "events_used": len(retrieved_events) if retrieved_events else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze answer errors: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "error_type": "Analysis Failed",
                "specific_issues": f"Error analysis failed: {e}",
                "root_cause": "System error during analysis",
                "missing_information": "",
                "recommendations": "Fix system error and retry analysis",
                "full_analysis": "",
                "events_used": len(retrieved_events) if retrieved_events else 0
            }

    def comprehensive_evaluation(self, question: str, generated_answer: str, standard_answer: str, retrieved_events: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform comprehensive evaluation including answer accuracy, event relevance, and error analysis"""
        try:
            # 1. Evaluate answer accuracy
            accuracy_result = self.evaluate_answer_accuracy(question, generated_answer, standard_answer)
            
            # 2. Evaluate retrieved events (if provided)
            events_result = None
            if retrieved_events:
                events_result = self.evaluate_retrieved_events(question, standard_answer, retrieved_events)
            
            # 3. Analyze errors (if answer is incorrect)
            error_analysis = None
            if not accuracy_result.get('is_correct', False):
                error_analysis = self.analyze_answer_errors(question, generated_answer, standard_answer, retrieved_events)
            
            # Compile comprehensive report
            return {
                "success": True,
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "timestamp": datetime.now().isoformat(),
                
                # Answer accuracy evaluation
                "answer_accuracy": {
                    "is_correct": accuracy_result.get('is_correct', False),
                    "explanation": accuracy_result.get('explanation', ''),
                    "success": accuracy_result.get('success', False)
                },
                
                # Retrieved events evaluation
                "events_evaluation": {
                    "total_events": events_result.get('total_events', 0) if events_result else 0,
                    "relevant_count": events_result.get('relevant_count', 0) if events_result else 0,
                    "irrelevant_count": events_result.get('irrelevant_count', 0) if events_result else 0,
                    "relevance_rate": events_result.get('relevance_rate', 0) if events_result else 0,
                    "event_details": events_result.get('event_evaluations', []) if events_result else [],
                    "success": events_result.get('success', False) if events_result else False
                },
                
                # Error analysis (only if answer is incorrect)
                "error_analysis": {
                    "performed": error_analysis is not None,
                    "error_type": error_analysis.get('error_type', '') if error_analysis else '',
                    "specific_issues": error_analysis.get('specific_issues', '') if error_analysis else '',
                    "root_cause": error_analysis.get('root_cause', '') if error_analysis else '',
                    "missing_information": error_analysis.get('missing_information', '') if error_analysis else '',
                    "recommendations": error_analysis.get('recommendations', '') if error_analysis else '',
                    "success": error_analysis.get('success', False) if error_analysis else False
                },
                
                # Summary statistics
                "summary": {
                    "overall_correct": accuracy_result.get('is_correct', False),
                    "events_processed": len(retrieved_events) if retrieved_events else 0,
                    "relevant_events_found": events_result.get('relevant_count', 0) if events_result else 0,
                    "error_analysis_available": error_analysis is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to perform comprehensive evaluation: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "generated_answer": generated_answer,
                "standard_answer": standard_answer,
                "timestamp": datetime.now().isoformat(),
                "answer_accuracy": {"success": False, "is_correct": False},
                "events_evaluation": {"success": False, "total_events": 0},
                "error_analysis": {"success": False, "performed": False},
                "summary": {"overall_correct": False, "events_processed": 0, "relevant_events_found": 0}
            }

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific evaluation tool by name"""
        tool_methods = {
            "evaluate_answer_accuracy": self.evaluate_answer_accuracy,
            "evaluate_retrieved_events": self.evaluate_retrieved_events,
            "analyze_answer_errors": self.analyze_answer_errors,
            "comprehensive_evaluation": self.comprehensive_evaluation
        }
        
        if tool_name not in tool_methods:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(tool_methods.keys())
            }
        
        try:
            return tool_methods[tool_name](**kwargs)
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "arguments": kwargs
            }

    def execute(self, user_message: str, max_iterations: int = 10) -> Dict[str, Any]:
        """Execute user message with function calling support"""
        try:
            tools = self.get_available_tools()
            messages = [{"role": "user", "content": user_message}]
            
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                
                # Get response from LLM with tools
                llm_response = self.llm_client.chat_completion(
                    messages=messages,
                    tools=tools,
                    max_tokens=4000,
                    temperature=0.1
                )
                
                # Check if LLM response was successful
                if not llm_response.success:
                    raise Exception(f"LLM call failed: {llm_response.error}")
                
                # Convert LLMResponse to dict format expected by the rest of the code
                response = {
                    "content": llm_response.content or "",
                    "tool_calls": llm_response.tool_calls if llm_response.tool_calls else None
                }
                
                # Add assistant message
                assistant_message = {
                    "role": "assistant", 
                    "content": response.get("content", "")
                }
                
                # Only add tool_calls if they exist and are not empty
                if response.get("tool_calls"):
                    assistant_message["tool_calls"] = response["tool_calls"]
                
                messages.append(assistant_message)
                
                # Process tool calls if any
                if response.get("tool_calls"):
                    for tool_call in response["tool_calls"]:
                        try:
                            # Handle different possible tool call formats
                            if hasattr(tool_call, 'function'):
                                # OpenAI API format
                                tool_name = tool_call.function.name
                                arguments = json.loads(tool_call.function.arguments)
                                tool_call_id = tool_call.id
                            elif isinstance(tool_call, dict):
                                # Dict format
                                tool_name = tool_call["function"]["name"]
                                arguments = json.loads(tool_call["function"]["arguments"])
                                tool_call_id = tool_call["id"]
                            else:
                                raise Exception(f"Unknown tool call format: {type(tool_call)}")
                            
                            # Execute tool
                            result = self.execute_tool(tool_name, **arguments)
                            
                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(result, indent=2)
                            })
                            
                        except Exception as e:
                            logger.error(f"Error processing tool call: {e}")
                            
                            # Add error response
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id if 'tool_call_id' in locals() else "unknown",
                                "content": json.dumps({
                                    "success": False,
                                    "error": f"Tool execution failed: {str(e)}"
                                }, indent=2)
                            })
                else:
                    # No more tool calls, we're done
                    break
            
            return {
                "success": True,
                "final_response": response.get("content", ""),
                "iterations": iteration,
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"Failed to execute user message: {e}")
            return {
                "success": False,
                "error": str(e),
                "final_response": "",
                "iterations": 0,
                "messages": []
            }


# Example usage and testing
if __name__ == "__main__":
    # Initialize the evaluate agent
    agent = EvaluateAgent()
    
    # Example evaluation
    question = "What is Caroline's favorite restaurant?"
    generated_answer = "Caroline likes Italian food."
    standard_answer = "Caroline's favorite restaurant is Mario's Italian Bistro."
    retrieved_events = [
        {
            "character": "Caroline",
            "event": "Caroline went to Mario's Italian Bistro for dinner last week",
            "score": 0.85,
            "rank": 1
        },
        {
            "character": "Caroline", 
            "event": "Caroline mentioned she loves pasta",
            "score": 0.72,
            "rank": 2
        }
    ]
    
    # Perform comprehensive evaluation
    result = agent.comprehensive_evaluation(
        question=question,
        generated_answer=generated_answer,
        standard_answer=standard_answer,
        retrieved_events=retrieved_events
    )
    
    print(json.dumps(result, indent=2)) 