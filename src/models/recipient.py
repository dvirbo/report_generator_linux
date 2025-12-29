"""
Recipient Model
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Recipient:
    """
    Recipient model for email distribution
    
    >>> recipient = Recipient(email='test@example.com')
    >>> recipient.email
    'test@example.com'
    >>> recipient.bu_identifier is None
    True
    >>> 
    >>> recipient_with_bu = Recipient(email='test@example.com', bu_identifier='BU001')
    >>> recipient_with_bu.bu_identifier
    'BU001'
    """
    email: str
    bu_identifier: Optional[str] = None
    full_name: Optional[str] = None
    bu_internal_id: Optional[int] = None

