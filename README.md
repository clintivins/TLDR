# BDO Digital news digest

This GitHub Action emails a daily digest of public news matching BDO Digital
in the UK, United States, and Canada. It uses Google News RSS, so no paid news
API is required.

## Setup

Add these repository secrets under **Settings -> Secrets and variables -> Actions**:

| Secret | Value |
| --- | --- |
| `NEWS_EMAIL_TO` | Address that should receive the digest |
| `SMTP_FROM` | Your Gmail sender address, such as `name@gmail.com` |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `465` for SSL or `587` for STARTTLS |
| `SMTP_USERNAME` | Your Gmail sender address |
| `SMTP_PASSWORD` | A Google app password, not your normal Gmail password |

For Gmail, enable 2-Step Verification and create an app password under your
Google Account security settings. Use that 16-character app password for
`SMTP_PASSWORD`.

The workflow runs at 07:00 Europe/London and can also be started manually from
the **Actions** tab. GitHub may delay scheduled workflows by several minutes.

The first run can be tested with **Run workflow** after the secrets are set.