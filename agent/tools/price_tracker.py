"""
Tool: Price Tracker — Theo dõi giá sản phẩm trong database.
"""
import json
import traceback
from database.models import Product, Notification


def track_price(product_name: str, url: str = None,
                current_price: float = None, target_price: float = None,
                source: str = None) -> str:
    """
    Thêm sản phẩm vào danh sách theo dõi giá.

    Args:
        product_name: Tên sản phẩm
        url: URL sản phẩm (tùy chọn)
        current_price: Giá hiện tại (tùy chọn)
        target_price: Giá mong muốn để nhận thông báo (tùy chọn)
        source: Nguồn (shopee, tiki, lazada...) (tùy chọn)

    Returns:
        JSON string xác nhận đã thêm vào theo dõi
    """
    try:
        product_id = Product.create(
            name=product_name,
            url=url,
            source=source,
            current_price=current_price,
            target_price=target_price
        )

        # Create notification
        price_str = f"{current_price:,.0f}đ" if current_price else "chưa rõ"
        Notification.create(
            title="📌 Sản phẩm mới được theo dõi",
            message=f"Đã thêm '{product_name}' vào danh sách theo dõi. Giá hiện tại: {price_str}",
            product_id=product_id,
            ntype="tracking"
        )

        return json.dumps({
            "success": True,
            "product_id": product_id,
            "message": f"Đã thêm '{product_name}' vào danh sách theo dõi giá.",
            "product": {
                "id": product_id,
                "name": product_name,
                "url": url,
                "current_price": current_price,
                "target_price": target_price,
                "source": source
            }
        }, ensure_ascii=False)

    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "message": f"Lỗi khi thêm sản phẩm: {str(e)}"
        }, ensure_ascii=False)


def get_tracked_products() -> str:
    """
    Lấy danh sách tất cả sản phẩm đang theo dõi.

    Returns:
        JSON string chứa danh sách sản phẩm
    """
    try:
        products = Product.get_all()
        return json.dumps({
            "success": True,
            "total": len(products),
            "products": products
        }, ensure_ascii=False)
    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "message": f"Lỗi: {str(e)}"
        }, ensure_ascii=False)


TOOL_DEFINITIONS = [
    {
        "name": "track_price",
        "description": "Thêm sản phẩm vào danh sách theo dõi giá. Sử dụng khi người dùng muốn theo dõi giá một sản phẩm để nhận thông báo khi giá giảm.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Tên sản phẩm cần theo dõi"
                },
                "url": {
                    "type": "string",
                    "description": "URL trang sản phẩm (nếu có)"
                },
                "current_price": {
                    "type": "number",
                    "description": "Giá hiện tại của sản phẩm (VND)"
                },
                "target_price": {
                    "type": "number",
                    "description": "Giá mong muốn để nhận thông báo khi giá giảm đến mức này (VND)"
                },
                "source": {
                    "type": "string",
                    "description": "Nguồn bán hàng (vd: 'shopee', 'tiki', 'lazada', 'cellphones')"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "get_tracked_products",
        "description": "Lấy danh sách tất cả sản phẩm đang được theo dõi giá. Sử dụng khi người dùng muốn xem các sản phẩm đã thêm vào theo dõi.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]
