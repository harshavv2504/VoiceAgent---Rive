import json
from datetime import datetime, timedelta
import asyncio
from .business_logic import (
    get_customer,
    get_customer_appointments,
    get_customer_orders,
    schedule_appointment,
    get_available_appointment_slots,
    prepare_agent_filler_message,
    prepare_farewell_message,
    create_customer,
    reschedule_appointment,
    cancel_appointment,
    update_appointment_status,
)

# Import Knowledge Base Search
try:
    import sys
    from pathlib import Path
    # Add vector_builder to path
    vector_builder_path = Path(__file__).parent.parent / "vector_builder"
    sys.path.insert(0, str(vector_builder_path))
    from knowledge_search import KnowledgeBaseSearch
    
    # Initialize knowledge base
    kb_search = KnowledgeBaseSearch()
    try:
        kb_search.load_index()
        print("✅ Knowledge base loaded successfully")
    except Exception as e:
        print(f"⚠️ Knowledge base not loaded: {e}")
        kb_search = None
except ImportError as e:
    print(f"⚠️ Knowledge base not available: {e}")
    kb_search = None


async def find_customer(params):
    """Look up a customer by phone, email, or ID."""
    phone = params.get("phone")
    email = params.get("email")
    customer_id = params.get("customer_id")

    result = await get_customer(phone=phone, email=email, customer_id=customer_id)
    return result


async def get_appointments(params):
    """Get appointments for a customer."""
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}

    result = await get_customer_appointments(customer_id)
    return result


async def get_orders(params):
    """Get orders for a customer."""
    customer_id = params.get("customer_id")
    if not customer_id:
        return {"error": "customer_id is required"}

    result = await get_customer_orders(customer_id)
    return result


async def create_appointment(params):
    """Schedule a new appointment."""
    customer_id = params.get("customer_id")
    date = params.get("date")
    service = params.get("service")

    if not all([customer_id, date, service]):
        return {"error": "customer_id, date, and service are required"}

    result = await schedule_appointment(customer_id, date, service)
    return result


async def check_availability(params):
    """Check available appointment slots."""
    start_date = params.get("start_date")
    end_date = params.get(
        "end_date", (datetime.fromisoformat(start_date) + timedelta(days=7)).isoformat()
    )

    if not start_date:
        return {"error": "start_date is required"}

    result = await get_available_appointment_slots(start_date, end_date)
    return result


async def agent_filler(websocket, params):
    """
    Handle agent filler messages while maintaining proper function call protocol.
    """
    result = await prepare_agent_filler_message(websocket, **params)
    return result


async def end_call(websocket, params):
    """
    End the conversation and close the connection.
    """
    farewell_type = params.get("farewell_type", "general")
    result = await prepare_farewell_message(websocket, farewell_type)
    return result


async def search_knowledge_base(params):
    """Search the Bean & Brew knowledge base for specific information."""
    if not kb_search:
        return {"error": "Knowledge base not available"}
    
    query = params.get("query", "")
    if not query:
        return {"error": "Search query is required"}
    
    try:
        results = kb_search.search(query, k=4)
        if results:
            # Return the best match
            best_match = results[0]
            return {
                "found": True,
                "question": best_match.get("question", ""),
                "answer": best_match.get("answer", ""),
                "score": best_match.get("score", 0),
                "total_results": len(results)
            }
        else:
            return {"found": False, "message": "No information found for that query"}
    except Exception as e:
        return {"error": f"Error searching knowledge base: {str(e)}"}


async def get_knowledge_base_topics(params):
    """Get all available topics in the Bean & Brew knowledge base."""
    if not kb_search:
        return {"error": "Knowledge base not available"}
    
    try:
        questions = kb_search.get_all_questions()
        # Return first 20 questions as topics
        return {
            "topics": questions[:20],
            "total_topics": len(questions)
        }
    except Exception as e:
        return {"error": f"Error getting topics: {str(e)}"}


async def create_customer_account(params):
    """Create a new customer account"""
    name = params.get("name", "").strip()
    phone = params.get("phone", "").strip()
    email = params.get("email", "").strip()
    
    if not all([name, phone, email]):
        return {"error": "Name, phone, and email are required"}
    
    result = await create_customer(name, phone, email)
    return result


