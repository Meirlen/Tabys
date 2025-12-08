"""
Mobizon SMS API Service
Documentation: https://api.mobizon.kz/
"""

import requests
from typing import Optional, Dict, Any
from config import get_settings
import logging

logger = logging.getLogger(__name__)

class MobizonService:
    """Service for sending SMS via Mobizon API"""

    BASE_URL = "https://api.mobizon.kz/service"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.MOBIZON_API_KEY

    def send_sms(self, phone: str, message: str, sender: str = None) -> Dict[str, Any]:
        """
        Send SMS via Mobizon API according to official documentation

        Args:
            phone: Phone number in international format (e.g., 77051234567)
            message: SMS text message
            sender: Optional sender name (alpha name, must be pre-registered)

        Returns:
            dict: API response with status and data
        """
        try:
            # Ensure phone is in correct format (digits only, no + sign)
            phone = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

            # Correct API endpoint according to documentation
            url = f"{self.BASE_URL}/message/sendSmsMessage"

            # Build data for form-encoded POST request
            data = {
                "recipient": phone,
                "text": message
            }

            # Add sender (from parameter) only if provided
            # Note: Sender must be pre-registered in Mobizon account
            if sender:
                data["from"] = sender

            # API key goes in URL params, data in request body
            params = {
                "output": "json",
                "api": "v1",
                "apiKey": self.api_key
            }

            logger.info(f"Sending SMS to {phone[:4]}****{phone[-2:]}")
            logger.debug(f"SMS data: recipient={phone}, text_length={len(message)}, from={sender}")

            # Use form-encoded POST as per documentation
            response = requests.post(
                url,
                params=params,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            response_data = response.json()

            logger.info(f"Mobizon response: {response_data}")

            # According to docs: code 0 means success
            if response_data.get("code") == 0:
                message_id = response_data.get("data", {}).get("messageId")
                campaign_id = response_data.get("data", {}).get("campaignId")
                logger.info(f"SMS sent successfully to {phone[:4]}****{phone[-2:]} (message_id: {message_id}, campaign_id: {campaign_id})")
                return {
                    "success": True,
                    "message": "SMS sent successfully",
                    "message_id": message_id,
                    "campaign_id": campaign_id
                }
            else:
                error_msg = response_data.get("message", "Unknown error")
                error_code = response_data.get("code")
                logger.error(f"Mobizon API error (code {error_code}): {error_msg}")
                logger.error(f"Full response: {response_data}")
                return {
                    "success": False,
                    "message": f"Failed to send SMS (code {error_code}): {error_msg}"
                }

        except requests.exceptions.Timeout:
            logger.error("Mobizon API timeout")
            return {
                "success": False,
                "message": "SMS service timeout"
            }
        except Exception as e:
            logger.error(f"Error sending SMS via Mobizon: {str(e)}")
            return {
                "success": False,
                "message": f"Error sending SMS: {str(e)}"
            }

    def send_otp(self, phone: str, otp_code: str) -> Dict[str, Any]:
        """
        Send OTP code via SMS

        Args:
            phone: Phone number
            otp_code: 6-digit OTP code

        Returns:
            dict: API response
        """
        # Simplified message format - some SMS providers are sensitive to special characters
        message = f"{otp_code} - SARYARQAJASTARY kod rastau"
        # Try without sender name first (more compatible)
        return self.send_sms(phone, message, sender=None)

    def check_balance(self) -> Optional[float]:
        """
        Check SMS balance

        Returns:
            float: Current balance or None if error
        """
        try:
            url = f"{self.BASE_URL}/user/getownbalance"
            params = {"apiKey": self.api_key}

            response = requests.get(url, params=params, timeout=10)
            response_data = response.json()

            if response_data.get("code") == 0:
                balance = response_data.get("data", {}).get("balance", 0)
                logger.info(f"Mobizon balance: {balance}")
                return float(balance)
            else:
                logger.error(f"Failed to check balance: {response_data.get('message')}")
                return None

        except Exception as e:
            logger.error(f"Error checking Mobizon balance: {str(e)}")
            return None


# Singleton instance
_mobizon_service: Optional[MobizonService] = None

def get_mobizon_service() -> MobizonService:
    """Get Mobizon service singleton instance"""
    global _mobizon_service
    if _mobizon_service is None:
        _mobizon_service = MobizonService()
    return _mobizon_service
