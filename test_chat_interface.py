#!/usr/bin/env python3
import sys
import os

# Add chat directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'chat'))

def test_chat_interface():
    """Test the chat bot interface methods"""
    try:
        import chat
        bot = chat.Spammer()
        
        print("Testing Chat Bot Interface...")
        print("=" * 50)
        
        # Test 1: Check if methods exist
        print("\n1. Checking method existence:")
        methods_to_check = ['get_channel', 'get_spam_mode', 'get_messages', 'get_target_count']
        for method in methods_to_check:
            if hasattr(bot, method):
                print(f"   {method}: EXISTS")
            else:
                print(f"   {method}: MISSING")
                return False
        
        # Test 2: Check if banner is removed
        print("\n2. Checking banner removal:")
        with open('chat/chat.py', 'r') as f:
            content = f.read()
            if 'clear_screen()' not in content.split('async def run')[1].split('async def')[0]:
                print("   clear_screen(): REMOVED from run method")
            else:
                print("   clear_screen(): STILL PRESENT in run method")
            
            if 'BANNER' not in content.split('async def run')[1].split('async def')[0]:
                print("   BANNER: REMOVED from run method")
            else:
                print("   BANNER: STILL PRESENT in run method")
        
        # Test 3: Check channel input method
        print("\n3. Checking channel input method:")
        with open('chat/chat.py', 'r') as f:
            content = f.read()
            if 'Enter channel name:' in content and 'Channel:' in content:
                print("   Channel input: FIXED")
            else:
                print("   Channel input: STILL BROKEN")
        
        print("\n" + "=" * 50)
        print("Interface test completed!")
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_chat_interface()
    
    print(f"\nUsage Instructions:")
    print(f"1. Run main.py or run_bot.bat")
    print(f"2. Authenticate with a key")
    print(f"3. Select option 1 for Chat Bot")
    print(f"4. The chat bot will now:")
    print(f"   - NOT clear the screen")
    print(f"   - NOT show the ReviveX banner")
    print(f"   - Show clean interface for channel input")
    print(f"   - Accept channel name properly")
    print(f"   - Continue with mode selection")
    
    input(f"\nPress Enter to exit...")
