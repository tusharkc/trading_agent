"""
Helper script to generate Kite access token.
Run this once to get your access token, then add it to .env file.
"""
import sys
import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect

load_dotenv()


def main():
    """Generate Kite access token."""
    print("\n" + "=" * 60)
    print("🔐 Kite Connect Access Token Generator")
    print("=" * 60 + "\n")

    # Get API credentials from .env
    api_key = os.getenv("KITE_API_KEY")
    api_secret = os.getenv("KITE_API_SECRET")

    if not api_key:
        print("❌ Error: KITE_API_KEY not found in .env file")
        print("\n📝 Please add your API key to .env:")
        print("   KITE_API_KEY=your_api_key_here")
        return 1

    if not api_secret:
        print("❌ Error: KITE_API_SECRET not found in .env file")
        print("\n📝 Please add your API secret to .env:")
        print("   KITE_API_SECRET=your_api_secret_here")
        print("\n💡 You can find your API secret by clicking 'Show API secret' in your Kite Connect app page")
        return 1

    try:
        # Initialize KiteConnect
        kite = KiteConnect(api_key=api_key)

        # Step 1: Generate login URL
        print("📋 Step 1: Generating Login URL...")
        print("-" * 60)
        login_url = kite.login_url()
        print(f"\n✅ Login URL generated successfully!")
        print(f"\n🔗 Please visit this URL in your browser:")
        print(f"\n   {login_url}\n")
        print("📝 Instructions:")
        print("   1. The URL will open Kite login page")
        print("   2. Login with your Zerodha credentials")
        print("   3. After login, you'll be redirected to a URL like:")
        print("      http://127.0.0.1:8080/callback?request_token=XXXXXX&action=login&status=success")
        print("   4. Copy the 'request_token' value from the URL\n")
        print("-" * 60)

        # Step 2: Get request token from user
        print("\n📥 Step 2: Enter Request Token")
        print("-" * 60)
        request_token = input("Paste the request_token here: ").strip()

        if not request_token:
            print("\n❌ Request token is required")
            return 1

        # Step 3: Generate access token
        print("\n🔄 Step 3: Generating Access Token...")
        print("-" * 60)
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]

        print(f"\n✅ SUCCESS! Access Token Generated!\n")
        print("=" * 60)
        print("📝 Next Steps:")
        print("=" * 60)
        print(f"\n1. Add this to your .env file:")
        print(f"\n   KITE_ACCESS_TOKEN={access_token}\n")
        print("2. Your .env file should now have:")
        print("   KITE_API_KEY=your_api_key")
        print("   KITE_API_SECRET=your_api_secret")
        print(f"   KITE_ACCESS_TOKEN={access_token}\n")
        print("⚠️  IMPORTANT NOTES:")
        print("   • Access tokens expire daily at 6 AM IST")
        print("   • You'll need to regenerate the token each trading day")
        print("   • Run this script again to get a new token when needed")
        print("   • Keep your API Secret and Access Token secure - never share them!\n")
        print("=" * 60 + "\n")

        # Optionally save to .env automatically
        save_choice = input("💾 Would you like to automatically update .env file? (y/n): ").strip().lower()
        if save_choice == 'y':
            env_file = ".env"
            if os.path.exists(env_file):
                # Read current .env
                with open(env_file, 'r') as f:
                    lines = f.readlines()

                # Update or add KITE_ACCESS_TOKEN
                updated = False
                with open(env_file, 'w') as f:
                    for line in lines:
                        if line.startswith("KITE_ACCESS_TOKEN="):
                            f.write(f"KITE_ACCESS_TOKEN={access_token}\n")
                            updated = True
                        else:
                            f.write(line)
                    
                    if not updated:
                        f.write(f"\nKITE_ACCESS_TOKEN={access_token}\n")

                print(f"\n✅ Updated {env_file} with access token!")
            else:
                print(f"\n⚠️  .env file not found. Please manually add the token.")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 Troubleshooting:")
        print("   • Verify your API Key and Secret are correct")
        print("   • Make sure you copied the request_token correctly")
        print("   • Request token expires quickly - generate it right after login")
        return 1


if __name__ == "__main__":
    exit(main())

