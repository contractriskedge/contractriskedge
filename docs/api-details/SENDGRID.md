# SendGrid — Email Notifications

## Overview

SendGrid handles all outbound email for the AI Contract Risk Analyzer, including transactional emails (welcome, password reset), notifications (risk alerts, redline accepted), and marketing emails (trial reminders, feature announcements).

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SENDGRID_API_KEY` | SendGrid API key (starts with `SG.`) | ✅ |
| `SENDGRID_FROM_EMAIL` | Sender email address | ✅ |
| `SENDGRID_FROM_NAME` | Sender display name | ❌ |

### Setup Steps

1. Go to https://sendgrid.com → Sign up (free: 100 emails/day)
2. Go to **Settings** → **API Keys** → **Create API Key**
3. Select **Full Access** → Copy key (starts with `SG.`)
4. Go to **Settings** → **Sender Authentication**
5. Verify a **Single Sender** email address
6. (Recommended) Set up **Domain Authentication** (SPF/DKIM) for better deliverability
7. Set `SENDGRID_API_KEY` in `.env`

---

## API Endpoints

### SendGrid v3 API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `https://api.sendgrid.com/v3/mail/send` | Send email |
| `GET` | `https://api.sendgrid.com/v3/templates` | List dynamic templates |
| `POST` | `https://api.sendgrid.com/v3/templates` | Create template |
| `PATCH` | `https://api.sendgrid.com/v3/templates/{id}` | Update template |
| `GET` | `https://api.sendgrid.com/v3/templates/{id}/versions` | List template versions |
| `POST` | `https://api.sendgrid.com/v3/templates/{id}/versions` | Create template version |
| `GET` | `https://api.sendgrid.com/v3/stats` | Get email statistics |
| `GET` | `https://api.sendgrid.com/v3/suppression/bounces` | List bounced emails |

---

## Email Templates

### Dynamic Templates (SendGrid)

Create these templates in SendGrid Dashboard → **Templates** → **Dynamic Templates**:

| Template ID | Name | Trigger | Priority |
|---|---|---|---|
| `d-abc123` | Welcome Email | User signs up | High |
| `d-def456` | Trial Ending | 3 days before trial end | High |
| `d-ghi789` | Trial Expired | Trial ended | High |
| `d-jkl012` | Risk Alert | High-severity risk flagged | High |
| `d-mno345` | Redline Accepted | Redline accepted by team | Medium |
| `d-pqr678` | Weekly Digest | Weekly risk summary | Medium |
| `d-stu901` | Payment Failed | Dunning email | High |
| `d-vwx234` | Invoice Available | New invoice generated | Medium |

### Template Variables

Each template uses Handlebars syntax for dynamic content:

```html
<!-- Welcome Email Template -->
<h1>Welcome to {{app_name}}, {{first_name}}!</h1>
<p>You've joined {{organization_name}} on the {{plan_name}} plan.</p>
<p>Get started:</p>
<ol>
  <li><a href="{{onboarding_url}}">Upload your first contract</a></li>
  <li><a href="{{docs_url}}">Read the quickstart guide</a></li>
</ol>
<p>Your trial ends on {{trial_end_date}}.</p>
```

### Template Variables Dictionary

| Variable | Description | Example |
|---|---|---|
| `{{app_name}}` | Application name | AI Contract Risk Analyzer |
| `{{first_name}}` | User's first name | Jane |
| `{{organization_name}}` | Tenant/org name | Acme Corp |
| `{{plan_name}}` | Subscription plan | Growth |
| `{{trial_end_date}}` | Trial expiration | May 27, 2026 |
| `{{risk_count}}` | Number of high-risk flags | 12 |
| `{{contract_name}}` | Contract name | MSA - Acme Corp |
| `{{redline_count}}` | Number of redlines | 5 |
| `{{dashboard_url}}` | Link to dashboard | https://app.contractriskedge.com |
| `{{onboarding_url}}` | Onboarding link | https://app.contractriskedge.com/onboarding |
| `{{billing_url}}` | Billing portal | https://app.contractriskedge.com/billing |
| `{{unsubscribe_url}}` | Unsubscribe link | https://app.contractriskedge.com/unsubscribe |

---

## Email Types

### 1. Transactional Emails

| Email | Trigger | Content |
|---|---|---|
| Welcome | User signs up | App overview, quickstart guide, support info |
| Password Reset | User requests reset | Secure reset link (expires 1 hour) |
| Team Invite | Admin invites user | Join link, role information |
| Plan Change | Subscription change | New plan details, next billing date |

