#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

import discord_bot

# Create bot instance
bot = discord_bot.TwitchBotDiscord()

# Get all commands
commands = bot.tree.get_commands()
print("=== REGISTERED COMMANDS ===")
for cmd in commands:
    print(f"- /{cmd.name}: {cmd.description}")
print(f"\nTotal commands: {len(commands)}")

# Check specifically for our new commands
event_cmd = None
tfollow_cmd = None

for cmd in commands:
    if cmd.name == "event":
        event_cmd = cmd
    elif cmd.name == "tfollow":
        tfollow_cmd = cmd

print(f"\n=== EVENT COMMANDS ===")
print(f"Event command found: {event_cmd is not None}")
print(f"Tfollow command found: {tfollow_cmd is not None}")

if event_cmd:
    print(f"Event command: {event_cmd.name} - {event_cmd.description}")
if tfollow_cmd:
    print(f"Tfollow command: {tfollow_cmd.name} - {tfollow_cmd.description}")
