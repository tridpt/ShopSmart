"""
Tool: Notifier — Gửi thông báo cho người dùng.
"""
import json
import traceback
from database.models import Notification


def send_notification(title: str, message: str, ntype: str = "info") -> str:
    """
    Tạo thông báo cho người dùng.

    Args:
        title: Tiêu đề thông báo
        message: Nội dung thông báo
        ntype: Loại thông báo (info, deal, alert, tracking)

    Returns:
        JSON string xác nhận
    """
    try:
        nid = Notification.create(title=title, message=message, ntype=ntype)
        return json.dumps({
            "success": True,
            "notification_id": nid,
            "message": "Đã gửi thông báo thành công."
        }, ensure_ascii=False)
    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "message": f"Lỗi gửi thông báo: {str(e)}"
        }, ensure_ascii=False)


TOOL_DEFINITION = {
    "name": "send_notification",
    "description": "Gửi thông báo cho người dùng. Sử dụng khi cần thông báo về deal tốt, giá giảm, hoặc cập nhật quan trọng.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Tiêu đề thông báo"
            },
            "message": {
                "type": "string",
                "description": "Nội dung chi tiết của thông báo"
            },
            "ntype": {
                "type": "string",
                "description": "Loại thông báo: 'info', 'deal', 'alert', 'tracking'",
                "enum": ["info", "deal", "alert", "tracking"]
            }
        },
        "required": ["title", "message"]
    }
}
