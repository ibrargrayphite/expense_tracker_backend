from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from tracker.models import PlannedExpense
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_planned_expense_reminders():
    """
    Celery task to send consolidated email reminders for active and overdue planned expenses.
    """
    now = timezone.now()
    
    # Fetch non-completed expenses that are either active or overdue
    expenses = PlannedExpense.objects.filter(
        is_completed=False,
        start_date__lte=now
    ).select_related('user', 'category')
    
    user_reminders = {}
    
    for exp in expenses:
        user = exp.user
        if user.id not in user_reminders:
            user_reminders[user.id] = {
                'user': user,
                'active': [],
                'overdue': []
            }
        
        if exp.end_date < now:
            user_reminders[user.id]['overdue'].append(exp)
        elif exp.start_date <= now <= exp.end_date:
            user_reminders[user.id]['active'].append(exp)
    
    for data in user_reminders.values():
        user = data['user']
        active = data['active']
        overdue = data['overdue']
        
        if not active and not overdue:
            continue
            
        _send_reminder_email(user, active, overdue)

def _send_reminder_email(user, active, overdue):
    if not user.email:
        logger.warning("User %s has no email address. Skipping reminder.", user.username)
        return

    subject = "Your Planned Expense Reminders"
    
    active_html = "".join([
        f"<li><strong>Rs. {exp.amount}</strong> - {exp.category.name if exp.category else 'No Category'} - {exp.note if exp.note else 'No Note'} "
        f"(Due: {exp.end_date.strftime('%b %d, %H:%M')})</li>"
        for exp in active
    ])
    
    overdue_html = "".join([
        f"<li style='color: #ef4444;'><strong>Rs. {exp.amount}</strong> - {exp.category.name if exp.category else 'No Category'} - {exp.note if exp.note else 'No Note'} "
        f"(Was due: {exp.end_date.strftime('%b %d, %H:%M')})</li>"
        for exp in overdue
    ])
    
    html_content = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
            <h2 style="color: #1e293b;">Hello {user.first_name or user.username},</h2>
            <p style="color: #475569;">Here is a summary of your current planned expenses that need your attention:</p>
            
            {f"<h3 style='color: #ef4444;'>Overdue Expenses ⚠️</h3><ul>{overdue_html}</ul>" if overdue_html else ""}
            {f"<h3 style='color: #f59e0b;'>Active Expenses ●</h3><ul>{active_html}</ul>" if active_html else ""}
            
            <p style="margin-top: 20px; color: #64748b; font-size: 0.875rem;">
                Log in to your account to manage these expenses or mark them as completed.
            </p>
        </div>
    """
    
    try:
        sendgrid_api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        
        if sendgrid_api_key:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            message = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_emails=user.email,
                subject=subject,
                html_content=html_content
            )
            sg = SendGridAPIClient(sendgrid_api_key)
            sg.send(message)
        else:
            send_mail(
                subject,
                "", # Plain text body
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_content
            )
        logger.info("Sent reminder email to %s", user.email)
    except Exception as e:
        logger.error("Failed to send reminder email to %s: %s", user.email, e, exc_info=True)
