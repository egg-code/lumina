import os
import logging
import asyncio
import httpx
from app.core.models import FeedbackRequest

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
DESTINATION_EMAIL = "luminabornin2026@gmail.com"
FROM_ADDRESS = "Lumina Feedback <onboarding@resend.dev>"


async def send_feedback_email_task(feedback: FeedbackRequest):
    """Send user feedback to the destination email via Resend HTTP API.

    Runs as a FastAPI BackgroundTask — the HTTP response is returned to the
    user immediately while this coroutine fires in the background.
    Uses HTTPS (port 443) which is always open on Render's free tier,
    making it immune to the port-587/465 firewall and IPv6 issues of SMTP.
    """
    if not RESEND_API_KEY:
        logger.warning(
            "RESEND_API_KEY is not set. Feedback email skipped. "
            "Please add RESEND_API_KEY to your environment variables."
        )
        return

    stars = "★" * feedback.rating + "☆" * (5 - feedback.rating)
    feedback_body_html = feedback.feedback.replace("\n", "<br>")

    remarks_html = ""
    if feedback.remarks:
        formatted_remarks = feedback.remarks.replace("\n", "<br>")
        remarks_html = (
            f"<h3>Remarks:</h3>"
            f"<p style='background: #f9fafb; padding: 15px; border-radius: 6px;'>"
            f"{formatted_remarks}</p>"
        )

    html_body = f"""
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

    plain_body = (
        f"New Feedback Received for Lumina!\n\n"
        f"Name: {feedback.name}\n"
        f"Email: {feedback.email}\n"
        f"Rating: {feedback.rating} / 5 stars\n\n"
        f"Feedback:\n{feedback.feedback}\n\n"
        f"Remarks:\n{feedback.remarks or 'N/A'}"
    )

    payload = {
        "from": FROM_ADDRESS,
        "to": [DESTINATION_EMAIL],
        "reply_to": feedback.email,
        "subject": f"[Lumina Feedback] Rating: {feedback.rating}★ from {feedback.name}",
        "html": html_body,
        "text": plain_body,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            logger.info(
                f"Feedback email sent via Resend. "
                f"id={response.json().get('id')} to={DESTINATION_EMAIL}"
            )
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Resend API returned an error: {e.response.status_code} — {e.response.text}",
            exc_info=True,
        )
    except Exception as e:
        logger.error(f"Failed to send feedback email via Resend: {e}", exc_info=True)
