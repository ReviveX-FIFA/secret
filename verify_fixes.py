#!/usr/bin/env python3
import os
import sys

def verify_main_py():
    """Check if main.py has the fixes"""
    try:
        with open('main.py', 'r') as f:
            content = f.read()
            
        # Check for error handling in main()
        if 'try:' in content and 'Authentication system error' in content:
            print("Main.py: Authentication error handling - FIXED")
        else:
            print("Main.py: Authentication error handling - MISSING")
            
        # Check for error handling in __main__
        if 'FATAL ERROR' in content and 'Program ended' in content:
            print("Main.py: Main execution error handling - FIXED")
        else:
            print("Main.py: Main execution error handling - MISSING")
            
        return True
    except Exception as e:
        print(f"Error checking main.py: {e}")
        return False

def verify_run_bot():
    """Check if run_bot.bat has the fixes"""
    try:
        with open('run_bot.bat', 'r') as f:
            content = f.read()
            
        if 'main.py' in content and 'discord_bot.py' not in content:
            print("run_bot.bat: Points to main.py - FIXED")
        else:
            print("run_bot.bat: Still points to discord_bot.py - NOT FIXED")
            
        return True
    except Exception as e:
        print(f"Error checking run_bot.bat: {e}")
        return False

def verify_chat_py():
    """Check if chat.py has proper input methods"""
    try:
        with open('chat/chat.py', 'r') as f:
            content = f.read()
            
        # Check for get_channel method
        if 'def get_channel(self):' in content:
            print("Chat.py: Channel input method - EXISTS")
        else:
            print("Chat.py: Channel input method - MISSING")
            
        # Check for get_spam_mode method
        if 'def get_spam_mode(self):' in content:
            print("Chat.py: Spam mode input method - EXISTS")
        else:
            print("Chat.py: Spam mode input method - MISSING")
            
        # Check for get_messages method
        if 'def get_messages(self):' in content:
            print("Chat.py: Messages input method - EXISTS")
        else:
            print("Chat.py: Messages input method - MISSING")
            
        return True
    except Exception as e:
        print(f"Error checking chat.py: {e}")
        return False

def verify_keys():
    """Check if keys exist"""
    try:
        if os.path.exists('main_keys.txt'):
            with open('main_keys.txt', 'r') as f:
                keys = [line.strip() for line in f if line.strip()]
                if keys:
                    print(f"Keys: {len(keys)} keys available - OK")
                else:
                    print("Keys: No keys found - ISSUE")
        else:
            print("Keys: main_keys.txt not found - ISSUE")
        return True
    except Exception as e:
        print(f"Error checking keys: {e}")
        return False

if __name__ == "__main__":
    print("Verifying Bot Fixes...")
    print("=" * 50)
    
    print("\n1. Checking main.py fixes:")
    verify_main_py()
    
    print("\n2. Checking run_bot.bat fixes:")
    verify_run_bot()
    
    print("\n3. Checking chat.py functionality:")
    verify_chat_py()
    
    print("\n4. Checking authentication keys:")
    verify_keys()
    
    print("\n" + "=" * 50)
    print("Verification complete!")
    print("\nTo run the bot:")
    print("1. Use run_bot.bat (recommended)")
    print("2. Or run: py -3.11 main.py")
    print("\nTo use chat bot:")
    print("1. Authenticate with a key from main_keys.txt")
    print("2. Select option 1 for Chat Bot")
    print("3. Enter channel name")
    print("4. Select spam mode (regular/emote_only)")
    print("5. Enter messages (if not emote-only mode)")
    print("6. Set target count")
    
    input("\nPress Enter to exit...")