async def reschedule_appointment_func(params):
    """Reschedule an existing appointment"""
    appointment_id = params.get("appointment_id")
    new_date = params.get("new_date")
    new_service = params.get("new_service")
    
    if not all([appointment_id, new_date, new_service]):
        return {"error": "appointment_id, new_date, and new_service are required"}
    
    result = await reschedule_appointment(appointment_id, new_date, new_service)
    return result


async def cancel_appointment_func(params):
    """Cancel an existing appointment"""
    appointment_id = params.get("appointment_id")
    
    if not appointment_id:
        return {"error": "appointment_id is required"}
    
    result = await cancel_appointment(appointment_id)
    return result


async def update_appointment_status_func(params):
    """Update appointment status"""
    appointment_id = params.get("appointment_id")
    new_status = params.get("new_status")
    
    if not all([appointment_id, new_status]):
        return {"error": "appointment_id and new_status are required"}
    
    result = await update_appointment_status(appointment_id, new_status)
    return result


async def get_best_answer(params):
    """Get all top matching answers for a specific question."""
    if not kb_search:
        return {"error": "Knowledge base not available"}
    
    query = params.get("query", "")
    if not query:
        return {"error": "Query is required"}
    
    try:
        # Get top 4 matches with threshold
        results = kb_search.search(query, k=4)
        
        # Filter by confidence threshold (0.5)
        confident_results = [r for r in results if r.get("score", 0) >= 0.5]
        
        if confident_results:
            # Return all confident matches
            formatted_results = []
            for r in confident_results:
                formatted_results.append({
                    "question": r.get("question", ""),
                    "answer": r.get("answer", ""),
                    "score": r.get("score", 0)
                })
            
            return {
                "found": True,
                "matches": formatted_results,
                "total_matches": len(formatted_results)
            }
        else:
            return {"found": False, "message": "No confident answer found"}
    except Exception as e:
        return {"error": f"Error getting answer: {str(e)}"}


