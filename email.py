import resend
from config import settings
import logging

logger = logging.getLogger(__name__)
resend.api_key = settings.RESEND_API_KEY


TEMPLATES = {
    "welcome": {
        "subject": "Welcome to AIVisoor 🚀",
        "html": lambda d: f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
          <h2 style="color:#6366f1">Welcome, {d['name']}!</h2>
          <p>Your account is ready. Start analyzing your AI visibility now.</p>
          <a href="{d['dashboard_url']}" style="background:#6366f1;color:white;padding:12px 24px;
             border-radius:8px;text-decoration:none;display:inline-block;margin:16px 0">
            Open Dashboard →
          </a>
          <p style="color:#888;font-size:12px">AIVisoor · Unsubscribe</p>
        </div>""",
    },
    "report_ready": {
        "subject": "Your AI Visibility Report is Ready 📊",
        "html": lambda d: f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
          <h2 style="color:#6366f1">Report Ready: {d['domain']}</h2>
          <p>Your AI Visibility Score: <strong style="color:#6366f1">{d['score']}/100</strong></p>
          <a href="{d['report_url']}" style="background:#6366f1;color:white;padding:12px 24px;
             border-radius:8px;text-decoration:none;display:inline-block;margin:16px 0">
            View Full Report →
          </a>
        </div>""",
    },
    "password_reset": {
        "subject": "Reset your AIVisoor password",
        "html": lambda d: f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
          <h2>Password Reset</h2>
          <p>Click below to reset your password. Link expires in 1 hour.</p>
          <a href="{d['reset_url']}" style="background:#6366f1;color:white;padding:12px 24px;
             border-radius:8px;text-decoration:none;display:inline-block;margin:16px 0">
            Reset Password →
          </a>
          <p style="color:#888;font-size:12px">If you didn't request this, ignore this email.</p>
        </div>""",
    },
    "subscription_upgraded": {
        "subject": "Subscription Upgraded ✨",
        "html": lambda d: f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto">
          <h2 style="color:#6366f1">You're now on {d['plan'].title()}!</h2>
          <p>You now have {d['reports_limit']} reports/month. Enjoy the extra power.</p>
        </div>""",
    },
}


async def send_email(to: str, template: str, data: dict) -> bool:
    try:
        tpl = TEMPLATES[template]
        resend.Emails.send({
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": [to],
            "subject": tpl["subject"],
            "html": tpl["html"](data),
        })
        logger.info(f"Email '{template}' sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email '{template}' to {to}: {e}")
        return False
