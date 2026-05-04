"""
Memory Linker

Creates and manages links between memory notes.
Links enable traversal and discovery of related context.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MemoryLinker:
    """Creates links between memory notes"""
    
    def __init__(self):
        self.link_types = [
            "related_to",
            "extends",
            "contradicts",
            "prerequisite_of",
            "example_of",
            "part_of",
        ]
    
    def create_links(
        self,
        note: Dict[str, Any],
        related_notes: List[Dict[str, Any]],
        max_links: int = 10,
    ) -> List[str]:
        """
        Create links between notes
        
        Links are based on:
        - Shared tags
        - Same note type
        - Same workflow or user
        - Content similarity (simplified for now)
        
        Returns list of linked note IDs
        """
        links = []
        
        # Sort by importance and relevance
        scored_notes = []
        for related in related_notes:
            if related["id"] == note["id"]:
                continue
            
            score = 0.0
            
            # Shared tags boost
            shared_tags = set(note.get("tags", [])) & set(related.get("tags", []))
            score += len(shared_tags) * 0.3
            
            # Same type boost
            if related.get("note_type") == note.get("note_type"):
                score += 0.2
            
            # Same workflow boost
            if related.get("workflow_id") == note.get("workflow_id"):
                score += 0.4
            
            # Same user boost
            if related.get("user_id") == note.get("user_id"):
                score += 0.2
            
            # Importance factor
            score += related.get("importance", 0.5) * 0.2
            
            scored_notes.append((score, related["id"]))
        
        # Sort by score and take top links
        scored_notes.sort(reverse=True, key=lambda x: x[0])
        links = [note_id for _, note_id in scored_notes[:max_links]]
        
        logger.debug(f"Created {len(links)} links for note {note['id']}")
        return links
    
    def suggest_link_type(
        self,
        note1: Dict[str, Any],
        note2: Dict[str, Any],
    ) -> str:
        """Suggest the type of relationship between two notes"""
        
        # Same workflow suggests part_of or extends
        if note1.get("workflow_id") == note2.get("workflow_id"):
            return "part_of"
        
        # Shared tags with same type suggests related_to
        shared_tags = set(note1.get("tags", [])) & set(note2.get("tags", []))
        if shared_tags and note1.get("note_type") == note2.get("note_type"):
            return "related_to"
        
        # Different types but shared context
        if shared_tags:
            return "extends"
        
        return "related_to"
    
    def remove_broken_links(
        self,
        note: Dict[str, Any],
        valid_ids: set,
    ) -> List[str]:
        """Remove links to notes that no longer exist"""
        current_links = note.get("links", [])
        valid_links = [link_id for link_id in current_links if link_id in valid_ids]
        
        removed_count = len(current_links) - len(valid_links)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} broken links from note {note['id']}")
        
        return valid_links
