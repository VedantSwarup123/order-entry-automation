"""Notification adapters — Slack and email confirmations.

These are non-critical: a failure to notify never causes the overall
pipeline to fail.
"""
from __future__ import annotations

import structlog

from order_automation.integrations.composio_client import execute_action
from order_automation.models.order import Order, SubmissionResult
from order_automation.output.base import OutputAdapter

log = structlog.get_logger()


class SlackNotifier(OutputAdapter):
    """Posts a formatted order summary to a Slack channel via Composio."""

    def __init__(self, channel: str = "#orders") -> None:
        self.channel = channel

    def submit(self, order: Order) -> SubmissionResult:
        """Send a Slack message. Always returns success=True."""
        message = (
            f"*New Order* `{order.po_number}`\n"
            f"Customer: {order.customer_name} ({order.customer_id})\n"
            f"Items: {order.total_quantity} | Total: ${order.total_amount}\n"
            f"Source: {order.source.value} | Status: {order.status.value}"
        )
        try:
            execute_action("SLACK_SEND_MESSAGE", {
                "channel": self.channel,
                "text": message,
            })
        except Exception as exc:
            log.warning("slack_notify_failed", error=str(exc))
        return SubmissionResult(success=True, destination="slack_notify")


class EmailConfirmation(OutputAdapter):
    """Sends an email confirmation if the order metadata contains a recipient."""

    def submit(self, order: Order) -> SubmissionResult:
        """Send a confirmation email. Always returns success=True."""
        recipient = order.metadata.get("confirmation_email", "")
        if not recipient:
            return SubmissionResult(success=True, destination="email_confirmation")

        subject = f"Order Confirmation — {order.po_number}"
        body = (
            f"Thank you for your order {order.po_number}.\n\n"
            f"Items: {order.total_quantity}\n"
            f"Total: ${order.total_amount}\n\n"
            f"We will notify you when it ships."
        )
        try:
            execute_action("GMAIL_SEND_EMAIL", {
                "to": recipient,
                "subject": subject,
                "body": body,
            })
        except Exception as exc:
            log.warning("email_confirmation_failed", error=str(exc))
        return SubmissionResult(success=True, destination="email_confirmation")
