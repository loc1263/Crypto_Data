"""Order book L2 — snapshot único (métricas derivadas)."""

from ..exchange import init_exchange, spot_symbol


def fetch_orderbook_metrics(
    symbol: str,
    exchange_name: str = "binance",
    depth: int = 20,
) -> dict:
    """
    Retorna un dict con métricas del libro de órdenes en el momento de la llamada:
        OB_Spread           — ask_best − bid_best
        OB_Spread_%         — spread relativo al mid price
        OB_Mid_Price        — (bid_best + ask_best) / 2
        OB_Bid_Depth        — suma de cantidad en los primeros `depth` niveles bid
        OB_Ask_Depth        — suma de cantidad en los primeros `depth` niveles ask
        OB_Imbalance        — bid_depth / (bid_depth + ask_depth)  [0=presión vendedora, 1=compradora]
        OB_Bid_USDT_Depth   — profundidad bid en USDT
        OB_Ask_USDT_Depth   — profundidad ask en USDT
        OB_Timestamp        — timestamp del snapshot
    """
    exchange = init_exchange(exchange_name, "spot")
    ob = exchange.fetch_order_book(spot_symbol(symbol), limit=depth)

    bids = ob.get("bids", [])
    asks = ob.get("asks", [])
    if not bids or not asks:
        return {}

    bid_p, bid_q = bids[0]
    ask_p, ask_q = asks[0]
    mid = (bid_p + ask_p) / 2

    bid_depth = sum(q for _, q in bids[:depth])
    ask_depth = sum(q for _, q in asks[:depth])
    bid_usdt  = sum(p * q for p, q in bids[:depth])
    ask_usdt  = sum(p * q for p, q in asks[:depth])
    total_depth = bid_depth + ask_depth

    return {
        "OB_Spread":         round(ask_p - bid_p, 8),
        "OB_Spread_%":       round((ask_p - bid_p) / mid * 100, 6) if mid else None,
        "OB_Mid_Price":      round(mid, 8),
        "OB_Bid_Depth":      round(bid_depth, 4),
        "OB_Ask_Depth":      round(ask_depth, 4),
        "OB_Imbalance":      round(bid_depth / total_depth, 6) if total_depth else None,
        "OB_Bid_USDT_Depth": round(bid_usdt, 2),
        "OB_Ask_USDT_Depth": round(ask_usdt, 2),
        "OB_Timestamp":      ob.get("timestamp"),
    }
