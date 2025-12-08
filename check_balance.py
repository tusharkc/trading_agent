#!/usr/bin/env python3
"""
Script to check Zerodha account balance.
"""

import sys
from app.shared.config import config
from app.domains.trading.kite_client import KiteClient
from app.shared.logger import logger


def main():
    """Check and display account balance."""
    try:
        print("\n" + "=" * 60)
        print("💰 Zerodha Account Balance Check")
        print("=" * 60 + "\n")

        # Validate configuration
        if not config.KITE_API_KEY:
            print("❌ Error: KITE_API_KEY not found in .env file")
            return 1

        if not config.KITE_ACCESS_TOKEN:
            print("❌ Error: KITE_ACCESS_TOKEN not found in .env file")
            print("💡 Run: python generate_kite_token.py")
            return 1

        # Initialize Kite client
        print("🔌 Connecting to Zerodha Kite API...")
        client = KiteClient()

        # Get account profile
        print("📊 Fetching account information...")
        profile = client.kite.profile()
        print(f"✅ Connected as: {profile.get('user_name', 'N/A')}")
        print(f"   Email: {profile.get('email', 'N/A')}\n")

        # Get account balance
        print("💰 Fetching account balance...")
        available_capital = client.get_available_capital()

        print("\n" + "=" * 60)
        print("💵 ACCOUNT BALANCE")
        print("=" * 60)
        print(f"Available Capital: ₹{available_capital:,.2f}")
        print("=" * 60 + "\n")

        # Get detailed margins
        margins = client.get_margins()
        equity = margins.get("equity", {})
        available = equity.get("available", {})

        if available:
            print("📊 Detailed Margin Information:")
            print("-" * 60)
            if "cash" in available:
                print(f"Available Cash: ₹{float(available['cash']):,.2f}")
            if "opening_balance" in available:
                print(f"Opening Balance: ₹{float(available['opening_balance']):,.2f}")
            if "collateral" in available:
                print(f"Collateral: ₹{float(available['collateral']):,.2f}")
            if "intraday_payin" in available:
                print(f"Intraday Payin: ₹{float(available['intraday_payin']):,.2f}")

            if "net" in equity:
                net_equity = float(equity.get("net", 0))
                print(f"\nNet Equity: ₹{net_equity:,.2f}")
            print("-" * 60 + "\n")

        # Get holdings info
        try:
            holdings = client.get_holdings()
            if holdings:
                total_holdings_value = sum(
                    float(h.get("quantity", 0)) * float(h.get("average_price", 0))
                    for h in holdings
                    if h.get("quantity", 0) > 0
                )
                if total_holdings_value > 0:
                    print(
                        f"📈 Holdings Value: ₹{total_holdings_value:,.2f} ({len(holdings)} positions)"
                    )
        except:
            pass

        # Warning if balance is too low
        if available_capital < 1000:
            print("\n⚠️  WARNING: Available cash is very low!")
            print(f"   Available Cash: ₹{available_capital:,.2f}")
            if equity.get("net"):
                net_equity = float(equity.get("net", 0))
                print(f"   Net Equity: ₹{net_equity:,.2f}")
                if net_equity > available_capital:
                    print("\n💡 Your funds might be:")
                    print("   • Used in existing positions")
                    print("   • Locked in pending orders")
                    print("   • Not yet settled")
                    print("   • Check your holdings on Zerodha Kite app\n")
            print(f"   Minimum recommended: ₹1,000 for trading")
            print("   Please ensure you have sufficient available cash.\n")

        return 0

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Possible solutions:")
        print("   1. Check if your account is funded")
        print("   2. Verify KITE_ACCESS_TOKEN is valid (may need to regenerate)")
        print("   3. Run: python generate_kite_token.py to get a new token")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
