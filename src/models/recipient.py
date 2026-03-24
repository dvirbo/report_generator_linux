"""
Recipient Model
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Recipient:
    """
    Recipient model for email distribution
    """
    email: str
    bu_identifier: Optional[str] = None
    full_name: Optional[str] = None
    bu_internal_id: Optional[int] = None
    manager_id: Optional[str] = None

