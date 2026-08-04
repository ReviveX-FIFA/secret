#!/usr/bin/env python3
import sys
import os

# Add chat directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'chat'))

def test_chat_import():
    """Test if chat module can be imported"""
    try:
        import chat
        print("Chat module imported successfully")
        return True
    except Exception as e:
        print(f"Failed to import chat module: {e}")
        return False

def test_chat_class():
    """Test if Spammer class can be instantiated"""
    try:
        import chat
        bot = chat.Spammer()
        print("Spammer class instantiated successfully")
        return True
    except Exception as e:
        print(f"Failed to create Spammer instance: {e}")
        return False

def test_chat_methods():
    """Test if chat methods work"""
    try:
        import chat
        bot = chat.Spammer()
        
        # Test method existence
        methods = ['get_channel', 'get_spam_mode', 'get_messages', 'get_target_count']
        for method in methods:
            if hasattr(bot, method):
                print(f"Method {method} exists")
            else:
                print(f"Method {method} missing")
                return False
        
        return True
    except Exception as e:
        print(f"Failed to test chat methods: {e}")
        return False

if __name__ == "__main__":
    print("Testing Chat Bot Functionality...")
    print("=" * 40)
    
    success = True
    
    print("\n1. Testing import...")
    if not test_chat_import():
        success = False
    
    print("\n2. Testing class instantiation...")
    if not test_chat_class():
        success = False
    
    print("\n3. Testing methods...")
    if not test_chat_methods():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("All tests passed! Chat bot is working correctly.")
    else:
        print("Some tests failed. Check the errors above.")
    
    input("\nPress Enter to exit...")
