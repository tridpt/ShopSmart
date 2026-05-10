"""
Tool: Web Search — Tìm kiếm sản phẩm trên internet.
Uses DuckDuckGo search (free, no API key required).
"""
import json
import traceback
from duckduckgo_search import DDGS


def search_product(query: str, max_results: int = 8) -> str:
    """
    Tìm kiếm sản phẩm trên internet và trả về danh sách kết quả với giá.

    Args:
        query: Tên sản phẩm cần tìm (vd: "iPhone 16 128GB giá")
        max_results: Số lượng kết quả tối đa (mặc định 8)

    Returns:
        JSON string chứa danh sách kết quả tìm kiếm
    """
    try:
        # Enhance query for price comparison
        enhanced_query = f"{query} giá bán mua"

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(enhanced_query, region="vn-vi", max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

        if not results:
            return json.dumps({
                "success": False,
                "message": f"Không tìm thấy kết quả cho '{query}'",
                "results": []
            }, ensure_ascii=False)

        return json.dumps({
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results
        }, ensure_ascii=False)

    except Exception as e:
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "message": f"Lỗi khi tìm kiếm: {str(e)}",
            "results": []
        }, ensure_ascii=False)


# Tool definition for Gemini function calling
TOOL_DEFINITION = {
    "name": "search_product",
    "description": "Tìm kiếm sản phẩm trên internet. Sử dụng khi người dùng muốn tìm sản phẩm, so sánh giá, hoặc tìm deal tốt. Trả về danh sách kết quả với tiêu đề, link và mô tả.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Tên sản phẩm hoặc từ khóa tìm kiếm (vd: 'iPhone 16 128GB', 'laptop gaming dưới 20 triệu')"
            },
            "max_results": {
                "type": "integer",
                "description": "Số lượng kết quả tối đa (mặc định 8)"
            }
        },
        "required": ["query"]
    }
}
