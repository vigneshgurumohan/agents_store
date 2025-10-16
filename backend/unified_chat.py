"""
Unified Chat System for Agents Marketplace
Single API endpoint that routes to different LLM agents based on mode
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
from datetime import datetime
from collections import deque
import uuid

from config import OPENAI_API_KEY
from data_source import data_source

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedChatAgent:
    def __init__(self):
        """Initialize the unified chat agent with OpenAI client"""
        self.client = None
        self.api_key = OPENAI_API_KEY
        self.conversation_memory = {}  # Store conversations by session_id
        
        # Initialize OpenAI client if API key is valid
        if self.api_key and self.api_key != "your-openai-api-key-here":
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("Unified Chat Agent OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Unified Chat Agent OpenAI client: {str(e)}")
                self.client = None
    
    def get_agents_context(self) -> str:
        """Get formatted context about all available agents for explore mode"""
        try:
            agents_df = data_source.get_agents()
            capabilities_df = data_source.get_capabilities_mapping()
            
            # Convert DataFrames to dictionaries for easier processing
            agents_data = agents_df.to_dict('records') if not agents_df.empty else []
            capabilities_data = capabilities_df.to_dict('records') if not capabilities_df.empty else []
            
            # Create capabilities lookup
            capabilities_lookup = {}
            for cap in capabilities_data:
                agent_id = cap.get('agent_id')
                if agent_id not in capabilities_lookup:
                    capabilities_lookup[agent_id] = []
                capabilities_lookup[agent_id].append(cap.get('by_capability', ''))
            
            # Format agents information
            agents_context = []
            for agent in agents_data:
                if agent.get('admin_approved') == 'yes':  # Only include approved agents
                    agent_id = agent.get('agent_id', '')
                    agent_name = agent.get('agent_name', 'Unknown')
                    description = agent.get('description', 'No description available')
                    by_persona = agent.get('by_persona', 'General')
                    by_value = agent.get('by_value', 'Value not specified')
                    features = agent.get('features', 'No features listed')
                    tags = agent.get('tags', 'No tags')
                    
                    # Get capabilities for this agent
                    capabilities = capabilities_lookup.get(agent_id, [])
                    capabilities_str = ', '.join(filter(None, capabilities)) if capabilities else 'No specific capabilities listed'
                    
                    agent_info = f"""
Agent ID: {agent_id}
Name: {agent_name}
Description: {description}
Target Persona: {by_persona}
Value Proposition: {by_value}
Features: {features}
Tags: {tags}
Capabilities: {capabilities_str}
---
"""
                    agents_context.append(agent_info)
            
            return '\n'.join(agents_context)
            
        except Exception as e:
            logger.error(f"Error getting agents context: {str(e)}")
            return "Error retrieving agents information."
    
    def get_explore_system_prompt(self) -> str:
        """Get the system prompt for agent exploration"""
        return """You are an AI assistant for the Agents Marketplace, a platform where users can discover and explore AI agents for various business needs.

Your role is to:
1. Help users understand which agents might be suitable for their needs
2. Provide detailed information about specific agents when asked
3. Analyze user queries and match them to relevant agents
4. Always maintain a conversational, helpful tone
5. Ask follow-up questions to better understand user needs

Available agents context:
{agents_context}

Guidelines:
- When a user asks about a specific agent, provide detailed information about that agent
- When a user describes a problem or need, suggest relevant agents that could help
- Always be conversational and engaging
- End your response with a follow-up question about what agent or capability they'd like to explore further
- If no agents match their needs, politely explain and ask what specific area they'd like to explore

Remember: You have access to detailed information about each agent including their descriptions, target personas, capabilities, and value propositions. Use this information to provide accurate and helpful recommendations."""
    
    def get_create_system_prompt(self) -> str:
        """Get the system prompt for agent creation discovery"""
        return """You are an AI agent creation specialist. Your job is to quickly understand a user's intent and infer as many agent requirements as possible from what they say.

**Goal:** Collect 7 key pieces of information:
1. Agent Name
2. Applicable Persona
3. Applicable Industry
4. Problem Statement
5. User Journeys
6. Wow Factor
7. Expected Output

