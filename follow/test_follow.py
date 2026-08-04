#!/usr/bin/env python3
"""
Test script for the Twitch Follow Bot
This demonstrates that the follow functionality is working correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from follow import TwitchFollower
import time

def test_follow_bot():
    print("=" * 60)
    print("TWITCH FOLLOW BOT - TEST RUN")
    print("=" * 60)
    
    # Initialize the bot
    bot = TwitchFollower(print)
    
    # Test parameters
    test_username = "testuser"
    test_count = 3
    
    print(f"\n🎯 Testing with:")
    print(f"   Username: {test_username}")
    print(f"   Follow count: {test_count}")
    
    # Load tokens and proxies directly
    from follow import load_tokens, load_proxies
    tokens = load_tokens()
    proxies = load_proxies()
    
    print(f"   Available tokens: {len(tokens)}")
    print(f"   Available proxies: {len(proxies)}")
    
    # Start the follow operation
    print(f"\n🚀 Starting follow operation...")
    thread = bot.start(test_username, test_count)
    
    # Wait for completion
    while bot.running:
        time.sleep(0.5)
    
    print(f"\n✅ Test completed!")
    print(f"   Final count: {bot.follow_counter}/{test_count}")
    
    if bot.follow_counter == test_count:
        print("   🎉 SUCCESS: All follows completed successfully!")
        return True
    else:
        print("   ⚠️  PARTIAL: Some follows may have failed")
        return False

if __name__ == "__main__":
    success = test_follow_bot()
    sys.exit(0 if success else 1)
