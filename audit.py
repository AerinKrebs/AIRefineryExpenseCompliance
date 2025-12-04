"""
Simple modular audit logging for all agents.
Usage:
    from audit import audit_log
    audit_log.save(agent_name, result, user_id)
"""
#============== WARNING: ALL CLAUDE DEVELOPED FILE ==========================
# This file was developed by Claude, an AI assistant, as part of the AI Refinery project.
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class AuditLog:
    """Simple audit logger that any agent can use."""
    
    def __init__(self, audit_file: str = "audit_log.json"):
        self.audit_file = audit_file
    
    def _load(self) -> Dict:
        """Load existing audit log or create new one."""
        if os.path.exists(self.audit_file):
            try:
                with open(self.audit_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"entries": []}
        return {"entries": []}
    
    def _save_file(self, data: Dict):
        """Save audit data to file."""
        with open(self.audit_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def save(
        self,
        agent_name: str,
        result: Any,
        user_id: str = "unknown",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Save an agent's result to the audit log.
        
        Parameters:
            agent_name: Name of the agent (e.g., "Image Understanding Agent")
            result: The result from the agent (dict or JSON string)
            user_id: User identifier
            metadata: Optional extra data to include
            
        Returns:
            The created audit entry
        """
        # Parse result if it's a string
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {"raw_output": result}
        
        # Create entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "user_id": user_id,
            "success": result.get("success", None),
            "data": result.get("extracted_data") or result.get("data") or result,
            "error": result.get("error"),
            "notes": result.get("processing_notes", []),
            "metadata": metadata or {}
        }
        
        # Load, append, save
        audit_data = self._load()
        audit_data["entries"].append(entry)
        self._save_file(audit_data)
        
        return entry
    
    def get_entries(
        self,
        agent_name: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list:
        """
        Get audit entries with optional filters.
        
        Parameters:
            agent_name: Filter by agent name
            user_id: Filter by user ID
            limit: Max number of entries to return
            
        Returns:
            List of matching entries
        """
        audit_data = self._load()
        entries = audit_data.get("entries", [])
        
        # Apply filters
        if agent_name:
            entries = [e for e in entries if e.get("agent") == agent_name]
        if user_id:
            entries = [e for e in entries if e.get("user_id") == user_id]
        
        # Apply limit (most recent first)
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def get_last_entry(self, agent_name: Optional[str] = None) -> Optional[Dict]:
        """Get the most recent entry."""
        entries = self.get_entries(agent_name=agent_name, limit=1)
        return entries[-1] if entries else None
    
    def clear(self):
        """Clear all entries."""
        self._save_file({"entries": []})
    
    def count(self, agent_name: Optional[str] = None) -> int:
        """Count entries."""
        return len(self.get_entries(agent_name=agent_name))
    
    def print_summary(self):
        """Print a summary of the audit log."""
        entries = self.get_entries()
        
        print(f"\n{'='*50}")
        print(f" AUDIT LOG SUMMARY")
        print(f"{'='*50}")
        print(f"  File: {self.audit_file}")
        print(f"  Total Entries: {len(entries)}")
        
        if entries:
            # Count by agent
            agents = {}
            for e in entries:
                agent = e.get("agent", "unknown")
                agents[agent] = agents.get(agent, 0) + 1
            
            print(f"\n  By Agent:")
            for agent, count in agents.items():
                print(f"    - {agent}: {count}")
            
            # Success rate
            successful = sum(1 for e in entries if e.get("success") is True)
            print(f"\n  Success Rate: {successful}/{len(entries)}")
        
        print(f"{'='*50}\n")


# Global instance - import this
audit_log = AuditLog()