# Function definitions that will be sent to the Voice Agent API
FUNCTION_DEFINITIONS = [
    {
        "name": "agent_filler",
        "description": """Use this function to provide natural conversational filler before looking up information.
        ALWAYS call this function first with message_type='lookup' when you're about to look up customer information.
        After calling this function, you MUST immediately follow up with the appropriate lookup function (e.g., find_customer).""",
        "parameters": {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "description": "Type of filler message to use. Use 'lookup' when about to search for information.",
                    "enum": ["lookup", "general"],
                }
            },
            "required": ["message_type"],
        },
    },
    {
        "name": "find_customer",
        "description": """Look up a customer's account information. Use context clues to determine what type of identifier the user is providing:

        Customer ID formats:
        - Numbers only (e.g., '169', '42') → Format as 'CUST0169', 'CUST0042'
        - With prefix (e.g., 'CUST169', 'customer 42') → Format as 'CUST0169', 'CUST0042'
        
        Phone number recognition:
        - Standard format: '555-123-4567' → Format as '+15551234567'
        - With area code: '(555) 123-4567' → Format as '+15551234567'
        - Spoken naturally: 'five five five, one two three, four five six seven' → Format as '+15551234567'
        - International: '+1 555-123-4567' → Use as is
        - Always add +1 country code if not provided
        
        Email address recognition:
        - Spoken naturally: 'my email is john dot smith at example dot com' → Format as 'john.smith@example.com'
        - With domain: 'john@example.com' → Use as is
        - Spelled out: 'j o h n at example dot com' → Format as 'john@example.com'""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID. Format as CUSTXXXX where XXXX is the number padded to 4 digits with leading zeros. Example: if user says '42', pass 'CUST0042'",
                },
                "phone": {
                    "type": "string",
                    "description": """Phone number with country code. Format as +1XXXXXXXXXX:
                    - Add +1 if not provided
                    - Remove any spaces, dashes, or parentheses
                    - Convert spoken numbers to digits
                    Example: 'five five five one two three four five six seven' → '+15551234567'""",
                },
                "email": {
                    "type": "string",
                    "description": """Email address in standard format:
                    - Convert 'dot' to '.'
                    - Convert 'at' to '@'
                    - Remove spaces between spelled out letters
                    Example: 'j dot smith at example dot com' → 'j.smith@example.com'""",
                },
            },
        },
    },
    {
        "name": "get_appointments",
        "description": """Retrieve all appointments for a customer. Use this function when:
        - A customer asks about their upcoming appointments
        - A customer wants to know their appointment schedule
        - A customer asks 'When is my next appointment?'
        
        Always verify you have the customer's account first using find_customer before checking appointments.""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_orders",
        "description": """Retrieve order history for a customer. Use this function when:
        - A customer asks about their orders
        - A customer wants to check order status
        - A customer asks questions like 'Where is my order?' or 'What did I order?'
        
        Always verify you have the customer's account first using find_customer before checking orders.""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "create_appointment",
        "description": """Schedule a new appointment for a customer. Use this function when:
        - A customer wants to book a new appointment
        - A customer asks to schedule a service
        
        Before scheduling:
        1. Verify customer account exists using find_customer
        2. Check availability using check_availability
        3. Confirm date/time and service type with customer before booking""",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer's ID in CUSTXXXX format. Must be obtained from find_customer first.",
                },
                "date": {
                    "type": "string",
                    "description": "Appointment date and time in ISO format (YYYY-MM-DDTHH:MM:SS). Must be a time slot confirmed as available.",
                },
                "service": {
                    "type": "string",
                    "description": "Type of service requested. Must be one of the following: Consultation, Follow-up, Review, or Planning",
                    "enum": ["Consultation", "Follow-up", "Review", "Planning"],
                },
            },
            "required": ["customer_id", "date", "service"],
        },
    },
    {
        "name": "check_availability",
        "description": """Check available appointment slots within a date range. Use this function when:
        - A customer wants to know available appointment times
        - Before scheduling a new appointment
        - A customer asks 'When can I come in?' or 'What times are available?'
        
        After checking availability, present options to the customer in a natural way, like:
        'I have openings on [date] at [time] or [date] at [time]. Which works better for you?'""",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO format (YYYY-MM-DDTHH:MM:SS). Usually today's date for immediate availability checks.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO format. Optional - defaults to 7 days after start_date. Use for specific date range requests.",
                },
            },
            "required": ["start_date"],
        },
    },
    {
        "name": "end_call",
        "description": """End the conversation and close the connection. Call this function when:
        - User says goodbye, thank you, etc.
        - User indicates they're done ("that's all I need", "I'm all set", etc.)
        - User wants to end the conversation
        
        Examples of triggers:
        - "Thank you, bye!"
        - "That's all I needed, thanks"
        - "Have a good day"
        - "Goodbye"
        - "I'm done"
        
        Do not call this function if the user is just saying thanks but continuing the conversation.""",
        "parameters": {
            "type": "object",
            "properties": {
                "farewell_type": {
                    "type": "string",
                    "description": "Type of farewell to use in response",
                    "enum": ["thanks", "general", "help"],
                }
            },
            "required": ["farewell_type"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": """Search the Bean & Brew knowledge base using semantic search. Use this function when:
        - Users ask questions about Bean & Brew's services, coffee, or business
        - Users want to know about specialty coffee, roasting, or coffee programs
        - Users ask "What does Bean & Brew do?", "Tell me about Bean & Brew", or similar
        - Users want information about coffee quality, training, or partnerships
        
        DO NOT use this function for:
        - Questions about other companies (Starbucks, Dunkin, etc.)
        - Topics unrelated to Bean & Brew or specialty coffee
        - General business questions not specific to Bean & Brew
        
        IMPORTANT: Use detailed, natural language queries for better results. The semantic search understands meaning and context.
        
        Examples of GOOD queries:
        - "How can Bean & Brew help my café increase coffee revenue and profitability?"
        - "What training and support does Bean & Brew provide for baristas and staff?"
        - "Tell me about Bean & Brew's specialty coffee quality and sourcing practices"
        - "What makes Bean & Brew different from other coffee suppliers and roasters?"
        
        Examples of BAD queries (too short):
        - "coffee" (too vague)
        - "services" (too generic)
        - "help" (unclear)
        
        This function searches across 407 Q&A pairs using AI-powered semantic matching.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A detailed, natural language query about Bean & Brew. Use the user's full question or rephrase it with more context for better semantic matching. Longer, more specific queries work better than short keywords.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_knowledge_base_topics",
        "description": """Get available topics in the Bean & Brew knowledge base. Use this function when:
        - Users ask "What can you tell me about?" or "What topics do you know?"
        - Users want to know what information is available
        - Users ask for an overview of Bean & Brew topics""",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_customer_account",
        "description": """Create a new customer account. Use this function when:
        - A customer says they need to create an account
        - A customer wants to sign up or register
        - A customer doesn't exist and needs to be added
        
        IMPORTANT: Always ask customers to spell out their details for accuracy:
        - Ask them to spell their name letter by letter
        - Ask them to spell their phone number digit by digit
        - Ask them to spell their email address letter by letter
        - Confirm all details before creating the account""",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Customer's full name",
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number in international format (e.g., +15551234567)",
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                }
            },
            "required": ["name", "phone", "email"],
        },
    },
    {
        "name": "reschedule_appointment",
        "description": """Reschedule an existing appointment. Use this function when:
        - A customer wants to change their appointment time
        - A customer needs to move their appointment to a different date
        
        Before rescheduling:
        1. Get the appointment ID from get_appointments
        2. Check new availability using check_availability
        3. Confirm the new date/time with customer""",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to reschedule",
                },
                "new_date": {
                    "type": "string",
                    "description": "New date and time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                },
                "new_service": {
                    "type": "string",
                    "description": "Service type: Consultation, Follow-up, Review, or Planning",
                    "enum": ["Consultation", "Follow-up", "Review", "Planning"],
                },
            },
            "required": ["appointment_id", "new_date", "new_service"],
        },
    },
    {
        "name": "cancel_appointment",
        "description": """Cancel an existing appointment. Use this function when:
        - A customer wants to cancel their appointment
        - A customer can no longer make their scheduled time
        
        Before cancelling:
        1. Get the appointment ID from get_appointments
        2. Confirm cancellation with the customer""",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to cancel",
                },
            },
            "required": ["appointment_id"],
        },
    },
    {
        "name": "update_appointment_status",
        "description": """Update appointment status. Use this function when:
        - Marking an appointment as completed
        - Changing appointment status for administrative purposes
        
        Valid statuses: Scheduled, Completed, Cancelled""",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {
                    "type": "string",
                    "description": "The appointment ID to update",
                },
                "new_status": {
                    "type": "string",
                    "description": "New status for the appointment",
                    "enum": ["Scheduled", "Completed", "Cancelled"],
                },
            },
            "required": ["appointment_id", "new_status"],
        },
    },
    {
        "name": "get_best_answer",
        "description": """Get the single best matching answer for a specific Bean & Brew question using semantic search. Use this function when:
        - Users ask a very specific, direct question about Bean & Brew
        - You need one confident, authoritative answer (not multiple options)
        - Users want detailed information about a particular topic
        
        DO NOT use this function for:
        - Questions about other companies
        - Topics unrelated to Bean & Brew
        - Broad exploratory questions (use search_knowledge_base instead)
        
        IMPORTANT: Use detailed, natural language queries. The AI understands context and meaning.
        
        Examples:
        - "What specific training programs does Bean & Brew offer to help baristas improve their skills?"
        - "How does Bean & Brew's private-label coffee program work for restaurants?"
        - "What are the exact steps in Bean & Brew's coffee sourcing and quality control process?"
        
        This returns only the BEST match with a confidence threshold.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A detailed, specific question about Bean & Brew. Use natural language and include context for better semantic matching.",
                }
            },
            "required": ["query"],
        },
    },
]

# Map function names to their implementations
FUNCTION_MAP = {
    "find_customer": find_customer,
    "get_appointments": get_appointments,
    "get_orders": get_orders,
    "create_appointment": create_appointment,
    "check_availability": check_availability,
    "agent_filler": agent_filler,
    "end_call": end_call,
    "search_knowledge_base": search_knowledge_base,
    "get_knowledge_base_topics": get_knowledge_base_topics,
    "get_best_answer": get_best_answer,
    "create_customer_account": create_customer_account,
    "reschedule_appointment": reschedule_appointment_func,
    "cancel_appointment": cancel_appointment_func,
    "update_appointment_status": update_appointment_status_func,
}
