"""Utility functions for EgoShell."""

from __future__ import annotations
import json
import re
from typing import Any

def extract_json(text: str) -> dict[str, Any] | None:
    """Finds and parses the first complete JSON object in the text.
    
    Tracks braces while ignoring braces inside string literals or escaped characters.
    """
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    candidate = text[start_idx:i+1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
                        
    # Fallback to greedy regex if balance check failed
    for match in re.finditer(r'\{.*\}', text, re.DOTALL):
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
            
    return None
