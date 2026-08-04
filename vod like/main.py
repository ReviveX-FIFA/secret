import httpx
import asyncio
import json
import os
import sys
import random
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

GQL_URL = "https://gql.twitch.tv/gql"
TOKENS_PATH = "tokens.txt"
PROXIES_PATH = "proxies.txt"
CLIENT_ID = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"
CLIENT_VERSION = "d1cb2181-c708-4417-b0b6-7fe7ddd78637"

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/144.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:118.0) Gecko/20100101 Firefox/118.0'
]

def load_proxies():
    proxies = []
    if os.path.exists(PROXIES_PATH):
        with open(PROXIES_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)
    return proxies

async def get_channel_id(client, username):
    headers = {
        'client-id': CLIENT_ID,
        'content-type': 'text/plain;charset=UTF-8',
        'user-agent': random.choice(USER_AGENTS),
    }
    payload = [{
        "operationName": "GetIDFromLogin",
        "variables": {"login": username.lower()},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "94e82a7b1e3c21e186daa73ee2afc4b8f23bade1fbbff6fe8ac133f50a2f58ca"
            }
        }
    }]
    try:
        response = await client.post(GQL_URL, headers=headers, content=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            if data and data[0].get('data', {}).get('user'):
                return data[0]['data']['user']['id']
    except:
        pass
    return None

async def get_channel_from_video(client, video_id):
    headers = {
        'client-id': CLIENT_ID,
        'content-type': 'text/plain;charset=UTF-8',
        'user-agent': random.choice(USER_AGENTS),
    }
    payload = [{
        "operationName": "VideoMetadata",
        "variables": {"videoID": video_id},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "cb3b1eb2d030e247f23d0fd3ac69b9876273c901854518f004b814d5878c9488"
            }
        }
    }]
    try:
        response = await client.post(GQL_URL, headers=headers, content=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            if data and data[0].get('data', {}).get('video'):
                return data[0]['data']['video']['owner']['id']
    except:
        pass
    return None

async def get_channel_from_clip(client, clip_id, channel_name=None):
    # If we have the channel name, get channel ID directly
    if channel_name:
        return await get_channel_id(client, channel_name)
    
    # Otherwise try to get it from clip metadata (limited queries available)
    headers = {
        'client-id': CLIENT_ID,
        'content-type': 'text/plain;charset=UTF-8',
        'user-agent': random.choice(USER_AGENTS),
    }
    payload = [{
        "operationName": "VideoAccessToken_Clip",
        "variables": {"slug": clip_id},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11"
            }
        }
    }]
    try:
        response = await client.post(GQL_URL, headers=headers, content=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            if data and data[0].get('data', {}).get('clip'):
                # This query doesn't return channel info, so we can't get it this way
                pass
    except Exception as e:
        print(f"Error getting clip info: {e}")
    return None

async def like_content(client, token, channel_id, content_id, content_type="VIDEO"):
    headers = {
        'authorization': f'OAuth {token}',
        'client-id': CLIENT_ID,
        'client-version': CLIENT_VERSION,
        'content-type': 'text/plain;charset=UTF-8',
        'user-agent': random.choice(USER_AGENTS),
        'x-device-id': ''.join(random.choices('0123456789abcdef', k=32)),
    }

    payload = [{
        "operationName": "updateReactionByContentKey",
        "variables": {
            "input": {
                "channelID": channel_id,
                "contentID": content_id,
                "contentType": content_type,
                "reactionType": "LIKE"
            }
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "968a80753fdb112103c273fa7cfb202ee7709f92920822e73cda120427daa5bf"
            }
        }
    }]
    
    try:
        response = await client.post(GQL_URL, headers=headers, content=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            # Check if the like was successful
            if data and len(data) > 0 and data[0].get('data', {}).get('updateReactionByContentKey'):
                return True
            else:
                return False
        else:
            return False
    except Exception as e:
        return False

def load_tokens():
    if not os.path.exists(TOKENS_PATH):
        print("tokens.txt not found")
        return []
    
    with open(TOKENS_PATH, "r") as f:
        tokens = [line.strip().replace("oauth:", "").strip() for line in f if line.strip()]
    return tokens

async def main():
    print("TWITCH CONTENT LIKER - FAST (VODs & Clips)")
    print("="*40)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Non-interactive mode
        vod_url = sys.argv[1] if len(sys.argv) > 1 else ""
        amount = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        
        if not vod_url:
            print("VOD URL required")
            return
        
        # Extract content ID, channel name, and determine type from URL
        content_type = "VIDEO"
        channel_name = None
        if '/videos/' in vod_url:
            video_id = vod_url.split('/videos/')[1].split('?')[0]
            content_type = "VIDEO"
            # Extract channel name from URL like https://www.twitch.tv/channelname/videos/...
            if 'twitch.tv/' in vod_url:
                parts = vod_url.split('twitch.tv/')[1].split('/')
                if len(parts) > 0:
                    channel_name = parts[0]
        elif '/clip/' in vod_url:
            video_id = vod_url.split('/clip/')[1].split('?')[0]
            content_type = "CLIP"
            # Extract channel name from URL like https://www.twitch.tv/channelname/clip/...
            if 'twitch.tv/' in vod_url:
                parts = vod_url.split('twitch.tv/')[1].split('/')
                if len(parts) > 0:
                    channel_name = parts[0]
        elif vod_url.startswith('https://') and 'twitch.tv' in vod_url:
            # Handle other Twitch URL formats
            parts = vod_url.split('/')
            if len(parts) > 3:
                video_id = parts[-1].split('?')[0]
                # Check if it looks like a clip ID (longer, contains hyphens)
                if len(video_id) > 20 and '-' in video_id:
                    content_type = "CLIP"
                else:
                    content_type = "VIDEO"
                # Extract channel name
                if 'twitch.tv/' in vod_url:
                    channel_name = vod_url.split('twitch.tv/')[1].split('/')[0]
            else:
                video_id = vod_url.split('?')[0]
                content_type = "VIDEO"
        else:
            video_id = vod_url
            # Default to VIDEO unless it looks like a clip
            if len(video_id) > 20 and '-' in video_id:
                content_type = "CLIP"
            else:
                content_type = "VIDEO"
        
        print(f"Extracted {content_type} ID: {video_id}")
        if channel_name:
            print(f"Channel name: {channel_name}")
        
        # Load tokens
        tokens = load_tokens()
        if not tokens:
            print("No tokens found")
            return
        
        amount = min(amount, len(tokens))
        
        # Get channel ID from content first
        print(f"Getting {content_type.lower()} info for {video_id}...")
        
        # Create async client
        limits = httpx.Limits(max_keepalive_connections=200, max_connections=300)  # Increased limits
        async with httpx.AsyncClient(limits=limits, timeout=5.0, http2=False) as client:
            if content_type == "VIDEO":
                channel_id = await get_channel_from_video(client, video_id)
            else:  # CLIP
                channel_id = await get_channel_from_clip(client, video_id, channel_name)
                
            if not channel_id:
                print(f"Could not get channel ID from {content_type.lower()}")
                return
            
            print(f"Channel ID: {channel_id}")
            print(f"Liking {content_type.lower()} {video_id} with {amount} likes...")
            
            # Start liking
            stats = {'success': 0, 'failed': 0, 'total': 0}
            start_time = time.time()
            
            # Process in batches to prevent overwhelming
            batch_size = 200  # Increased from 100 for faster processing
            total_batches = (amount + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, amount)
                batch_tokens = tokens[start_idx:end_idx]
                
                print(f"\nProcessing batch {batch_num + 1}/{total_batches} ({len(batch_tokens)} likes)...")
                
                # Create tasks for this batch
                tasks = []
                for token in batch_tokens:
                    task = asyncio.create_task(like_content(client, token, channel_id, video_id, content_type))
                    tasks.append(task)
                
                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, bool):
                        if result:
                            stats['success'] += 1
                        else:
                            stats['failed'] += 1
                    else:
                        stats['failed'] += 1
                    
                    stats['total'] += 1
                
                # Show progress after each batch
                elapsed = time.time() - start_time
                rate = stats['success'] / elapsed if elapsed > 0 else 0
                print(f"Batch complete: {stats['success']}/{stats['total']} | Failed: {stats['failed']} | Rate: {rate:.0f}/s")
                
                # Reduced delay between batches for faster processing
                if batch_num < total_batches - 1:
                    await asyncio.sleep(0.2)  # Reduced from 1.0 to 0.2
        
        # Results
        print(f"\nCompleted in {time.time() - start_time:.1f} seconds")
        print(f"Successful likes: {stats['success']}/{amount}")
        print(f"Failed likes: {stats['failed']}")
        
        if stats['success'] > 0:
            print(f"Speed: {stats['success']/(time.time() - start_time):.1f}/s")
    else:
        # Interactive mode
        tokens = load_tokens()
        if not tokens:
            print("No tokens found")
            return
        
        print(f"Available tokens: {len(tokens)}")
        
        video_url = input("Video URL: ").strip()
        
        # Extract content ID, channel name, and determine type from URL
        content_type = "VIDEO"
        channel_name = None
        if '/videos/' in video_url:
            video_id = video_url.split('/videos/')[1].split('?')[0]
            content_type = "VIDEO"
            # Extract channel name from URL like https://www.twitch.tv/channelname/videos/...
            if 'twitch.tv/' in video_url:
                parts = video_url.split('twitch.tv/')[1].split('/')
                if len(parts) > 0:
                    channel_name = parts[0]
        elif '/clip/' in video_url:
            video_id = video_url.split('/clip/')[1].split('?')[0]
            content_type = "CLIP"
            # Extract channel name from URL like https://www.twitch.tv/channelname/clip/...
            if 'twitch.tv/' in video_url:
                parts = video_url.split('twitch.tv/')[1].split('/')
                if len(parts) > 0:
                    channel_name = parts[0]
        elif video_url.startswith('https://') and 'twitch.tv' in video_url:
            # Handle other Twitch URL formats
            parts = video_url.split('/')
            if len(parts) > 3:
                video_id = parts[-1].split('?')[0]
                # Check if it looks like a clip ID (longer, contains hyphens)
                if len(video_id) > 20 and '-' in video_id:
                    content_type = "CLIP"
                else:
                    content_type = "VIDEO"
                # Extract channel name
                if 'twitch.tv/' in video_url:
                    channel_name = video_url.split('twitch.tv/')[1].split('/')[0]
            else:
                video_id = video_url.split('?')[0]
                content_type = "VIDEO"
        else:
            video_id = video_url
            # Default to VIDEO unless it looks like a clip
            if len(video_id) > 20 and '-' in video_id:
                content_type = "CLIP"
            else:
                content_type = "VIDEO"
        
        print(f"Extracted {content_type} ID: {video_id}")
        if channel_name:
            print(f"Channel name: {channel_name}")
        
        try:
            amount = int(input(f"Likes (max {len(tokens)}): ").strip())
            amount = min(amount, len(tokens))
        except:
            amount = len(tokens)
        
        # Get channel ID from content first
        print(f"Getting {content_type.lower()} info for {video_id}...")
        
        # Create async client
        limits = httpx.Limits(max_keepalive_connections=200, max_connections=300)  # Increased limits
        async with httpx.AsyncClient(limits=limits, timeout=5.0, http2=False) as client:
            if content_type == "VIDEO":
                channel_id = await get_channel_from_video(client, video_id)
            else:  # CLIP
                channel_id = await get_channel_from_clip(client, video_id, channel_name)
                
            if not channel_id:
                print(f"Could not get channel ID from {content_type.lower()}")
                return
            
            print(f"Channel ID: {channel_id}")
            print(f"Liking {content_type.lower()} {video_id} with {amount} likes...")
            
            # Start liking
            stats = {'success': 0, 'failed': 0, 'total': 0}
            start_time = time.time()
            
            # Process in batches to prevent overwhelming
            batch_size = 200  # Increased from 100 for faster processing
            total_batches = (amount + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, amount)
                batch_tokens = tokens[start_idx:end_idx]
                
                print(f"\nProcessing batch {batch_num + 1}/{total_batches} ({len(batch_tokens)} likes)...")
                
                # Create tasks for this batch
                tasks = []
                for token in batch_tokens:
                    task = asyncio.create_task(like_content(client, token, channel_id, video_id, content_type))
                    tasks.append(task)
                
                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, bool):
                        if result:
                            stats['success'] += 1
                        else:
                            stats['failed'] += 1
                    else:
                        stats['failed'] += 1
                    
                    stats['total'] += 1
                
                # Show progress after each batch
                elapsed = time.time() - start_time
                rate = stats['success'] / elapsed if elapsed > 0 else 0
                print(f"Batch complete: {stats['success']}/{stats['total']} | Failed: {stats['failed']} | Rate: {rate:.0f}/s")
                
                # Reduced delay between batches for faster processing
                if batch_num < total_batches - 1:
                    await asyncio.sleep(0.2)  # Reduced from 1.0 to 0.2
        
        # Results
        print(f"\nCompleted in {time.time() - start_time:.1f} seconds")
        print(f"Successful likes: {stats['success']}/{amount}")
        print(f"Failed likes: {stats['failed']}")
        
        if stats['success'] > 0:
            print(f"Speed: {stats['success']/(time.time() - start_time):.1f}/s")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped")
        sys.exit(0)