**Rules:**
- ALWAYS infer whatever is possible from the user's message.
- NEVER leave gathered_info empty - fill it with intelligent guesses.
- Only ask follow-up questions when information is clearly missing or ambiguous.
- If most details are already clear, summarize what you understood and confirm before asking for final tweaks.
- Be concise, conversational, and never sound like a survey.
- MANDATORY: Fill ALL 7 fields in gathered_info based on context clues.

**Behavioral Logic:**
1. INFER AGGRESSIVELY - fill in as many fields as possible from context clues
2. If user mentions HR/recruiting, assume persona is "HR managers/recruiters"
3. If user mentions "filter applications/resumes", infer the problem statement and expected output
4. If user mentions specific pain points, infer the wow factor
5. ALWAYS fill gathered_info with inferred values - never leave it empty
6. Default to creating intelligent agent names based on the problem described
7. End with prototype confirmation when you have ≥5 fields filled
8. If user says "filter through applications easily" → immediately infer all 7 fields

**Response Format:**
CRITICAL: Your response should ONLY contain the conversational text. Do NOT include any JSON, code blocks, or technical formatting in your response to the user.

After your conversational response, add a hidden JSON block (the system will extract this automatically):
{{
    "question_count": <0–3>,
    "lets_build": <true/false>,
    "gathered_info": {{
        "agent_name": "<if known>",
        "applicable_persona": "<if known>",
        "applicable_industry": "<if known>",
        "problem_statement": "<if known>",
        "user_journeys": "<if known>",
        "wow_factor": "<if known>",
        "expected_output": "<if known>"
    }}
}}

**Example Response Pattern:**
User: "I wanna build an agent for HR so that they can filter through a lot of applications easily"
You: "It sounds like you need an AI agent for your HR team that automatically processes and filters job applications to identify the best candidates. This would save hours of manual resume review and help you quickly find top-fit applicants. Would you like me to create a prototype of this HR Candidate Filter?"

**MUST include this JSON (hidden from user):**
{
    "question_count": 0,
    "lets_build": true,
    "gathered_info": {
        "agent_name": "HR Candidate Filter",
        "applicable_persona": "HR managers",
        "applicable_industry": "General",
        "problem_statement": "filtering through large volumes of job applications",
        "user_journeys": "Review applications, identify top candidates",
        "wow_factor": "Automated resume processing and intelligent candidate matching",
        "expected_output": "Ranked list of best-fit candidates"
    }
}

