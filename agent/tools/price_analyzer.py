"""
Tool: Price Analyzer — Phân tích xu hướng giá sản phẩm.
"""
import json
import traceback
from database.models import Product, PriceHistory


def analyze_price(product_name: str) -> str:
    """
    Phân tích xu hướng giá của sản phẩm đang theo dõi.

    Args:
        product_name: Tên sản phẩm cần phân tích

    Returns:
        JSON string chứa phân tích giá
    """
    try:
        products = Product.search_by_name(product_name)
        if not products:
            return json.dumps({
                "success": False,
                "message": f"Không tìm thấy sản phẩm '{product_name}' trong danh sách theo dõi."
            }, ensure_ascii=False)

        product = products[0]
        stats = PriceHistory.get_stats(product["id"])
        history = PriceHistory.get_by_product(product["id"])

        # Calculate trend
        trend = "stable"
        change_percent = 0
        if len(history) >= 2:
            first_price = history[0]["price"]
            last_price = history[-1]["price"]
            if first_price > 0:
                change_percent = ((last_price - first_price) / first_price) * 100
                if change_percent > 2:
                    trend = "increasing"
                elif change_percent < -2:
                    trend = "decreasing"

        # Build analysis
        analysis = {
            "success": True,
            "product": {
                "id": product["id"],
                "name": product["name"],
                "current_price": product["current_price"],
                "target_price": product["target_price"],
            },
            "stats": {
                "min_price": stats["min_price"] if stats else None,
                "max_price": stats["max_price"] if stats else None,
                "avg_price": round(stats["avg_price"], 0) if stats and stats["avg_price"] else None,
                "total_records": stats["total_records"] if stats else 0,
            },
            "trend": trend,
            "change_percent": round(change_percent, 2),
            "recommendation": _get_recommendation(trend, change_percent, product),
            "history_count": len(history),
        }

        return json.dumps(analysis, ensure_ascii=False)

    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "message": f"Lỗi phân tích: {str(e)}"
        }, ensure_ascii=False)


def _get_recommendation(trend: str, change_pct: float, product: dict) -> str:
    """Generate a buying recommendation."""
    if trend == "decreasing" and change_pct < -5:
        return "🟢 Giá đang giảm mạnh. Đây có thể là thời điểm tốt để mua!"
    elif trend == "decreasing":
        return "🟡 Giá đang có xu hướng giảm nhẹ. Có thể chờ thêm."
    elif trend == "increasing" and change_pct > 5:
        return "🔴 Giá đang tăng mạnh. Nếu cần, nên mua sớm."
    elif trend == "increasing":
        return "🟠 Giá đang tăng nhẹ. Cân nhắc mua sớm."
    else:
        return "⚪ Giá ổn định. Không có biến động lớn."


TOOL_DEFINITION = {
    "name": "analyze_price",
    "description": "Phân tích xu hướng giá của sản phẩm đang theo dõi. Bao gồm giá min/max/trung bình, xu hướng tăng/giảm, và khuyến nghị mua hàng.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_name": {
                "type": "string",
                "description": "Tên sản phẩm cần phân tích (phải là sản phẩm đang được theo dõi)"
            }
        },
        "required": ["product_name"]
    }
}
