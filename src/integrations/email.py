"""
Email Integration Module

Provides email notifications for scraper events and reports.
Supports HTML emails, attachments, and templates.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)


@dataclass
class EmailAttachment:
    """Email attachment."""

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class EmailMessage:
    """Email message structure."""

    to: List[str]
    subject: str
    body: str
    from_addr: Optional[str] = None
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    html: bool = False
    attachments: List[EmailAttachment] = field(default_factory=list)
    reply_to: Optional[str] = None

    def to_mime(self) -> MIMEMultipart:
        """Convert to MIME message."""
        msg = MIMEMultipart()
        msg['Subject'] = self.subject
        msg['From'] = self.from_addr or "noreply@scraper.local"
        msg['To'] = ', '.join(self.to)

        if self.cc:
            msg['Cc'] = ', '.join(self.cc)

        if self.reply_to:
            msg['Reply-To'] = self.reply_to

        # Add body
        mime_type = 'html' if self.html else 'plain'
        msg.attach(MIMEText(self.body, mime_type))

        # Add attachments
        for attachment in self.attachments:
            part = MIMEBase(*attachment.content_type.split('/'))
            part.set_payload(attachment.content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment.filename}'
            )
            msg.attach(part)

        return msg


class EmailTemplate:
    """Email template for consistent formatting."""

    def __init__(self, name: str, template: str):
        """
        Initialize email template.

        Args:
            name: Template name
            template: Template string with {placeholders}
        """
        self.name = name
        self.template = template

    def render(self, **kwargs) -> str:
        """
        Render template with variables.

        Args:
            **kwargs: Template variables

        Returns:
            Rendered template
        """
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return self.template


class EmailClient:
    """
    Email client for sending notifications.

    Features:
    - SMTP support
    - HTML emails
    - Attachments
    - Templates
    - Retry logic
    """

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        default_from: str = "noreply@scraper.local"
    ):
        """
        Initialize email client.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Whether to use TLS
            default_from: Default from address
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.default_from = default_from
        self.templates: Dict[str, EmailTemplate] = {}
        logger.info(f"Initialized EmailClient: {smtp_host}:{smtp_port}")

    def send(self, message: EmailMessage, retry: int = 3) -> bool:
        """
        Send an email message.

        Args:
            message: Email message to send
            retry: Number of retry attempts

        Returns:
            True if sent successfully
        """
        # Set default from address
        if not message.from_addr:
            message.from_addr = self.default_from

        mime_msg = message.to_mime()

        for attempt in range(retry):
            try:
                logger.debug(
                    f"Sending email to {', '.join(message.to)}: {message.subject}"
                )

                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()

                    if self.username and self.password:
                        server.login(self.username, self.password)

                    # Get all recipients
                    recipients = message.to + message.cc + message.bcc

                    server.send_message(mime_msg, to_addrs=recipients)

                logger.info(f"Email sent successfully: {message.subject}")
                return True

            except smtplib.SMTPException as e:
                logger.error(f"SMTP error (attempt {attempt + 1}/{retry}): {e}")
                if attempt == retry - 1:
                    return False

            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                return False

        return False

    def send_simple(
        self,
        to: List[str],
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """
        Send a simple email.

        Args:
            to: Recipient addresses
            subject: Email subject
            body: Email body
            html: Whether body is HTML

        Returns:
            True if sent successfully
        """
        message = EmailMessage(
            to=to,
            subject=subject,
            body=body,
            html=html
        )
        return self.send(message)

    def send_alert(
        self,
        to: List[str],
        title: str,
        message: str,
        severity: str = "warning",
        details: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send an alert email.

        Args:
            to: Recipient addresses
            title: Alert title
            message: Alert message
            severity: Severity level
            details: Additional details

        Returns:
            True if sent successfully
        """
        # Build HTML email
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert {{ padding: 20px; border-left: 4px solid #ff9900; background: #fff3cd; }}
                .alert.error {{ border-color: #dc3545; background: #f8d7da; }}
                .alert.info {{ border-color: #0dcaf0; background: #d1ecf1; }}
                .details {{ margin-top: 20px; }}
                .details table {{ border-collapse: collapse; width: 100%; }}
                .details th {{ text-align: left; padding: 8px; background: #f8f9fa; }}
                .details td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
            </style>
        </head>
        <body>
            <div class="alert {severity}">
                <h2>{title}</h2>
                <p>{message}</p>
            </div>
        """

        if details:
            html_body += """
            <div class="details">
                <h3>Details</h3>
                <table>
            """
            for key, value in details.items():
                html_body += f"<tr><th>{key}</th><td>{value}</td></tr>"

            html_body += "</table></div>"

        html_body += """
            <hr>
            <p style="color: #6c757d; font-size: 12px;">
                This is an automated message from Scraper Platform
            </p>
        </body>
        </html>
        """

        subject = f"[{severity.upper()}] {title}"

        message = EmailMessage(
            to=to,
            subject=subject,
            body=html_body,
            html=True
        )

        return self.send(message)

    def send_report(
        self,
        to: List[str],
        report_name: str,
        summary: str,
        data: Dict[str, Any],
        attach_file: Optional[Path] = None
    ) -> bool:
        """
        Send a report email.

        Args:
            to: Recipient addresses
            report_name: Report name
            summary: Report summary
            data: Report data
            attach_file: Optional file to attach

        Returns:
            True if sent successfully
        """
        # Build HTML report
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: #007bff; color: white; padding: 20px; }}
                .summary {{ padding: 20px; background: #f8f9fa; margin: 20px 0; }}
                .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
                .metric {{ flex: 1; padding: 15px; background: white; border: 1px solid #dee2e6; border-radius: 4px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                .metric-label {{ color: #6c757d; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report_name}</h1>
                <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p>{summary}</p>
            </div>

            <div class="metrics">
        """

        # Add metrics
        for key, value in data.items():
            html_body += f"""
                <div class="metric">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{key}</div>
                </div>
            """

        html_body += """
            </div>
        </body>
        </html>
        """

        message = EmailMessage(
            to=to,
            subject=f"Report: {report_name}",
            body=html_body,
            html=True
        )

        # Add attachment if provided
        if attach_file and attach_file.exists():
            with open(attach_file, 'rb') as f:
                content = f.read()
            message.attachments.append(EmailAttachment(
                filename=attach_file.name,
                content=content
            ))

        return self.send(message)

    def register_template(self, name: str, template: str) -> None:
        """
        Register an email template.

        Args:
            name: Template name
            template: Template string
        """
        self.templates[name] = EmailTemplate(name, template)
        logger.debug(f"Registered email template: {name}")

    def send_from_template(
        self,
        to: List[str],
        subject: str,
        template_name: str,
        html: bool = False,
        **variables
    ) -> bool:
        """
        Send email using a template.

        Args:
            to: Recipient addresses
            subject: Email subject
            template_name: Template name
            html: Whether template is HTML
            **variables: Template variables

        Returns:
            True if sent successfully
        """
        if template_name not in self.templates:
            logger.error(f"Template not found: {template_name}")
            return False

        template = self.templates[template_name]
        body = template.render(**variables)

        return self.send_simple(to, subject, body, html)


# Global client instance
_email_client: Optional[EmailClient] = None


def get_email_client() -> EmailClient:
    """
    Get the global email client instance.

    Returns:
        Email client singleton
    """
    global _email_client
    if _email_client is None:
        import os
        smtp_host = os.getenv("SMTP_HOST", "localhost")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")

        _email_client = EmailClient(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=username,
            password=password
        )

    return _email_client


def send_email(
    to: List[str],
    subject: str,
    body: str,
    html: bool = False
) -> bool:
    """
    Convenience function to send an email.

    Args:
        to: Recipient addresses
        subject: Email subject
        body: Email body
        html: Whether body is HTML

    Returns:
        True if sent successfully
    """
    client = get_email_client()
    return client.send_simple(to, subject, body, html)
