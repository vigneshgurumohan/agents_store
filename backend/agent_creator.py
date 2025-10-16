"""
Agent Creation Discovery System
Helps users define requirements for custom AI agents through conversational discovery
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

class AgentCreator:
    def __init__(self):
        """Initialize the agent creation discovery system"""
        self.client = None
        self.api_key = OPENAI_API_KEY
        self.conversation_memory = {}  # Store conversations by session_id
        
        # Initialize OpenAI client if API key is valid
        if self.api_key and self.api_key != "your-openai-api-key-here":
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("Agent Creator OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Agent Creator OpenAI client: {str(e)}")
                self.client = None
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent creation discovery"""
        return """You are an expert AI agent creation specialist and business analyst. Your role is to help users discover and define requirements for custom AI agents through a conversational discovery process.

Your goal is to collect comprehensive information to build a custom AI agent by asking intelligent, probing questions. You need to gather:

1. **Agent Name** - A clear, descriptive name for the agent
2. **Applicable Persona** - Who will use this agent (role, department, skill level)
3. **Applicable Industry** - Industry/sector where this agent will be used
4. **Problem Statement** - Clear definition of the business problem to solve
5. **User Journeys** - Key workflows and processes the agent will support
6. **Wow Factor** - Unique value proposition and differentiators
7. **Expected Output** - What the agent should deliver/produce

**Discovery Rules:**
- Ask maximum 3 strategic questions per conversation
- Each question should gather multiple pieces of information
- Be conversational and engaging, not robotic
- Build on previous answers to ask deeper questions
- After 3 questions, synthesize the information and propose a solution
- Ask for confirmation if this is what they want to build
- Only end with "Great, let's build it!" when you have all required information AND confirmation

**Question Strategy:**
- Question 1: Focus on problem understanding, persona, and industry context
- Question 2: Dive deeper into workflows, processes, and expected outcomes
- Question 3: Explore unique value, differentiators, and success metrics

**Response Format:**
Always end your response with a JSON object containing:
{
    "question_count": <number>,
    "lets_build": <true/false>,
    "gathered_info": {
        "agent_name": "<if known>",
        "applicable_persona": "<if known>",
        "applicable_industry": "<if known>",
        "problem_statement": "<if known>",
        "user_journeys": "<if known>",
        "wow_factor": "<if known>",
        "expected_output": "<if known>"
    }
}

Remember: You're not just collecting information - you're helping them think through their requirements and discover what they really need."""
    
    def get_fallback_response(self, user_query: str, question_count: int = 0) -> Dict[str, Any]:
        """Generate a fallback response when OpenAI is not available"""
        try:
            # Simple template-based responses for fallback
            if question_count == 0:
                response = """I'd love to help you create a custom AI agent! Let me understand your needs better.

**First, tell me about the challenge you're facing:**
- What specific problem are you trying to solve?
- Who in your organization would be using this agent?
- What industry or domain does this relate to?

This will help me understand the foundation for your custom agent."""
                
                gathered_info = {
                    "agent_name": "",
                    "applicable_persona": "",
                    "applicable_industry": "",
                    "problem_statement": "",
                    "user_journeys": "",
                    "wow_factor": "",
                    "expected_output": ""
                }
                
            elif question_count == 1:
                response = """Great start! Now let's dive deeper into the workflows and processes.

**Tell me more about the day-to-day processes:**
- What are the key steps in the current workflow?
- What tasks take the most time or cause the most friction?
- What would success look like? What specific outputs or results do you need?

This helps me understand how the agent will fit into your operations."""
                
                gathered_info = {
                    "agent_name": "",
                    "applicable_persona": "",
                    "applicable_industry": "",
                    "problem_statement": user_query,
                    "user_journeys": "",
                    "wow_factor": "",
                    "expected_output": ""
                }
                
            else:  # question_count >= 2
                response = """Perfect! Now let's define what makes this agent special.

**Final question about your vision:**
- What would make this agent truly valuable and unique?
- What's the "wow factor" that would get people excited to use it?
- What would you call this agent, and what should it deliver?

Based on what you've shared, I think we can build something amazing together!"""
                
                gathered_info = {
                    "agent_name": "",
                    "applicable_persona": "",
                    "applicable_industry": "",
                    "problem_statement": user_query,
                    "user_journeys": "",
                    "wow_factor": "",
                    "expected_output": ""
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
    
    def parse_response_metadata(self, ai_response: str) -> Dict[str, Any]:
        """Extract metadata from AI response"""
        try:
            # Look for JSON at the end of the response
            if "{" in ai_response and "}" in ai_response:
                json_start = ai_response.rfind("{")
                json_str = ai_response[json_start:]
                metadata = json.loads(json_str)
                
                # Remove JSON from the main response
                clean_response = ai_response[:json_start].strip()
                return {
                    "response": clean_response,
                    "metadata": metadata
                }
            else:
                return {
                    "response": ai_response,
                    "metadata": {
                        "question_count": 0,
                        "lets_build": False,
                        "gathered_info": {}
                    }
                }
        except Exception as e:
            logger.error(f"Error parsing response metadata: {str(e)}")
            return {
                "response": ai_response,
                "metadata": {
                    "question_count": 0,
                    "lets_build": False,
                    "gathered_info": {}
                }
            }
    
    def discover_agent_requirements(self, user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main discovery function for agent creation
        
        Args:
            user_query: The user's requirement or response
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
                result = self.get_fallback_response(user_query, question_count)
                result["session_id"] = session_id
                return result
            
            # Get conversation history
            conversation_history = self.get_conversation_history(session_id)
            
            # Count existing questions
            question_count = len([msg for msg in conversation_history if msg["role"] == "assistant"])
            
            # Prepare messages for OpenAI
            messages = [
                {"role": "system", "content": self.get_system_prompt()}
            ]
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_query})
            
            # Call OpenAI API
            logger.info(f"Sending agent creation discovery request for session {session_id}")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            # Extract AI response
            ai_response = response.choices[0].message.content
            
            # Parse response and metadata
            parsed_response = self.parse_response_metadata(ai_response)
            
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
            
            logger.info(f"Agent creation discovery response generated for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in agent creation discovery: {str(e)}")
            # Use fallback response on error
            try:
                conversation_history = self.get_conversation_history(session_id) if session_id else []
                question_count = len([msg for msg in conversation_history if msg["role"] == "assistant"])
                result = self.get_fallback_response(user_query, question_count)
                result["session_id"] = session_id
                result["error"] = str(e)
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback response also failed: {str(fallback_error)}")
                return {
                    "response": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                    "question_count": 0,
                    "lets_build": False,
                    "gathered_info": {},
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
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
    
    def clear_conversation(self, session_id: str) -> Dict[str, Any]:
        """Clear conversation history for a session"""
        if session_id in self.conversation_memory:
            del self.conversation_memory[session_id]
        
        return {
            "message": "Agent creation conversation history cleared",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

# Global agent creator instance
agent_creator = AgentCreator()

# Example usage and testing
if __name__ == "__main__":
    # Test the agent creator
    print("🤖 Testing Agent Creator...")
    
    # Test queries
    test_queries = [
        "I need an AI agent to help with customer support",
        "We have a lot of customer emails and it takes too long to respond",
        "We want something that can understand customer intent and suggest responses to our support team"
    ]
    
    session_id = "test_session"
    for i, query in enumerate(test_queries):
        print(f"\n👤 User: {query}")
        response = agent_creator.discover_agent_requirements(query, session_id)
        print(f"🤖 Creator: {response['response']}")
        print(f"📊 Question Count: {response['question_count']}")
        print(f"🏗️ Let's Build: {response['lets_build']}")
        print(f"📋 Gathered Info: {response['gathered_info']}")
        print("-" * 50)
