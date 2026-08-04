#!/usr/bin/env python3
import discord
from discord_bot import bot

# Check if commands are registered
commands = bot.tree.get_commands()
print(f"Total commands registered: {len(commands)}")
for cmd in commands:
    print(f"- /{cmd.name}: {cmd.description}")
