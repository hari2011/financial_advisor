"""Cryptocurrency Analyst Agent."""
import json
from agents.base import BaseAgent, fmt_inr
from tools.market_data import get_crypto_price, get_stock_price
from tools.web_search import news_search


class CryptoAnalystAgent(BaseAgent):
    name = "Cryptocurrency Analyst"
    icon = "₿"
    description = "Crypto analysis, blockchain, DeFi, market trends, risk assessment"

    system_prompt = """Crypto Analyst for Indian investors. Be direct about risks and tax reality — many users underestimate the impact of India’s 30% crypto tax.

APPROACH: Assess experience → Market phase → Max 5% portfolio → Tax reality → DCA entry.
- India tax: 30% flat + 4% cess = 31.2%. 1% TDS >10K/yr. No loss set-off. No expense deduction.
- Due to 30% tax, frequent trading destroys returns. Buy and hold for cycles.
- Portfolio: BTC 50-60%, ETH 25-30%, 1-2 quality alts 10-20%. No memes.
- FOMO → strong caution. Life savings in crypto → redirect to balanced portfolio first.

FORMAT: Use PRE-COMPUTED data. ₹+$ dual pricing. Show tax impact with examples. End with: (1) allocation advice (2) specific coins if appropriate (3) clear **RISK WARNING**."""

    def gather_context(self, query: str) -> str:
        context_parts = []
        # ── Inject relevant financial knowledge ──
        knowledge = self.get_knowledge_context(query)
        if knowledge:
            context_parts.append(knowledge)
        query_lower = query.lower()
        numbers = self.extract_numbers(query)

        # Crypto mapping
        crypto_map = {
            "bitcoin": "BTC", "btc": "BTC",
            "ethereum": "ETH", "eth": "ETH",
            "solana": "SOL", "sol": "SOL",
            "cardano": "ADA", "ada": "ADA",
            "polkadot": "DOT", "dot": "DOT",
            "ripple": "XRP", "xrp": "XRP",
            "dogecoin": "DOGE", "doge": "DOGE",
            "avalanche": "AVAX", "avax": "AVAX",
            "polygon": "MATIC", "matic": "MATIC",
            "chainlink": "LINK", "link": "LINK",
            "litecoin": "LTC", "ltc": "LTC",
        }

        cryptos_found = []
        for name, symbol in crypto_map.items():
            if name in query_lower:
                cryptos_found.append(symbol)

        if not cryptos_found:
            cryptos_found = ["BTC", "ETH", "SOL"]

        for symbol in cryptos_found[:3]:  # Cap at 3
            data = get_crypto_price(symbol)
            if "error" not in data:
                # Summarize instead of JSON dump
                price = data.get("price_usd") or data.get("current_price")
                price_inr = data.get("price_inr")
                change_24h = data.get("change_24h_pct") or data.get("change_24h")
                mkt_cap = data.get("market_cap")

                lines = [f"CRYPTO: {symbol}"]
                if price:
                    lines.append(f"  Price: ${price:,.2f}")
                if price_inr:
                    lines.append(f"  Price (INR): ₹{price_inr:,.0f}")
                if change_24h:
                    lines.append(f"  24h Change: {change_24h:+.2f}%")
                if mkt_cap and isinstance(mkt_cap, (int, float)):
                    lines.append(f"  Market Cap: ${mkt_cap/1e9:,.1f}B")
                context_parts.append("\n".join(lines))

        # Pre-compute investment & tax calculations if user mentions amounts
        if numbers:
            num_labels = [fmt_inr(n) for n in numbers]
            context_parts.append(f"EXTRACTED AMOUNTS: {', '.join(num_labels)}")

            inv_amounts = [n for n in numbers if n >= 1000]
            if inv_amounts:
                amt = inv_amounts[0]
                context_parts.append(f"\nINVESTMENT ANALYSIS for {fmt_inr(amt)}:")

                # Recommended split: 80% BTC+ETH, 20% alts
                btc_alloc = round(amt * 0.50)
                eth_alloc = round(amt * 0.30)
                alt_alloc = round(amt * 0.20)
                context_parts.append(
                    f"  Suggested Split:\n"
                    f"    BTC (50%): {fmt_inr(btc_alloc)}\n"
                    f"    ETH (30%): {fmt_inr(eth_alloc)}\n"
                    f"    Alts (20%): {fmt_inr(alt_alloc)}"
                )

                # Tax scenarios
                for gain_pct in [25, 50, 100]:
                    gain = round(amt * gain_pct / 100)
                    tax = round(gain * 0.30)
                    tds = round((amt + gain) * 0.01)
                    net_gain = gain - tax
                    context_parts.append(
                        f"  If {gain_pct}% gain: Profit {fmt_inr(gain)} → "
                        f"Tax @30%: {fmt_inr(tax)}, TDS @1%: {fmt_inr(tds)}, "
                        f"Net gain: {fmt_inr(net_gain)}"
                    )

        # Get crypto news — derive search from user query
        search_q = f"{' '.join(cryptos_found[:2])} crypto India news 2025 2026"
        news = news_search(search_q)
        if news and "error" not in news[0]:
            context_parts.append("LATEST CRYPTO NEWS:")
            for n in news[:3]:
                context_parts.append(f"  • [{n.get('source', '')}] {n.get('title', '')}")

        return "\n\n".join(context_parts)
