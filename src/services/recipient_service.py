"""
Recipient Service
Fetch recipients by BU indicator from database
"""

import logging
from typing import List, Optional
from ..models.recipient import Recipient
from .database_service import DatabaseService
from ..utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)


class RecipientService:
    """Service for managing recipients"""

    def __init__(self, db_service: DatabaseService):
        """
        Initialize recipient service
        
        Args:
            db_service: DatabaseService instance
        """
        self.db_service = db_service

    def get_recipients(self, bu_indicator: str) -> List[Recipient]:
        """
        Fetch recipients from database based on BU indicator
        
        Args:
            bu_indicator: BU indicator string (possible: 'branches', 'merchav', 'compliance')
        
        Returns:
            List of Recipient objects with email and bu_identifier
        """
        name = (bu_indicator or '').strip().lower()

        # Read login names for this BU type from config.ini [recipients] section.
        config_loader = ConfigLoader()
        key = f"{name}_logins"
        logins_str = config_loader.get('recipients', key, fallback='')
        if not logins_str:
            logger.warning(f"No login names configured for bu_indicator {bu_indicator} (key: {key}), returning no recipients")
            return []

        login_names = [v.strip() for v in logins_str.split(',') if v.strip()]
        if not login_names:
            logger.warning(f"Empty login name list after parsing for bu_indicator {bu_indicator}, returning no recipients")
            return []

        # Build a simple IN list directly from config values
        # Example: 'AML_mobile_Manager','AML_Second_Level','AML_Mortgages_Manager'
        in_list = ", ".join(f"'{name}'" for name in login_names)

        query = f"""
            SELECT
              DISTINCT child_users.email AS email,
              bu.bu_identifier AS bu_identifier,
              child_users.full_name AS full_name,
              child_users.bu_internal_id AS bu_internal_id,
              child_users.user_identifier AS manager_id
            FROM actone.acm_users parent_users
            JOIN actone.acm_user_group_members members
              ON parent_users.user_internal_id = members.parent_user_id
             AND parent_users.is_active = 1
            JOIN actone.acm_users child_users
              ON members.child_user_id = child_users.user_internal_id
             AND child_users.is_active = 1
            JOIN actone.acm_md_business_units bu
              ON child_users.bu_internal_id = bu.bu_internal_id
            WHERE parent_users.login_name IN ({in_list})
        """
        
        try:
            rows = self.db_service.execute_query(query)
            
            recipients = []
            for row in rows:
                recipient = Recipient(
                    email=row.get('email') or row.get('EMAIL'),
                    bu_identifier=row.get('bu_identifier') or row.get('BU_IDENTIFIER'),
                    full_name=row.get('full_name') or row.get('FULL_NAME'),
                    bu_internal_id=row.get('bu_internal_id') or row.get('BU_INTERNAL_ID'),
                    manager_id=row.get('manager_id') or row.get('MANAGER_ID')
                )
                recipients.append(recipient)
            
            logger.info(f"Fetched {len(recipients)} recipients for BU indicator {bu_indicator}")
            return recipients
            
        except Exception as e:
            logger.error(f"Failed to fetch recipients from database: {e}")
            raise
    


