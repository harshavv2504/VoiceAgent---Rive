"""
MongoDB Database Connection and Operations
Handles all database interactions for customers, appointments, and orders
"""
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

# MongoDB connection
MONGODB_URI = os.environ.get("MONGODB_URL", os.environ.get("MONGODB_URI", "mongodb://localhost:27017/"))
DATABASE_NAME = os.environ.get("DATABASE_NAME", "bean_and_brew")

class Database:
    """MongoDB database handler"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.customers = None
        self.appointments = None
        self.orders = None
        
    def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(MONGODB_URI)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[DATABASE_NAME]
            
            # Collections
            self.customers = self.db.customers
            self.appointments = self.db.appointments
            self.orders = self.db.orders
            self.conversations = self.db.conversations
            
            # Create indexes
            self.customers.create_index("phone", unique=True)
            self.customers.create_index("email", unique=True)
            self.customers.create_index("customer_id", unique=True)
            self.conversations.create_index("session_id", unique=True)
            self.conversations.create_index("timestamp")
            
            logger.info(f"✅ Connected to MongoDB: {DATABASE_NAME}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    # Customer operations
    async def find_customer(self, phone: str = None, email: str = None, customer_id: str = None) -> Optional[Dict]:
        """Find a customer by phone, email, or ID"""
        try:
            query = {}
            if phone:
                query["phone"] = phone
            elif email:
                query["email"] = email
            elif customer_id:
                query["customer_id"] = customer_id
            else:
                return None
            
            customer = self.customers.find_one(query, {"_id": 0})
            return customer
            
        except Exception as e:
            logger.error(f"Error finding customer: {e}")
            return None
    
    async def create_customer(self, customer_id: str, name: str, phone: str, email: str) -> Dict:
        """Create a new customer"""
        try:
            customer = {
                "customer_id": customer_id,
                "name": name,
                "phone": phone,
                "email": email,
                "joined_date": datetime.now().isoformat()
            }
            
            self.customers.insert_one(customer)
            customer.pop("_id", None)  # Remove MongoDB _id
            return customer
            
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            raise
    
    # Appointment operations
    async def get_customer_appointments(self, customer_id: str) -> List[Dict]:
        """Get all appointments for a customer"""
        try:
            appointments = list(self.appointments.find(
                {"customer_id": customer_id},
                {"_id": 0}
            ))
            return appointments
            
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            return []
    
    async def create_appointment(self, appointment_id: str, customer_id: str, 
                                customer_name: str, date: str, service: str) -> Dict:
        """Create a new appointment"""
        try:
            appointment = {
                "appointment_id": appointment_id,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "date": date,
                "service": service,
                "status": "Scheduled",
                "created_at": datetime.now().isoformat()
            }
            
            self.appointments.insert_one(appointment)
            appointment.pop("_id", None)
            return appointment
            
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise
    
    async def check_appointment_exists(self, date: str) -> bool:
        """Check if an appointment exists at a specific time"""
        try:
            count = self.appointments.count_documents({"date": date})
            return count > 0
        except Exception as e:
            logger.error(f"Error checking appointment: {e}")
            return False
    
    # Order operations
    async def get_customer_orders(self, customer_id: str) -> List[Dict]:
        """Get all orders for a customer"""
        try:
            orders = list(self.orders.find(
                {"customer_id": customer_id},
                {"_id": 0}
            ))
            return orders
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    async def create_order(self, order_id: str, customer_id: str, 
                          customer_name: str, items: int, total: float, status: str) -> Dict:
        """Create a new order"""
        try:
            order = {
                "order_id": order_id,
                "customer_id": customer_id,
                "customer_name": customer_name,
                "date": datetime.now().isoformat(),
                "items": items,
                "total": total,
                "status": status
            }
            
            self.orders.insert_one(order)
            order.pop("_id", None)
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
    
    # Conversation operations
    async def save_conversation(self, session_id: str, messages: List[Dict], 
                               timestamp: str, duration: float = None) -> Dict:
        """Save a conversation log"""
        try:
            conversation = {
                "session_id": session_id,
                "messages": messages,
                "timestamp": timestamp,
                "duration": duration,
                "message_count": len(messages),
                "created_at": datetime.now().isoformat()
            }
            
            # Upsert (update if exists, insert if not)
            self.conversations.update_one(
                {"session_id": session_id},
                {"$set": conversation},
                upsert=True
            )
            conversation.pop("_id", None)
            return conversation
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            raise
    
    async def get_conversation(self, session_id: str) -> Optional[Dict]:
        """Get a conversation by session ID"""
        try:
            conversation = self.conversations.find_one(
                {"session_id": session_id},
                {"_id": 0}
            )
            return conversation
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None
    
    async def get_recent_conversations(self, limit: int = 10) -> List[Dict]:
        """Get recent conversations"""
        try:
            conversations = list(self.conversations.find(
                {},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit))
            return conversations
        except Exception as e:
            logger.error(f"Error getting recent conversations: {e}")
            return []


# Global database instance
db = Database()

# Connect on module import
if not db.connect():
    logger.warning("⚠️ MongoDB not connected. Using fallback mode.")
    db = None
