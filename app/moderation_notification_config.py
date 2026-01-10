"""
Moderation Notification Configuration

Configure how often to check for new moderation items and send notifications
"""

# How often to check moderation queue (in minutes)
# Default: 5 minutes
# For testing, you can set to 1 minute
MODERATION_CHECK_INTERVAL_MINUTES: int = 1

# CRM URL for moderation page
# This URL will be used in the inline keyboard button
CRM_MODERATION_URL: str = "https://soft09.tech/kz/admin/moderation"

# Notification message template (supports Kazakh and Russian)
NOTIFICATION_MESSAGE_KZ = """🚨 Жаңа модерация өтінімдері

Күтілуде: {count} өтінім

CRM-де қарап шығуыңызды сұраймыз."""

NOTIFICATION_MESSAGE_RU = """🚨 Новые заявки на модерацию

Ожидают проверки: {count} заявок

Пожалуйста, проверьте их в CRM."""

# Default to Russian for notifications
NOTIFICATION_MESSAGE = NOTIFICATION_MESSAGE_RU

# Broadcast title
BROADCAST_TITLE = "Уведомление о модерации"

# Inline keyboard button text
BUTTON_TEXT_KZ = "📋 Модерацияны қарау"
BUTTON_TEXT_RU = "📋 Проверить модерацию"
BUTTON_TEXT = BUTTON_TEXT_RU
