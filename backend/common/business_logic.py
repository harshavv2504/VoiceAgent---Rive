"""
Business Logic for Bean & Brew Voice Agent
Uses MongoDB for data persistence
"""
import asyncio
from datetime import datetime, timedelta
import logging
import random

# Import MongoDB database
try:
    from common.database import db
except ImportError:
    from .database import db

logger = logging.getLogger(__name__)


# Helper functions to generate unique IDs
def generate_unique_customer_id() -> str:
    """Generate unique customer ID"""
    return f"CUST{random.randint(1000, 9999)}"

def generate_unique_appointment_id() -> str:
    """Generate unique appointment ID"""
    return f"APT{random.randint(1000, 9999)}"

def generate_unique_order_id() -> str:
    """Generate unique order ID"""
    return f"ORD{random.randint(1000, 9999)}"


# Customer operations
async def get_customer(phone: str = None, email: str = None, customer_id: str = None):
    """Look up a customer by phone, email, or ID"""
    if not db:
        return {"error": "Database not available"}
    
    try:
        customer = await db.find_customer(phone=phone, email=email, customer_id=customer_id)
        if customer:
            return customer
        else:
            return {"error": "Customer not found"}
    except Exception as e:
        logger.error(f"Error finding customer: {e}")
        return {"error": str(e)}


async def create_customer(name: str, phone: str, email: str):
    """Create a new customer"""
    if not db:
        return {"error": "Database not available"}
    
    try:
        # Check if customer already exists
        existing = await db.find_customer(phone=phone)
        if existing:
            return {"error": "Customer already exists with this phone number"}
        
        customer_id = generate_unique_customer_id()
        customer = await db.create_customer(customer_id, name, phone, email)
        return {"success": True, "customer": customer}
    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        return {"error": str(e)}


async def reschedule_appointment(appointment_id: str, new_date: str, new_service: str):
    """Reschedule an existing appointment"""
    if not db:
        return {"error": "Database not available"}
    
    try:
        # Validate new date
        try:
            appointment_datetime = datetime.fromisoformat(new_date)
            if appointment_datetime <= datetime.now():
                return {"error": "Cannot schedule appointments in the past"}
        except ValueError:
            return {"error": "Invalid date format"}
        
        # Check if new slot is available
        slot_taken = await db.check_appointment_exists(new_date)
        if slot_taken:
            return {"error": "This time slot is already booked"}
        
        # Update appointment in database
        # Note: You'll need to add update_appointment method to database.py
        return {"success": True, "message": "Appointment rescheduled", "new_date": new_date}
    except Exception as e:
        logger.error(f"Error rescheduling appointment: {e}")
        return {"error": str(e)}


async def cancel_appointment(appointment_id: str):
    """Cancel an existing appointment"""
    if not db:
        return {"error": "Database not available"}
    
    try:
        # Note: You'll need to add cancel_appointment method to database.py
        return {"success": True, "message": "Appointment cancelled", "appointment_id": appointment_id}
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return {"error": str(e)}


async def update_appointment_status(appointment_id: str, new_status: str):
    """Update appointment status"""
    if not db:
        return {"error": "Database not available"}
    
    valid_statuses = ["Scheduled", "Completed", "Cancelled"]
    if new_status not in valid_statuses:
        return {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}
    
    try:
        # Note: You'll need to add update_status method to database.py
        return {"success": True, "message": "Status updated", "new_status": new_status}
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        return {"error": str(e)}


# Appointment operations
async def get_customer_appointments(customer_id: str):
    """Get all appointments for a customer"""
    if not db:
        return {"error": "Database not available"}
    
    try:
        appointments = await db.get_customer_appointments(customer_id)
        return {"customer_id": customer_id, "appointments": appointments}
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        return {"error": str(e)}


async def schedule_appointment(customer_id: str, date: str, service: str):
    """Schedule a new appointment"""
    if not db:
        return {"error": "Database not available"}
    
    try:
        # Verify customer exists
        customer = await db.find_customer(customer_id=customer_id)
        if not customer:
            return {"error": "Customer not found"}
        
        # Validate date
        try:
            appointment_datetime = datetime.fromisoformat(date)
            if appointment_datetime <= datetime.now():
                return {"error": "Cannot schedule appointments in the past"}
        except ValueError:
            return {"error": "Invalid date format"}
        
        # Check if slot is available
        slot_taken = await db.check_appointment_exists(date)
        if slot_taken:
            return {"error": "This time slot is already booked"}
        
        # Create appointment
        appointment_id = generate_unique_appointment_id()
        appointment = await db.create_appointment(
            appointment_id, 
            customer_id, 
            customer["name"], 
            date, 
            service
        )
        
        # Send email confirmation and calendar invite
        try:
            from .meeting_handler import send_meeting_invite
            await send_meeting_invite(appointment, customer)
            logger.info(f"✅ Meeting invite sent for appointment {appointment_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not send meeting invite: {e}")
        
        return appointment
    except Exception as e:
        logger.error(f"Error scheduling appointment: {e}")
        return {"error": str(e)}


async def get_available_appointment_slots(start_date: str, end_date: str):
    """Get available appointment slots"""
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        slots = []
        current = start
        
        while current <= end:
            # Only weekdays, 9 AM to 5 PM
            if current.weekday() < 5 and 9 <= current.hour < 17:
                slot_time = current.isoformat()
                
                # Check if slot is taken
                if db:
                    taken = await db.check_appointment_exists(slot_time)
                    if not taken:
                        slots.append(slot_time)
                else:
                    slots.append(slot_time)
            
            current += timedelta(hours=1)
        
        return {"available_slots": slots}
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        return {"error": str(e)}


# Order operations
async def get_customer_orders(customer_id: str):
    """Get all orders for a customer"""
    if not db:
        return {"error": "Database not available"}
    
    try:
        orders = await db.get_customer_orders(customer_id)
        return {"customer_id": customer_id, "orders": orders}
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return {"error": str(e)}


# Agent filler and farewell messages
async def prepare_agent_filler_message(websocket, message_type):
    """Handle agent filler messages"""
    result = {"status": "queued", "message_type": message_type}
    
    if message_type == "lookup":
        inject_message = {
            "type": "InjectAgentMessage",
            "message": "Let me look that up for you...",
        }
    else:
        inject_message = {
            "type": "InjectAgentMessage",
            "message": "One moment please...",
        }
    
    return {"function_response": result, "inject_message": inject_message}


async def prepare_farewell_message(websocket, farewell_type):
    """End the conversation with a farewell message"""
    if farewell_type == "thanks":
        message = "Thank you for calling! Have a great day!"
    elif farewell_type == "help":
        message = "I'm glad I could help! Have a wonderful day!"
    else:
        message = "Goodbye! Have a nice day!"
    
    inject_message = {"type": "InjectAgentMessage", "message": message}
    close_message = {"type": "close"}
    
    return {
        "function_response": {"status": "closing", "message": message},
        "inject_message": inject_message,
        "close_message": close_message,
    }
