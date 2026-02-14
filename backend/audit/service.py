"""
Audit logging service.

Provides centralized audit logging for admin actions and user activities.
"""

import logging
from typing import Optional

from backend.utils_helper import db

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for recording audit logs.

    Provides methods to log admin actions and user activities
    with detailed information for compliance and debugging.
    """

    # Action types for admin actions
    ACTION_DELETE_USER = "delete_user"
    ACTION_BULK_DELETE = "bulk_delete"
    ACTION_SET_ADMIN = "set_admin"
    ACTION_BULK_EDIT = "bulk_edit"
    ACTION_BULK_IMPORT = "bulk_import"
    ACTION_CREATE_USER = "create_user"
    ACTION_UPDATE_USER = "update_user"
    ACTION_EXPORT_DATA = "export_data"

    # Action types for user actions
    ACTION_MARK_SELF = "mark_self"
    ACTION_MARK_OTHER = "mark_other"
    ACTION_MASS_MARKING = "mass_marking"
    ACTION_EXTERNAL_AUTH = "external_auth"
    ACTION_LOGIN = "login"
    ACTION_LOGIN_2FA = "login_2fa"
    ACTION_TOGGLE_PERMISSION = "toggle_permission"

    # Target types
    TARGET_USER = "user"
    TARGET_NFC_CARD = "nfc_card"
    TARGET_TOKEN = "token"

    async def log_admin_action(
        self,
        admin_tg_userid: int,
        action_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log an admin action.

        Args:
            admin_tg_userid: Telegram ID of the admin performing the action
            action_type: Type of action (use ACTION_* constants)
            target_type: Type of the target entity (use TARGET_* constants)
            target_id: ID of the target entity
            old_value: Previous state of the entity
            new_value: New state of the entity
            ip_address: IP address of the admin
            user_agent: User agent of the admin's browser/client

        Returns:
            ID of the created audit log entry, or None if failed
        """
        try:
            log_id = await db.create_audit_log(
                admin_tg_userid=admin_tg_userid,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            logger.info(
                f"Audit log created: admin={admin_tg_userid}, "
                f"action={action_type}, target={target_type}:{target_id}"
            )
            return log_id
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            return None

    async def log_user_action(
        self,
        actor_tg_userid: int,
        action_type: str,
        target_tg_userid: Optional[int] = None,
        details: Optional[dict] = None,
        status: str = "success",
    ) -> Optional[int]:
        """
        Log a user action.

        Args:
            actor_tg_userid: Telegram ID of the user performing the action
            action_type: Type of action (use ACTION_* constants)
            target_tg_userid: Telegram ID of the target user (for mark_other, etc.)
            details: Additional details about the action
            status: Status of the action ("success" or "failure")

        Returns:
            ID of the created action log entry, or None if failed
        """
        try:
            log_id = await db.create_user_action_log(
                actor_tg_userid=actor_tg_userid,
                action_type=action_type,
                target_tg_userid=target_tg_userid,
                details=details,
                status=status,
            )
            logger.debug(
                f"User action logged: actor={actor_tg_userid}, "
                f"action={action_type}, status={status}"
            )
            return log_id
        except Exception as e:
            logger.error(f"Failed to log user action: {e}")
            return None

    async def log_delete_user(
        self,
        admin_tg_userid: int,
        target_tg_userid: int,
        target_info: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[int]:
        """Helper to log user deletion."""
        return await self.log_admin_action(
            admin_tg_userid=admin_tg_userid,
            action_type=self.ACTION_DELETE_USER,
            target_type=self.TARGET_USER,
            target_id=str(target_tg_userid),
            old_value=target_info,
            ip_address=ip_address,
        )

    async def log_bulk_delete(
        self,
        admin_tg_userid: int,
        deleted_ids: list,
        failed_ids: list,
        ip_address: Optional[str] = None,
    ) -> Optional[int]:
        """Helper to log bulk user deletion."""
        return await self.log_admin_action(
            admin_tg_userid=admin_tg_userid,
            action_type=self.ACTION_BULK_DELETE,
            target_type=self.TARGET_USER,
            new_value={
                "deleted": deleted_ids,
                "failed": failed_ids,
                "total_deleted": len(deleted_ids),
            },
            ip_address=ip_address,
        )

    async def log_admin_level_change(
        self,
        admin_tg_userid: int,
        target_tg_userid: int,
        old_level: int,
        new_level: int,
        ip_address: Optional[str] = None,
    ) -> Optional[int]:
        """Helper to log admin level change."""
        return await self.log_admin_action(
            admin_tg_userid=admin_tg_userid,
            action_type=self.ACTION_SET_ADMIN,
            target_type=self.TARGET_USER,
            target_id=str(target_tg_userid),
            old_value={"admin_lvl": old_level},
            new_value={"admin_lvl": new_level},
            ip_address=ip_address,
        )

    async def log_marking(
        self,
        actor_tg_userid: int,
        target_tg_userid: Optional[int] = None,
        lesson_info: Optional[dict] = None,
        status: str = "success",
    ) -> Optional[int]:
        """Helper to log attendance marking."""
        action_type = (
            self.ACTION_MARK_SELF
            if actor_tg_userid == target_tg_userid or target_tg_userid is None
            else self.ACTION_MARK_OTHER
        )
        return await self.log_user_action(
            actor_tg_userid=actor_tg_userid,
            action_type=action_type,
            target_tg_userid=target_tg_userid,
            details=lesson_info,
            status=status,
        )

    async def log_external_auth(
        self,
        actor_tg_userid: int,
        token: str,
        service_name: Optional[str] = None,
        status: str = "success",
    ) -> Optional[int]:
        """Helper to log external auth approval."""
        return await self.log_user_action(
            actor_tg_userid=actor_tg_userid,
            action_type=self.ACTION_EXTERNAL_AUTH,
            details={
                "token_prefix": token[:8] + "..." if len(token) > 8 else token,
                "service_name": service_name,
            },
            status=status,
        )


# Global audit service instance
audit_service = AuditService()
