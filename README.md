# BDO Digital news digest

This GitHub Action emails a daily digest of public news matching BDO Digital
in the UK, United States, and Canada. It uses Google News RSS, so no paid news
API is required.

## Setup

Add these repository secrets under **Settings -> Secrets and variables -> Actions**:

| Secret | Value |
| --- | --- |
| `NEWS_EMAIL_TO` | Address that should receive the digest |
| `SMTP_FROM` | Sender address accepted by your SMTP provider |
| `SMTP_HOST` | SMTP server hostname, such as `smtp.gmail.com` |
| `SMTP_PORT` | `465` for SSL or `587` for STARTTLS |
| `SMTP_USERNAME` | SMTP login, usually the sender address |
| `SMTP_PASSWORD` | SMTP password or provider app password |

The workflow runs at 07:00 Europe/London and can also be started manually from
the **Actions** tab. GitHub may delay scheduled workflows by several minutes.

The first run can be tested with **Run workflow** after the secrets are set.