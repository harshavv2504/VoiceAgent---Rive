"""
Meeting Handler for Bean & Brew
Sends email confirmations and calendar invites for consultations
"""
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import base64
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Load from environment
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Bean & Brew")
BUSINESS_ADDRESS = os.getenv("BUSINESS_ADDRESS", "123 Coffee Street")
MEETING_LOCATION = os.getenv("MEETING_LOCATION", "Zoom")
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    logger.warning("Google APIs not available. Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def generate_meeting_json(appointment, customer):
    """Generate meeting data for email and calendar"""
    meeting_start = appointment["date"]
    start_dt = datetime.fromisoformat(meeting_start)
    meeting_end = (start_dt + timedelta(minutes=30)).isoformat()

    return {
        "organizer_name": BUSINESS_NAME,
        "attendees": [
            {
                "email": customer.get("email", ""),
                "name": customer.get("name", "")
            }
        ],
        "meeting_topic": f"{BUSINESS_NAME} {appointment['service']} Consultation",
        "meeting_date": meeting_start[:10],
        "meeting_start": meeting_start,
        "meeting_end": meeting_end,
        "meeting_description": f"Consultation about {appointment['service']} - Discuss how {BUSINESS_NAME} can transform your coffee program",
        "meeting_location": MEETING_LOCATION
    }


def get_gmail_service():
    """Get Gmail API service from environment JSON"""
    if not GOOGLE_APIS_AVAILABLE:
        return None
    
    try:
        import json
        token_json = os.getenv("GOOGLE_TOKEN_GMAIL_JSON")
        
        if not token_json:
            logger.warning("GOOGLE_TOKEN_GMAIL_JSON not set in .env")
            return None
        
        token_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Error getting Gmail service: {e}")
        return None


def get_calendar_service():
    """Get Google Calendar API service from environment JSON"""
    if not GOOGLE_APIS_AVAILABLE:
        return None
    
    try:
        import json
        token_json = os.getenv("GOOGLE_TOKEN_CALENDAR_JSON")
        
        if not token_json:
            logger.warning("GOOGLE_TOKEN_CALENDAR_JSON not set in .env")
            return None
        
        token_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(token_data, CALENDAR_SCOPES)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Error getting Calendar service: {e}")
        return None


async def send_meeting_invite(appointment, customer):
    """Send email and calendar invite for appointment"""
    if not GOOGLE_APIS_AVAILABLE:
        logger.warning("Google APIs not available, skipping email/calendar")
        return False
    
    try:
        meeting_data = generate_meeting_json(appointment, customer)
        
        gmail_service = get_gmail_service()
        calendar_service = get_calendar_service()
        
        if not gmail_service or not calendar_service:
            logger.warning("Gmail or Calendar service not available")
            return False
        
        # Send email
        email = customer.get("email")
        name = customer.get("name", "there")
        subject = f"Consultation Confirmed: {meeting_data['meeting_topic']}"
        
        body_text = f"""Hi {name},

Thank you for scheduling a consultation with Bean & Brew!

Consultation Details:
• Service: {appointment['service']}
• Date: {meeting_data['meeting_date']}
• Time: {meeting_data['meeting_start'][-8:]} - {meeting_data['meeting_end'][-8:]}
• Location: {meeting_data['meeting_location']}

We're excited to discuss how Bean & Brew can help transform your coffee program and grow your business!

A calendar invite has been sent to your email.

Best regards,
{BUSINESS_NAME} Team
"""
        
        message = MIMEText(body_text)
        message["to"] = email
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {"raw": raw}
        
        sent = gmail_service.users().messages().send(userId="me", body=message_body).execute()
        logger.info(f"✅ Email sent to {email}")
        
        # Create calendar event
        event = {
            'summary': meeting_data['meeting_topic'],
            'description': meeting_data['meeting_description'],
            'location': meeting_data['meeting_location'],
            'start': {'dateTime': meeting_data['meeting_start'], 'timeZone': TIMEZONE},
            'end': {'dateTime': meeting_data['meeting_end'], 'timeZone': TIMEZONE},
            'attendees': [{'email': email}],
            'reminders': {'useDefault': True},
        }
        
        created_event = calendar_service.events().insert(
            calendarId='primary', 
            body=event, 
            sendUpdates='all'
        ).execute()
        
        logger.info(f"✅ Calendar event created: {created_event.get('htmlLink')}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending meeting invite: {e}")
        return False
