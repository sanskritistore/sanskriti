"""
SMS सेंडर - स्वैप करने योग्य ईंट (swappable brick)

वास्तुकला नियम: असली SMS प्रदाता (MSG91/Twilio) बाद में
इसी अनुबंध (contract) के पीछे जुड़ेगा - बाक़ी सिस्टम पर
एक शब्द नहीं बदलेगा।

असली प्रदाता जोड़ने के लिए:
1. नई क्लास बनाएँ, जैसे class Msg91SmsSender(BaseSmsSender)
2. send_otp() में प्रदाता का API कॉल करें
3. नीचे get_sms_sender() में सेटिंग से चुनें
बस! auth routes को कुछ नहीं बदलना पड़ेगा।
"""

from abc import ABC, abstractmethod


class BaseSmsSender(ABC):
    """SMS प्रदाता का अनुबंध - हर प्रदाता यही पूरा करेगा।"""

    @abstractmethod
    async def send_otp(self, phone: str, otp: str) -> bool:
        """OTP वाला SMS भेजें। सफलता पर True, विफलता पर False।"""
        ...


class StubSmsSender(BaseSmsSender):
    """
    MVP स्टब - SMS नहीं भेजता, सिर्फ़ लॉग करता है।

    डेवलपमेंट में OTP_DEV_MODE=true होने पर OTP
    API उत्तर में भी मिल जाता है, इसलिए टेस्ट आसान है।
    """

    async def send_otp(self, phone: str, otp: str) -> bool:
        # स्टब: असली SMS गेटवे बाद में जुड़ेगा (MSG91/Twilio)
        import logging

        logging.getLogger("sanskriti.sms").info(
            "OTP स्टब SMS: phone=%s otp=%s (असली गेटवे अभी नहीं जुड़ा)", phone, otp
        )
        return True


# सिंगलटन स्टब - असली प्रदाता आने पर सेटिंग से चुना जाएगा
_sms_sender: BaseSmsSender | None = None


def get_sms_sender() -> BaseSmsSender:
    """वर्तमान SMS प्रदाता लौटाएँ।

    भविष्य में: सेटिंग SMS_PROVIDER ("msg91" | "twilio" | "stub")
    से यहाँ प्रदाता चुना जाएगा - सिर्फ़ यही फ़ंक्शन बदलेगा।
    """
    global _sms_sender
    if _sms_sender is None:
        _sms_sender = StubSmsSender()
    return _sms_sender
