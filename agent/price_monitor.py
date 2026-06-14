"""
Price Monitor — Background service tự động cập nhật giá sản phẩm đang theo dõi.

Chạy trong một daemon thread, định kỳ scrape lại giá của các sản phẩm có URL,
ghi vào lịch sử giá, và tạo thông báo khi giá giảm hoặc chạm mức mục tiêu.
"""
import json
import threading
import time
import traceback

import config
from database.models import Product, Notification
from agent.tools.price_scraper import scrape_price


_monitor_thread = None
_stop_event = threading.Event()


def _format_vnd(value) -> str:
    try:
        return f"{float(value):,.0f}đ".replace(",", ".")
    except (TypeError, ValueError):
        return "chưa rõ"


def check_product(product: dict) -> dict | None:
    """
    Scrape lại giá cho một sản phẩm và cập nhật nếu giá thay đổi.

    Returns:
        dict mô tả thay đổi nếu có cập nhật, ngược lại None.
    """
    url = product.get("url")
    if not url:
        return None

    raw = scrape_price(url)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    if not data.get("success") or data.get("price") is None:
        return None

    new_price = float(data["price"])
    old_price = product.get("current_price")

    # Không có thay đổi -> bỏ qua (vẫn coi là quét thành công).
    if old_price is not None and float(old_price) == new_price:
        return {"product_id": product["id"], "changed": False, "price": new_price}

    Product.update_price(product["id"], new_price, source=product.get("source"))

    change = {
        "product_id": product["id"],
        "name": product["name"],
        "changed": True,
        "old_price": old_price,
        "new_price": new_price,
    }

    # Tạo thông báo phù hợp.
    target = product.get("target_price")
    if target is not None and new_price <= float(target):
        Notification.create(
            title="🎯 Giá đã chạm mục tiêu!",
            message=f"'{product['name']}' hiện còn {_format_vnd(new_price)} "
                    f"(mục tiêu {_format_vnd(target)}). Thời điểm tốt để mua!",
            product_id=product["id"],
            ntype="deal",
        )
    elif old_price is not None and new_price < float(old_price):
        Notification.create(
            title="📉 Giá giảm",
            message=f"'{product['name']}' giảm từ {_format_vnd(old_price)} "
                    f"xuống {_format_vnd(new_price)}.",
            product_id=product["id"],
            ntype="alert",
        )

    return change


def run_once() -> int:
    """Quét toàn bộ sản phẩm đang theo dõi một lần. Trả về số sản phẩm có cập nhật."""
    updated = 0
    try:
        products = Product.get_all()
    except Exception:
        traceback.print_exc()
        return 0

    for product in products:
        if _stop_event.is_set():
            break
        if not product.get("url"):
            continue
        try:
            result = check_product(product)
            if result and result.get("changed"):
                updated += 1
                print(f"  [PRICE] Updated '{product['name']}': "
                      f"{result.get('old_price')} -> {result.get('new_price')}")
        except Exception:
            traceback.print_exc()
        # Nghỉ giữa các sản phẩm để tránh bị rate-limit.
        _stop_event.wait(config.PRICE_MONITOR_PER_ITEM_DELAY)

    return updated


def _monitor_loop():
    print(f"[OK] Price monitor started (interval={config.PRICE_MONITOR_INTERVAL}s).")
    # Đợi một chút sau khi khởi động.
    if _stop_event.wait(config.PRICE_MONITOR_INITIAL_DELAY):
        return
    while not _stop_event.is_set():
        try:
            count = run_once()
            if count:
                print(f"[PRICE] Monitor cycle complete: {count} product(s) updated.")
        except Exception:
            traceback.print_exc()
        # Đợi tới chu kỳ kế tiếp (có thể bị ngắt bởi stop()).
        if _stop_event.wait(config.PRICE_MONITOR_INTERVAL):
            break


def start_monitor():
    """Khởi động background monitor (idempotent)."""
    global _monitor_thread
    if not config.PRICE_MONITOR_ENABLED:
        print("[INFO] Price monitor disabled (PRICE_MONITOR_ENABLED=false).")
        return
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _stop_event.clear()
    _monitor_thread = threading.Thread(
        target=_monitor_loop, name="price-monitor", daemon=True
    )
    _monitor_thread.start()


def stop_monitor():
    """Dừng background monitor."""
    _stop_event.set()