### 2. Notification Emails

| Email | Trigger | Content |
|---|---|---|
| Risk Alert | High-severity (7+) risk flagged | Contract name, risk category, severity, link to analysis |
| Redline Accepted | Team member accepts redline | Contract name, clause type, who accepted |
| Redline Rejected | Team member rejects redline | Contract name, clause type, reason |
| Report Ready | Scheduled report generated | Link to download PDF report |

### 3. Marketing / PLG Emails

| Email | Day | Content |
|---|---|---|
| Welcome + Quickstart | Day 1 | 5-step onboarding checklist |
| Feature Spotlight | Day 7 | "Most popular feature you haven't tried yet" |
| Trial Ending | Day 12 | "Your trial expires in 2 days" |
| Win-back | Day 15 | 20% first-month discount offer |

### 4. Billing Emails

| Email | Trigger | Content |
|---|---|---|
| Invoice Available | New invoice | Amount, due date, PDF link |
| Payment Failed | Day 1 of failure | "We'll retry automatically" |
| Payment Failed | Day 7 | "Update your payment method" |
| Account Suspended | Day 21 | "Account suspended — data preserved 30 days" |

---

## Sending Emails (Python)

```python
from api.services.email_service import EmailService

email = EmailService()

# Send a transactional email
await email.send(
    to="jane@acme.com",
    template_id="d-abc123",  # Welcome template
    dynamic_data={
        "first_name": "Jane",
        "organization_name": "Acme Corp",
        "plan_name": "Growth",
        "onboarding_url": "https://app.contractriskedge.com/onboarding",
    },
)

# Send a risk alert
await email.send_risk_alert(
    to="legal@acme.com",
    contract_name="MSA - Vendor Corp",
    risk_category="Liability Exposure",
    severity=8,
    analysis_url="https://app.contractriskedge.com/contracts/abc123",
)
```

---

## Email Events (Webhooks)

SendGrid can send event webhooks to your platform for tracking:

| Event | Description |
|---|---|
| `processed` | Email accepted by SendGrid |
| `delivered` | Email delivered to recipient |
| `open` | Recipient opened the email |
| `click` | Recipient clicked a link |
| `bounce` | Email bounced (hard/soft) |
| `spam_report` | Recipient marked as spam |
| `unsubscribe` | Recipient unsubscribed |
| `group_unsubscribe` | Left specific suppression group |

### Webhook Configuration

1. SendGrid Dashboard → **Settings** → **Mail Settings**
2. **Event Webhook** → **Enable**
3. URL: `https://your-domain.com/api/v1/webhooks/sendgrid`
4. Select events to POST

---

## Testing

### Send a Test Email

```bash
cd /Volumes/home/ContractRiskEdge
python3 << 'EOF'
from api.services.email_service import EmailService
import os

email = EmailService()

# Send test email
result = await email.send(
    to="your-email@example.com",
    subject="Test from Contract Risk Analyzer",
    content="<h1>Test</h1><p>This is a test email.</p>",
)

print(f"Email sent: {result.message_id}")
EOF
```

### Verify Deliverability

```bash
# Check SendGrid stats
curl -s "https://api.sendgrid.com/v3/stats?start_date=2026-05-01&end_date=2026-05-13" \
  -H "Authorization: Bearer $SENDGRID_API_KEY" \
  | python3 -c "
import sys, json
stats = json.load(sys.stdin)
for day in stats:
    print(f\"{day['date']}: {day['stats'][0]['metrics']}\")
"
```

---

## Common Issues

| Issue | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Invalid API key | Regenerate key in SendGrid dashboard |
| `Email not delivered` | Sender not verified | Verify sender email or domain |
| `Going to spam` | No domain auth | Set up SPF/DKIM records |
| `Rate limited` | > 100 emails/day (free tier) | Upgrade to paid plan |
| `Bounced emails` | Invalid recipient | Clean email list; use verification |
| `Template not found` | Wrong template ID | Verify template exists in SendGrid |

---

## Related Files

| File | Purpose |
|---|---|
| `api/services/email_service.py` | Email sending service |
| `api/services/email_templates.py` | Dynamic template data builders |
| `api/webhooks/sendgrid.py` | SendGrid event webhook handler |
| `api/services/notification_service.py` | Notification orchestration |