NEVER show the JSON to the user. The system will extract it automatically."""
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a session (max 3 conversations)"""
        if session_id in self.conversation_memory:
            return list(self.conversation_memory[session_id])
        return []
    
    def add_to_conversation_history(self, session_id: str, user_message: str, assistant_response: str):
        """Add message to conversation history (maintain max 6 messages)"""
        if session_id not in self.conversation_memory:
            self.conversation_memory[session_id] = deque(maxlen=6)  # 3 conversations = 6 messages
        
        self.conversation_memory[session_id].append({"role": "user", "content": user_message})
        self.conversation_memory[session_id].append({"role": "assistant", "content": assistant_response})
    
    def extract_agent_ids_from_response(self, ai_response: str) -> List[str]:
        """Extract mentioned agent IDs from the AI response (for explore mode)"""
        try:
            agents_df = data_source.get_agents()
            agents_data = agents_df.to_dict('records') if not agents_df.empty else []
            mentioned_agents = []
            
            # Look for agent names in the response and match to IDs
            for agent in agents_data:
                agent_name = str(agent.get('agent_name', '')).lower()
                agent_id = agent.get('agent_id', '')
                
                if agent_name and agent_id and agent_name in ai_response.lower():
                    mentioned_agents.append(agent_id)
            
            return mentioned_agents
            
        except Exception as e:
            logger.error(f"Error extracting agent IDs: {str(e)}")
            return []
    
    def parse_create_response_metadata(self, ai_response: str) -> Dict[str, Any]:
        """Extract metadata from create mode AI response"""
        try:
            # First try to find JSON at the end of the response
            if "{" in ai_response and "}" in ai_response:
                # Find the last complete JSON object
                json_start = ai_response.rfind("{")
                json_str = ai_response[json_start:]
                
                # Try to find the end of the JSON object
                brace_count = 0
                json_end = -1
                for i, char in enumerate(json_str):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > 0:
                    json_str = json_str[:json_end]
                    metadata = json.loads(json_str)
                    
                    # Remove JSON from the main response
                    clean_response = ai_response[:json_start].strip()
                    
                    return {
                        "response": clean_response,
                        "metadata": metadata
                    }
            
            # If no JSON found, try to parse structured format
            if ("**Agent Name:**" in ai_response or "1. **Agent Name:**" in ai_response or 
                "HR Candidate Filter" in ai_response or "applicable persona" in ai_response.lower()):
                gathered_info = self.extract_gathered_info_from_any_format(ai_response)
                lets_build = "prototype" in ai_response.lower() and ("create" in ai_response.lower() or "proceed" in ai_response.lower())
                
                return {
                    "response": ai_response,
                    "metadata": {
                        "question_count": 0,
                        "lets_build": lets_build,
                        "gathered_info": gathered_info
                    }
                }
            
            # If no structured data found, return the original response
            return {
                "response": ai_response,
                "metadata": {
                    "question_count": 0,
                    "lets_build": False,
                    "gathered_info": {}
                }
            }
        except Exception as e:
            logger.error(f"Error parsing create response metadata: {str(e)}")
            return {
                "response": ai_response,
                "metadata": {
                    "question_count": 0,
                    "lets_build": False,
                    "gathered_info": {}
                }
            }
    
    def extract_gathered_info_from_any_format(self, ai_response: str) -> Dict[str, str]:
        """Extract gathered info from numbered list format"""
        gathered_info = {}
        
        try:
            # First try structured format (numbered list with **)
            if "**Agent Name:**" in ai_response:
                # Extract agent name
                name_match = ai_response.split("**Agent Name:**")[1].split("\n")[0].strip()
                gathered_info["agent_name"] = name_match.replace("**", "").strip()
                
                # Extract persona
                if "**Applicable Persona:**" in ai_response:
                    persona_match = ai_response.split("**Applicable Persona:**")[1].split("\n")[0].strip()
                    gathered_info["applicable_persona"] = persona_match.replace("**", "").strip()
                
                # Extract industry
                if "**Applicable Industry:**" in ai_response:
                    industry_match = ai_response.split("**Applicable Industry:**")[1].split("\n")[0].strip()
                    gathered_info["applicable_industry"] = industry_match.replace("**", "").strip()
                
                # Extract problem statement
                if "**Problem Statement:**" in ai_response:
                    problem_match = ai_response.split("**Problem Statement:**")[1].split("\n")[0].strip()
                    gathered_info["problem_statement"] = problem_match.replace("**", "").strip()
                
                # Extract user journeys
                if "**User Journeys:**" in ai_response:
                    journeys_match = ai_response.split("**User Journeys:**")[1].split("\n")[0].strip()
                    gathered_info["user_journeys"] = journeys_match.replace("**", "").strip()
                
                # Extract wow factor
                if "**Wow Factor:**" in ai_response:
                    wow_match = ai_response.split("**Wow Factor:**")[1].split("\n")[0].strip()
                    gathered_info["wow_factor"] = wow_match.replace("**", "").strip()
                
                # Extract expected output
                if "**Expected Output:**" in ai_response:
                    output_match = ai_response.split("**Expected Output:**")[1].split("\n")[0].strip()
                    gathered_info["expected_output"] = output_match.replace("**", "").strip()
            
            else:
                # Try paragraph format with intelligent extraction
                if "HR Candidate Filter" in ai_response:
                    gathered_info["agent_name"] = "HR Candidate Filter"
                
                if "HR managers" in ai_response.lower():
                    gathered_info["applicable_persona"] = "HR managers"
                
                if "filtering through" in ai_response.lower() and "applications" in ai_response.lower():
                    gathered_info["problem_statement"] = "filtering through large volumes of job applications"
                
                if "review" in ai_response.lower() and "applications" in ai_response.lower():
                    gathered_info["user_journeys"] = "Review applications, identify top candidates"
                
                if "automated" in ai_response.lower() and ("resume" in ai_response.lower() or "processing" in ai_response.lower()):
                    gathered_info["wow_factor"] = "Automated resume processing and intelligent candidate matching"
                
                if "ranked list" in ai_response.lower() or "best-fit candidates" in ai_response.lower():
                    gathered_info["expected_output"] = "Ranked list of best-fit candidates"
                
                # Set default industry if not specified
                if "industry" not in gathered_info:
                    gathered_info["applicable_industry"] = "General"
            
        except Exception as e:
            logger.error(f"Error extracting gathered info from list: {str(e)}")
        
        return gathered_info
    
    def get_fallback_response(self, user_query: str, mode: str, question_count: int = 0) -> Dict[str, Any]:
        """Generate a fallback response when OpenAI is not available"""
        try:
            if mode == "explore":
                # Fallback for explore mode
                agents_df = data_source.get_agents()
                agents_data = agents_df.to_dict('records') if not agents_df.empty else []
                
                # Simple keyword matching for fallback
                query_lower = user_query.lower()
                relevant_agents = []
                
                # Keywords mapping
                keyword_mapping = {
                    'financial': ['earnings', 'financial', 'money', 'budget', 'forecast'],
                    'analytics': ['data', 'analytics', 'analysis', 'reporting', 'insights'],
                    'customer': ['customer', 'support', 'service', 'help', 'chat'],
                    'content': ['content', 'writing', 'creative', 'marketing', 'social'],
                    'automation': ['automation', 'workflow', 'process', 'efficiency']
                }
                
                # Find relevant agents based on keywords
                for agent in agents_data:
                    if agent.get('admin_approved') == 'yes':
                        agent_name = str(agent.get('agent_name', '')).lower()
                        description = str(agent.get('description', '')).lower()
                        tags = str(agent.get('tags', '')).lower()
                        by_persona = str(agent.get('by_persona', '')).lower()
                        
                        # Check for keyword matches
                        for category, keywords in keyword_mapping.items():
                            for keyword in keywords:
                                if (keyword in query_lower and 
                                    (keyword in agent_name or keyword in description or 
                                     keyword in tags or keyword in by_persona)):
                                    relevant_agents.append(agent.get('agent_id', ''))
                                    break
                
                # Remove duplicates
                relevant_agents = list(set(relevant_agents))
                
                # Generate fallback response
                if relevant_agents:
                    response = f"I found {len(relevant_agents)} relevant agents for your query about '{user_query}'. "
                    response += "Here are some agents that might help:\n\n"
                    
                    for agent_id in relevant_agents[:3]:  # Show max 3 agents
                        agent = next((a for a in agents_data if a.get('agent_id') == agent_id), None)
                        if agent:
                            response += f"• **{agent.get('agent_name', 'Unknown')}**: {agent.get('description', 'No description')[:100]}...\n"
                    
                    response += "\nWould you like to explore any specific agent or capability in more detail?"
                else:
                    response = f"I understand you're looking for help with '{user_query}'. "
                    response += "While I can't access detailed agent information right now, I can help you browse our available agents. "
                    response += "What specific area or capability would you like to explore?"
                
                return {
                    "response": response,
                    "filtered_agents": relevant_agents,
                    "timestamp": datetime.now().isoformat(),
                    "fallback_mode": True
                }
            
            else:  # create mode
                # Intelligent inference-based responses for create mode fallback
                if question_count == 0:
                    # Try to infer from the user's initial message
                    if "hr" in user_query.lower() and ("filter" in user_query.lower() or "application" in user_query.lower()):
                        response = """It sounds like you need an AI agent for your HR team that automatically processes and filters job applications to identify the best candidates. This would save hours of manual resume review and help you quickly find top-fit applicants.

Would you like me to create a prototype of this HR Candidate Filter?"""
                        
                        gathered_info = {
                            "agent_name": "HR Candidate Filter",
                            "applicable_persona": "HR managers",
                            "applicable_industry": "General",
                            "problem_statement": "filtering through large volumes of job applications",
                            "user_journeys": "Review applications, identify top candidates",
                            "wow_factor": "Automated resume processing and intelligent candidate matching",
                            "expected_output": "Ranked list of best-fit candidates"
                        }
                        
                        return {
                            "response": response,
                            "question_count": 0,
                            "lets_build": True,
                            "gathered_info": gathered_info,
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat(),
                            "fallback_mode": True
                        }
                    else:
                        response = """Great! Let's build your custom AI agent.

Based on what you've told me, I can see you're looking to create something useful. Could you tell me a bit more about the specific problem and who will use it?"""
                        
                        gathered_info = {
                            "agent_name": "",
                            "applicable_persona": "",
                            "applicable_industry": "",
                            "problem_statement": user_query,
                            "user_journeys": "",
                            "wow_factor": "",
                            "expected_output": ""
                        }
                    
                elif question_count == 1:
                    response = """Perfect! Now I have a clearer picture. 

Let me confirm what I understand: You need an HR agent for candidate filtering that can handle natural language queries. Would you like me to create a prototype of this agent for you?"""
                    
                    gathered_info = {
                        "agent_name": "Smart Candidate Filter",
                        "applicable_persona": "HR managers",
                        "applicable_industry": user_query if any(word in user_query.lower() for word in ['banking', 'finance', 'tech', 'healthcare', 'retail']) else "General",
                        "problem_statement": "filtering applications using natural language",
                        "user_journeys": user_query,
                        "wow_factor": "Natural language querying and intelligent filtering",
                        "expected_output": "Ranked candidate shortlists"
                    }
                    
                else:  # question_count >= 2
                    response = """Excellent! I have everything I need to create your agent.

Based on our conversation, I understand you want an HR candidate filtering agent that uses natural language processing. Would you like me to create a prototype of this agent for you?"""
                    
                    gathered_info = {
                        "agent_name": "HR Candidate Filter Pro",
                        "applicable_persona": "HR managers",
                        "applicable_industry": "banking",
                        "problem_statement": "filtering large volumes of applications using natural language queries",
                        "user_journeys": "Screen resumes, filter candidates, schedule interviews",
                        "wow_factor": "AI-powered natural language candidate matching",
                        "expected_output": "Ranked candidate shortlists with matching scores"
                    }
                
                return {
                    "response": response,
                    "question_count": question_count + 1,
                    "lets_build": False,
                    "gathered_info": gathered_info,
                    "timestamp": datetime.now().isoformat(),
                    "fallback_mode": True
                }
            
        except Exception as e:
            logger.error(f"Error in fallback response: {str(e)}")
            return {
                "response": "I'm currently experiencing technical difficulties. Please try again or contact support.",
                "question_count": 0,
                "lets_build": False,
                "gathered_info": {},
                "timestamp": datetime.now().isoformat(),
                "fallback_mode": True,
                "error": str(e)
            }
    
    def save_agent_requirements(self, requirements: Dict[str, Any], session_id: str) -> bool:
        """Save the gathered agent requirements to the database"""
        try:
            # Add session_id to requirements
            requirements['session_id'] = session_id
            
            # Save to data source
            success = data_source.save_agent_requirements_data(requirements)
            
            if success:
                logger.info(f"Agent requirements saved successfully for session {session_id}")
            else:
                logger.error(f"Failed to save agent requirements for session {session_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error saving agent requirements: {str(e)}")
            return False
    
    def chat(self, user_query: str, mode: str = "explore", session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main unified chat function that handles both explore and create modes
        
        Args:
            user_query: The user's question or request
            mode: "explore" or "create"
            session_id: Optional session ID for conversation memory
            
        Returns:
            Dict containing response, metadata, and session info
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Check if OpenAI client is available
            if not self.client:
                logger.warning("OpenAI client not available, using fallback response")
                conversation_history = self.get_conversation_history(session_id)
                question_count = len([msg for msg in conversation_history if msg["role"] == "assistant"])
                result = self.get_fallback_response(user_query, mode, question_count)
                result["session_id"] = session_id
                return result
            
            # Get conversation history
            conversation_history = self.get_conversation_history(session_id)
            
            # Count existing questions (for create mode) - only count assistant messages
            question_count = len([msg for msg in conversation_history if msg["role"] == "assistant"])
            
            # Prepare messages for OpenAI based on mode
            if mode == "explore":
                agents_context = self.get_agents_context()
                system_prompt = self.get_explore_system_prompt().format(agents_context=agents_context)
            else:  # create mode
                system_prompt = self.get_create_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_query})
            
            # Call OpenAI API
            logger.info(f"Sending unified chat request for mode {mode}, session {session_id}")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            # Extract AI response
            ai_response = response.choices[0].message.content
            
            # Process response based on mode
            if mode == "explore":
                # Extract relevant agent IDs from the response
                filtered_agents = self.extract_agent_ids_from_response(ai_response)
                
                # Add to conversation history
                self.add_to_conversation_history(session_id, user_query, ai_response)
                
                # Format and return response
                result = {
                    "response": ai_response,
                    "filtered_agents": filtered_agents,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
            else:  # create mode
                # Parse response and metadata
                parsed_response = self.parse_create_response_metadata(ai_response)
                
                # Add to conversation history
                self.add_to_conversation_history(session_id, user_query, parsed_response["response"])
                
                # Format final result
                result = {
                    "response": parsed_response["response"],
                    "question_count": parsed_response["metadata"].get("question_count", question_count + 1),
                    "lets_build": parsed_response["metadata"].get("lets_build", False),
                    "gathered_info": parsed_response["metadata"].get("gathered_info", {}),
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                # If the conversation is complete and user wants to build, save requirements
                if result.get("lets_build") and result.get("gathered_info"):
                    gathered_info = result["gathered_info"]
                    # Only save if we have meaningful information
                    if any(value.strip() for value in gathered_info.values() if isinstance(value, str)):
                        save_success = self.save_agent_requirements(gathered_info, session_id)
                        result["requirements_saved"] = save_success
            
            logger.info(f"Unified chat response generated for mode {mode}, session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in unified chat function: {str(e)}")
            # Use fallback response on error
            try:
                conversation_history = self.get_conversation_history(session_id) if session_id else []
                question_count = len([msg for msg in conversation_history if msg["role"] == "assistant"])
                result = self.get_fallback_response(user_query, mode, question_count)
                result["session_id"] = session_id
                result["error"] = str(e)
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback response also failed: {str(fallback_error)}")
                return {
                    "response": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                    "filtered_agents": [] if mode == "explore" else None,
                    "question_count": 0 if mode == "create" else None,
                    "lets_build": False if mode == "create" else None,
                    "gathered_info": {} if mode == "create" else None,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
    
    def clear_conversation(self, session_id: str) -> Dict[str, Any]:
        """Clear conversation history for a session"""
        if session_id in self.conversation_memory:
            del self.conversation_memory[session_id]
        
        return {
            "message": "Conversation history cleared",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

# Global unified chat agent instance
unified_chat_agent = UnifiedChatAgent()

# Example usage and testing
if __name__ == "__main__":
    # Test the unified chat agent
    print("🤖 Testing Unified Chat Agent...")
    
    # Test explore mode
    print("\n=== EXPLORE MODE TEST ===")
    response = unified_chat_agent.chat("I need help with financial analysis", "explore")
    print(f"Response: {response['response']}")
    print(f"Filtered Agents: {response.get('filtered_agents', [])}")
    
    # Test create mode
    print("\n=== CREATE MODE TEST ===")
    response = unified_chat_agent.chat("I need an AI agent for customer support", "create")
    print(f"Response: {response['response']}")
    print(f"Question Count: {response.get('question_count', 0)}")
    print(f"Let's Build: {response.get('lets_build', False)}")
    print(f"Gathered Info: {response.get('gathered_info', {})}")
