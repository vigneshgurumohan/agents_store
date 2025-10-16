"""
Chat Agent System for Agents Marketplace
Provides conversational AI assistance to help users discover and explore agents
"""

import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from datetime import datetime
from collections import deque
import uuid

from config import OPENAI_API_KEY
from data_source import data_source

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatAgent:
    def __init__(self):
        """Initialize the chat agent with OpenAI client"""
        self.client = None
        self.api_key = OPENAI_API_KEY
        self.conversation_memory = {}  # Store conversations by session_id
        
        # Initialize OpenAI client if API key is valid
        if self.api_key and self.api_key != "your-openai-api-key-here":
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
                self.client = None
        
    def get_agents_context(self) -> str:
        """Get formatted context about all available agents"""
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
    
    def get_fallback_response(self, user_query: str) -> Dict[str, Any]:
        """Generate a fallback response when OpenAI is not available"""
        try:
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
                    agent_name = agent.get('agent_name', '').lower()
                    description = agent.get('description', '').lower()
                    tags = agent.get('tags', '').lower()
                    by_persona = agent.get('by_persona', '').lower()
                    
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
            
        except Exception as e:
            logger.error(f"Error in fallback response: {str(e)}")
            return {
                "response": "I'm currently experiencing technical difficulties. Please try browsing our agents directly or contact support.",
                "filtered_agents": [],
                "timestamp": datetime.now().isoformat(),
                "fallback_mode": True,
                "error": str(e)
            }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI assistant"""
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
    
    def format_response(self, ai_response: str, filtered_agents: List[str]) -> Dict[str, Any]:
        """Format the response with filtered agents"""
        return {
            "response": ai_response,
            "filtered_agents": filtered_agents,
            "timestamp": datetime.now().isoformat()
        }
    
    def extract_agent_ids_from_response(self, ai_response: str) -> List[str]:
        """Extract mentioned agent IDs from the AI response"""
        try:
            agents_df = data_source.get_agents()
            agents_data = agents_df.to_dict('records') if not agents_df.empty else []
            mentioned_agents = []
            
            # Look for agent names in the response and match to IDs
            for agent in agents_data:
                agent_name = agent.get('agent_name', '').lower()
                agent_id = agent.get('agent_id', '')
                
                if agent_name and agent_id and agent_name in ai_response.lower():
                    mentioned_agents.append(agent_id)
            
            return mentioned_agents
            
        except Exception as e:
            logger.error(f"Error extracting agent IDs: {str(e)}")
            return []
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a session (max 3 conversations)"""
        if session_id in self.conversation_memory:
            return list(self.conversation_memory[session_id])
        return []
    
    def add_to_conversation_history(self, session_id: str, user_message: str, assistant_response: str):
        """Add message to conversation history (maintain max 3 conversations)"""
        if session_id not in self.conversation_memory:
            self.conversation_memory[session_id] = deque(maxlen=6)  # 3 conversations = 6 messages (user + assistant)
        
        self.conversation_memory[session_id].append({"role": "user", "content": user_message})
        self.conversation_memory[session_id].append({"role": "assistant", "content": assistant_response})
    
    def chat(self, user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main chat function that processes user queries and returns AI responses
        
        Args:
            user_query: The user's question or request
            session_id: Optional session ID for conversation memory
            
        Returns:
            Dict containing response, filtered_agents, and timestamp
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Check if OpenAI client is available
            if not self.client:
                logger.warning("OpenAI client not available, using fallback response")
                result = self.get_fallback_response(user_query)
                result["session_id"] = session_id
                return result
            
            # Get agents context
            agents_context = self.get_agents_context()
            
            # Get conversation history
            conversation_history = self.get_conversation_history(session_id)
            
            # Prepare messages for OpenAI
            messages = [
                {"role": "system", "content": self.get_system_prompt().format(agents_context=agents_context)}
            ]
            
            # Add conversation history
            messages.extend(conversation_history)
            
            # Add current user message
            messages.append({"role": "user", "content": user_query})
            
            # Call OpenAI API
            logger.info(f"Sending request to OpenAI for session {session_id}")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using GPT-4o-mini as specified
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            # Extract AI response
            ai_response = response.choices[0].message.content
            
            # Extract relevant agent IDs from the response
            filtered_agents = self.extract_agent_ids_from_response(ai_response)
            
            # Add to conversation history
            self.add_to_conversation_history(session_id, user_query, ai_response)
            
            # Format and return response
            result = self.format_response(ai_response, filtered_agents)
            result["session_id"] = session_id
            
            logger.info(f"Chat response generated for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in chat function: {str(e)}")
            # Use fallback response on error
            try:
                result = self.get_fallback_response(user_query)
                result["session_id"] = session_id
                result["error"] = str(e)
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback response also failed: {str(fallback_error)}")
                return {
                    "response": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                    "filtered_agents": [],
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
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

# Global chat agent instance
chat_agent = ChatAgent()

# Example usage and testing
if __name__ == "__main__":
    # Test the chat agent
    print("🤖 Testing Chat Agent...")
    
    # Test queries
    test_queries = [
        "I need help with financial analysis and reporting",
        "Tell me about the Earnings Analyst agent",
        "What agents can help with data analytics?",
        "I'm looking for something to help with customer support"
    ]
    
    for query in test_queries:
        print(f"\n👤 User: {query}")
        response = chat_agent.chat(query)
        print(f"🤖 Assistant: {response['response']}")
        print(f"🔍 Filtered Agents: {response['filtered_agents']}")
        print("-" * 50)
