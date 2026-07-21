import os
import smtplib
import logging
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.models import FeedbackRequest

logger = logging.getLogger(__name__)

DESTINATION_EMAIL = "luminabornin2026@gmail.com"
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", DESTINATION_EMAIL)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def _send_email_sync(feedback: FeedbackRequest) -> bool:
    """Synchronous SMTP email sending function to be executed in a background thread."""
    if not SMTP_PASSWORD:
        logger.warning(
            "SMTP_PASSWORD is not set. Feedback email skipped. "
            "Please configure SMTP_PASSWORD in .env file to enable Gmail SMTP sending."
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Lumina Feedback] Rating: {feedback.rating}★ from {feedback.name}"
        msg["From"] = SMTP_USER
        msg["To"] = DESTINATION_EMAIL
        msg["Reply-To"] = feedback.email

        plain_text = f"""
New Feedback Received for Lumina!

Name: {feedback.name}
Email: {feedback.email}
Rating: {feedback.rating} / 5 stars

Feedback:
{feedback.feedback}

Remarks:
{feedback.remarks or 'N/A'}
"""

        stars = "★" * feedback.rating + "☆" * (5 - feedback.rating)
        feedback_body_html = feedback.feedback.replace("\n", "<br>")

        remarks_html = ""
        if feedback.remarks:
            formatted_remarks = feedback.remarks.replace("\n", "<br>")
            remarks_html = f"<h3>Remarks:</h3><p style='background: #f9fafb; padding: 15px; border-radius: 6px;'>{formatted_remarks}</p>"

        html_text = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #4F46E5;">New Feedback Received for Lumina</h2>
    <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
      <tr>
        <td style="padding: 8px; font-weight: bold; width: 120px;">Name:</td>
        <td style="padding: 8px;">{feedback.name}</td>
      </tr>
      <tr>
        <td style="padding: 8px; font-weight: bold;">Email:</td>
        <td style="padding: 8px;"><a href="mailto:{feedback.email}">{feedback.email}</a></td>
      </tr>
      <tr>
        <td style="padding: 8px; font-weight: bold;">Rating:</td>
        <td style="padding: 8px; color: #F59E0B; font-weight: bold;">{stars} ({feedback.rating}/5)</td>
      </tr>
    </table>
    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
    <h3>Feedback:</h3>
    <p style="background: #f9fafb; padding: 15px; border-radius: 6px; border-left: 4px solid #4F46E5;">
      {feedback_body_html}
    </p>
    {remarks_html}
  </body>
</html>
"""

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_text, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Feedback email successfully sent to {DESTINATION_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Failed to send feedback email: {e}", exc_info=True)
        return False


async def send_feedback_email_task(feedback: FeedbackRequest):
    """Async wrapper to run synchronous SMTP sending in a thread pool background task."""
    await asyncio.to_thread(_send_email_sync, feedback)
