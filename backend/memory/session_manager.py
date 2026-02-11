"""
Session Manager
Handles persistent session storage across channels
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class SessionManager:
    """
    Manages shopping sessions with persistent file storage
    """
    
    def __init__(self, storage_file: str = "data/sessions.json"):
        self.storage_file = storage_file
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Load existing sessions from file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    self.sessions = json.load(f)
                print(f"✅ Loaded {len(self.sessions)} sessions from storage")
            else:
                # Create empty sessions file
                self._save_to_file()
                print("📝 Created new sessions storage")
        except Exception as e:
            print(f"⚠️ Error loading sessions: {e}")
            self.sessions = {}
    
    def _save_to_file(self):
        """Persist sessions to file"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            
            with open(self.storage_file, 'w') as f:
                json.dump(self.sessions, f, indent=2, default=str)
            print(f"💾 Saved {len(self.sessions)} sessions to storage")
        except Exception as e:
            print(f"❌ Error saving sessions: {e}")
    
    def create_session(self, customer_id: str = "CUST001") -> str:
        """
        Create a new shopping session
        """
        session_id = f"SESSION_{uuid.uuid4().hex[:8]}"
        
        self.sessions[session_id] = {
            "session_id": session_id,
            "customer_id": customer_id,
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "channel": "web",
            "liked_products": [],
            "cart": [],
            "conversation_history": [],
            "location": "Mumbai",
            "reserved_store": None,
            "status": "active"
        }
        
        self._save_to_file()
        print(f"🆕 Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session by ID
        """
        session = self.sessions.get(session_id)
        if session:
            # Update last activity
            session["last_activity"] = datetime.now().isoformat()
            self._save_to_file()
        return session
    
    def save_session(self, session_id: str, session_data: Dict[str, Any]):
        """
        Update and save session data
        """
        if session_id in self.sessions:
            session_data["last_activity"] = datetime.now().isoformat()
            self.sessions[session_id] = session_data
            self._save_to_file()
            print(f"💾 Updated session: {session_id}")
    
    def delete_session(self, session_id: str):
        """
        Delete a session
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_to_file()
            print(f"🗑️ Deleted session: {session_id}")
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all sessions
        """
        return self.sessions
    
    def clear_old_sessions(self, hours: int = 24):
        """
        Clear sessions older than specified hours
        """
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        
        to_delete = []
        for session_id, session in self.sessions.items():
            last_activity = datetime.fromisoformat(session["last_activity"])
            if last_activity < cutoff:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            self.delete_session(session_id)
        
        print(f"🧹 Cleared {len(to_delete)} old sessions")
    
    def add_to_liked_products(self, session_id: str, product_id: str):
        """
        Add product to liked list
        """
        session = self.get_session(session_id)
        if session and product_id not in session["liked_products"]:
            session["liked_products"].append(product_id)
            self.save_session(session_id, session)
    
    def add_to_cart(self, session_id: str, product_id: str, quantity: int = 1, size: str = "40"):
        """
        Add item to cart
        """
        session = self.get_session(session_id)
        if session:
            session["cart"].append({
                "product_id": product_id,
                "quantity": quantity,
                "size": size,
                "added_at": datetime.now().isoformat()
            })
            self.save_session(session_id, session)
    
    def update_cart_quantity(self, session_id: str, product_id: str, new_quantity: int):
        """
        Update quantity of item in cart (EDGE CASE #3)
        """
        session = self.get_session(session_id)
        if session:
            for item in session["cart"]:
                if item["product_id"] == product_id:
                    item["quantity"] = new_quantity
                    break
            self.save_session(session_id, session)
    
    def add_conversation(self, session_id: str, role: str, content: str, channel: str = "web"):
        """
        Add message to conversation history
        """
        session = self.get_session(session_id)
        if session:
            session["conversation_history"].append({
                "role": role,
                "content": content,
                "channel": channel,
                "timestamp": datetime.now().isoformat()
            })
            self.save_session(session_id, session)
    
    def get_conversation_history(self, session_id: str) -> list:
        """
        Get full conversation history
        """
        session = self.get_session(session_id)
        return session.get("conversation_history", []) if session else []
    
    def switch_channel(self, session_id: str, new_channel: str):
        """
        Switch to different channel (mobile → whatsapp → store)
        """
        session = self.get_session(session_id)
        if session:
            session["channel"] = new_channel
            self.save_session(session_id, session)
            print(f"📱 Switched to {new_channel} channel")