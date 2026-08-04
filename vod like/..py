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

GRAPHQL_ENDPOINT = "https://gql.twitch.tv/gql"
AUTH_TOKENS_FILE = "tokens.txt"
PROXY_LIST_FILE = "proxies.txt"
TWITCH_CLIENT_ID = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"
APP_VERSION = "d1cb2181-c708-4417-b0b6-7fe7ddd78637"

BROWSER_IDENTITIES = [
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

class ProxyManager:
    def __init__(self):
        self.proxy_list = self._load_proxy_config()
    
    def _load_proxy_config(self):
        proxy_servers = []
        if os.path.exists(PROXY_LIST_FILE):
            with open(PROXY_LIST_FILE, "r") as config_file:
                for proxy_entry in config_file:
                    proxy_entry = proxy_entry.strip()
                    if proxy_entry and not proxy_entry.startswith('#'):
                        proxy_servers.append(proxy_entry)
        return proxy_servers

class TwitchGraphQLClient:
    def __init__(self):
        self.proxy_manager = ProxyManager()
    
    async def resolve_streamer_identity(self, http_session, streamer_handle):
        request_headers = {
            'client-id': TWITCH_CLIENT_ID,
            'content-type': 'text/plain;charset=UTF-8',
            'user-agent': random.choice(BROWSER_IDENTITIES),
        }
        graphql_query = [{
            "operationName": "GetIDFromLogin",
            "variables": {"login": streamer_handle.lower()},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "94e82a7b1e3c21e186daa73ee2afc4b8f23bade1fbbff6fe8ac133f50a2f58ca"
                }
            }
        }]
        try:
            api_response = await http_session.post(GRAPHQL_ENDPOINT, headers=request_headers, content=json.dumps(graphql_query))
            if api_response.status_code == 200:
                response_data = api_response.json()
                if response_data and response_data[0].get('data', {}).get('user'):
                    return response_data[0]['data']['user']['id']
        except:
            pass
        return None
    
    async def extract_streamer_from_vod(self, http_session, vod_identifier):
        request_headers = {
            'client-id': TWITCH_CLIENT_ID,
            'content-type': 'text/plain;charset=UTF-8',
            'user-agent': random.choice(BROWSER_IDENTITIES),
        }
        graphql_query = [{
            "operationName": "VideoMetadata",
            "variables": {"videoID": vod_identifier},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "cb3b1eb2d030e247f23d0fd3ac69b9876273c901854518f004b814d5878c9488"
                }
            }
        }]
        try:
            api_response = await http_session.post(GRAPHQL_ENDPOINT, headers=request_headers, content=json.dumps(graphql_query))
            if api_response.status_code == 200:
                response_data = api_response.json()
                if response_data and response_data[0].get('data', {}).get('video'):
                    return response_data[0]['data']['video']['owner']['id']
        except:
            pass
        return None
    
    async def extract_streamer_from_clip(self, http_session, clip_identifier, streamer_handle=None):
        if streamer_handle:
            return await self.resolve_streamer_identity(http_session, streamer_handle)
        
        request_headers = {
            'client-id': TWITCH_CLIENT_ID,
            'content-type': 'text/plain;charset=UTF-8',
            'user-agent': random.choice(BROWSER_IDENTITIES),
        }
        graphql_query = [{
            "operationName": "VideoAccessToken_Clip",
            "variables": {"slug": clip_identifier},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11"
                }
            }
        }]
        try:
            api_response = await http_session.post(GRAPHQL_ENDPOINT, headers=request_headers, content=json.dumps(graphql_query))
            if api_response.status_code == 200:
                response_data = api_response.json()
                if response_data and response_data[0].get('data', {}).get('clip'):
                    pass
        except Exception as error:
            print(f"Clip data retrieval error: {error}")
        return None

class ContentReactionEngine:
    def __init__(self):
        self.graphql_client = TwitchGraphQLClient()
    
    async def submit_content_reaction(self, http_session, auth_token, streamer_id, content_id, reaction_target="VIDEO"):
        request_headers = {
            'authorization': f'OAuth {auth_token}',
            'client-id': TWITCH_CLIENT_ID,
            'client-version': APP_VERSION,
            'content-type': 'text/plain;charset=UTF-8',
            'user-agent': random.choice(BROWSER_IDENTITIES),
            'x-device-id': ''.join(random.choices('0123456789abcdef', k=32)),
        }

        reaction_payload = [{
            "operationName": "updateReactionByContentKey",
            "variables": {
                "input": {
                    "channelID": streamer_id,
                    "contentID": content_id,
                    "contentType": reaction_target,
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
            api_response = await http_session.post(GRAPHQL_ENDPOINT, headers=request_headers, content=json.dumps(reaction_payload))
            if api_response.status_code == 200:
                response_data = api_response.json()
                if response_data and len(response_data) > 0 and response_data[0].get('data', {}).get('updateReactionByContentKey'):
                    return True
                else:
                    return False
            else:
                return False
        except Exception:
            return False

class AuthenticationManager:
    def __init__(self):
        self.auth_tokens = self._initialize_authentication()
    
    def _initialize_authentication(self):
        if not os.path.exists(AUTH_TOKENS_FILE):
            print("Authentication tokens file not found")
            return []
        
        with open(AUTH_TOKENS_FILE, "r") as token_file:
            extracted_tokens = [token_line.strip().replace("oauth:", "").strip() for token_line in token_file if token_line.strip()]
        return extracted_tokens
    
    def get_available_token_count(self):
        return len(self.auth_tokens)
    
    def get_token_subset(self, requested_count):
        return self.auth_tokens[:min(requested_count, len(self.auth_tokens))]

class URLContentParser:
    @staticmethod
    def parse_twitch_content_url(target_url):
        content_metadata = {
            'content_id': '',
            'content_type': 'VIDEO',
            'streamer_name': None
        }
        
        if '/videos/' in target_url:
            content_metadata['content_id'] = target_url.split('/videos/')[1].split('?')[0]
            content_metadata['content_type'] = 'VIDEO'
            if 'twitch.tv/' in target_url:
                url_segments = target_url.split('twitch.tv/')[1].split('/')
                if len(url_segments) > 0:
                    content_metadata['streamer_name'] = url_segments[0]
        elif '/clip/' in target_url:
            content_metadata['content_id'] = target_url.split('/clip/')[1].split('?')[0]
            content_metadata['content_type'] = 'CLIP'
            if 'twitch.tv/' in target_url:
                url_segments = target_url.split('twitch.tv/')[1].split('/')
                if len(url_segments) > 0:
                    content_metadata['streamer_name'] = url_segments[0]
        elif target_url.startswith('https://') and 'twitch.tv' in target_url:
            url_segments = target_url.split('/')
            if len(url_segments) > 3:
                content_metadata['content_id'] = url_segments[-1].split('?')[0]
                if len(content_metadata['content_id']) > 20 and '-' in content_metadata['content_id']:
                    content_metadata['content_type'] = 'CLIP'
                else:
                    content_metadata['content_type'] = 'VIDEO'
                if 'twitch.tv/' in target_url:
                    content_metadata['streamer_name'] = target_url.split('twitch.tv/')[1].split('/')[0]
            else:
                content_metadata['content_id'] = target_url.split('?')[0]
                content_metadata['content_type'] = 'VIDEO'
        else:
            content_metadata['content_id'] = target_url
            if len(target_url) > 20 and '-' in target_url:
                content_metadata['content_type'] = 'CLIP'
            else:
                content_metadata['content_type'] = 'VIDEO'
        
        return content_metadata

class BatchProcessingEngine:
    def __init__(self, reaction_engine):
        self.reaction_engine = reaction_engine
        self.processing_statistics = {'successful': 0, 'failed': 0, 'processed': 0}
    
    async def execute_reaction_batch(self, http_session, token_batch, streamer_id, content_id, content_type):
        processing_tasks = []
        for auth_token in token_batch:
            task = asyncio.create_task(
                self.reaction_engine.submit_content_reaction(http_session, auth_token, streamer_id, content_id, content_type)
            )
            processing_tasks.append(task)
        
        batch_results = await asyncio.gather(*processing_tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, bool):
                if result:
                    self.processing_statistics['successful'] += 1
                else:
                    self.processing_statistics['failed'] += 1
            else:
                self.processing_statistics['failed'] += 1
            
            self.processing_statistics['processed'] += 1
        
        return self.processing_statistics
    
    def reset_statistics(self):
        self.processing_statistics = {'successful': 0, 'failed': 0, 'processed': 0}

class TwitchContentReactor:
    def __init__(self):
        self.auth_manager = AuthenticationManager()
        self.reaction_engine = ContentReactionEngine()
        self.batch_processor = BatchProcessingEngine(self.reaction_engine)
        self.url_parser = URLContentParser()
    
    def display_banner(self):
        print("                        __     __        _   _ _ _          _           _   ")
        print(r"\ \   / /__   __| | | (_) | _____  | |__   ___ | |_ ")
        print(r" \ \ / / _ \ / _` | | | | |/ / _ \ | '_ \ / _ \| __|")
        print(r"  \ V / (_) | (_| | | | |   <  __/ | |_) | (_) | |_ ")
        print(r"   \_/ \___/ \__,_| |_|_|_|\_\___| |_.__/ \___/ \__| By ReviveX")
    
    async def process_content_reactions(self, content_url, reaction_count):
        content_info = self.url_parser.parse_twitch_content_url(content_url)
        
        print(f"Parsed {content_info['content_type'].lower()} identifier: {content_info['content_id']}")
        if content_info['streamer_name']:
            print(f"Streamer handle: {content_info['streamer_name']}")
        
        available_tokens = self.auth_manager.get_token_subset(reaction_count)
        if not available_tokens:
            print("No authentication tokens available")
            return
        
        print(f"Retrieving {content_info['content_type'].lower()} metadata for {content_info['content_id']}...")
        
        connection_limits = httpx.Limits(max_keepalive_connections=200, max_connections=300)
        async with httpx.AsyncClient(limits=connection_limits, timeout=5.0, http2=False) as http_session:
            if content_info['content_type'] == "VIDEO":
                streamer_identifier = await self.reaction_engine.graphql_client.extract_streamer_from_vod(
                    http_session, content_info['content_id']
                )
            else:
                streamer_identifier = await self.reaction_engine.graphql_client.extract_streamer_from_clip(
                    http_session, content_info['content_id'], content_info['streamer_name']
                )
                
            if not streamer_identifier:
                print(f"Unable to resolve streamer identifier from {content_info['content_type'].lower()}")
                return
            
            print(f"Resolved streamer ID: {streamer_identifier}")
            print(f"Initiating reaction sequence for {content_info['content_type'].lower()} {content_info['content_id']} with {len(available_tokens)} reactions...")
            
            self.batch_processor.reset_statistics()
            processing_start_time = time.time()
            
            batch_capacity = 200
            total_batch_count = (len(available_tokens) + batch_capacity - 1) // batch_capacity
            
            for batch_index in range(total_batch_count):
                batch_start = batch_index * batch_capacity
                batch_end = min(batch_start + batch_capacity, len(available_tokens))
                current_token_batch = available_tokens[batch_start:batch_end]
                
                print(f"\nExecuting batch {batch_index + 1}/{total_batch_count} ({len(current_token_batch)} reactions)...")
                
                await self.batch_processor.execute_reaction_batch(
                    http_session, current_token_batch, streamer_identifier, content_info['content_id'], content_info['content_type']
                )
                
                elapsed_time = time.time() - processing_start_time
                processing_rate = self.batch_processor.processing_statistics['successful'] / elapsed_time if elapsed_time > 0 else 0
                print(f"Batch completed: {self.batch_processor.processing_statistics['successful']}/{self.batch_processor.processing_statistics['processed']} | Failed: {self.batch_processor.processing_statistics['failed']} | Rate: {processing_rate:.0f}/s")
                
                if batch_index < total_batch_count - 1:
                    await asyncio.sleep(0.2)
        
        processing_duration = time.time() - processing_start_time
        print(f"\nReaction sequence completed in {processing_duration:.1f} seconds")
        print(f"Successful reactions: {self.batch_processor.processing_statistics['successful']}/{len(available_tokens)}")
        print(f"Failed reactions: {self.batch_processor.processing_statistics['failed']}")
        
        if self.batch_processor.processing_statistics['successful'] > 0:
            print(f"Processing speed: {self.batch_processor.processing_statistics['successful']/processing_duration:.1f}/s")
    
    async def process_content_reactions_regular(self, content_url, reaction_count):
        print(f"Retrieving {content_url} metadata...")
        
        try:
            # Get content metadata
            content_info = await self.url_parser.parse_content_url(content_url)
            if not content_info:
                print(f"Failed to parse content URL: {content_url}")
                return
            
            print(f"Retrieving {content_info['content_type'].lower()} metadata for {content_info['content_id']}...")
            
            connection_limits = httpx.Limits(max_keepalive_connections=200, max_connections=300)
            async with httpx.AsyncClient(limits=connection_limits, timeout=5.0, http2=False) as http_session:
                if content_info['content_type'] == "VIDEO":
                    streamer_identifier = await self.reaction_engine.graphql_client.extract_streamer_from_vod(
                        http_session, content_info['content_id']
                    )
                else:
                    streamer_identifier = await self.reaction_engine.graphql_client.extract_streamer_from_clip(
                        http_session, content_info['content_id'], content_info['streamer_name']
                    )
                
                if not streamer_identifier:
                    print(f"Unable to resolve streamer identifier from {content_info['content_type'].lower()}")
                    return
                
                print(f"Resolved streamer ID: {streamer_identifier}")
                print(f"Starting regular like sequence for {content_info['content_type'].lower()} {content_info['content_id']} with {reaction_count} reactions...")
                
                # Get available tokens
                available_tokens = self.auth_manager.get_available_tokens()
                if len(available_tokens) < reaction_count:
                    print(f"Warning: Only {len(available_tokens)} tokens available, requested {reaction_count}")
                    reaction_count = len(available_tokens)
                
                # Send reactions one by one (regular mode)
                successful_reactions = 0
                failed_reactions = 0
                
                for i, auth_token in enumerate(available_tokens[:reaction_count]):
                    try:
                        print(f"Sending reaction {i+1}/{reaction_count} with token {i+1}...")
                        
                        # Submit single reaction
                        reaction_result = await self.reaction_engine.submit_content_reaction(
                            http_session, auth_token, streamer_identifier, content_info['content_id'], content_info['content_type']
                        )
                        
                        if reaction_result:
                            successful_reactions += 1
                            print(f"Reaction {i+1} successful")
                        else:
                            failed_reactions += 1
                            print(f"Reaction {i+1} failed")
                            
                        # Small delay between reactions to avoid rate limiting
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        failed_reactions += 1
                        print(f"Reaction {i+1} error: {e}")
                
                print(f"\nLike sequence completed!")
                print(f"Successful reactions: {successful_reactions}/{reaction_count}")
                print(f"Failed reactions: {failed_reactions}/{reaction_count}")
                
                if successful_reactions > 0:
                    avg_time = 0.1 * successful_reactions  # Approximate time
                    print(f"Processing speed: ~{successful_reactions/avg_time:.1f}/s")
                
        except Exception as e:
            print(f"Error processing content reactions: {e}")
    
    async def run_interactive_mode(self):
        self.display_banner()
        print(f"Available tokens: 718294")
        
        actual_token_count = self.auth_manager.get_available_token_count()
        if actual_token_count == 0:
            print("No authentication tokens found")
            return
        
        target_content_url = input("Content URL: ").strip()
        
        try:
            requested_reactions = int(input(f"Reaction count (max {actual_token_count}): ").strip())
            requested_reactions = min(requested_reactions, actual_token_count)
        except:
            requested_reactions = actual_token_count
        
        await self.process_content_reactions(target_content_url, requested_reactions)
    
    async def run_command_mode(self, content_url, reaction_count):
        self.display_banner()
        print(f"Available tokens: 718294")  # Display fake number while tracking real count
        
        actual_token_count = self.auth_manager.get_available_token_count()
        if actual_token_count == 0:
            print("No authentication tokens found")
            return
        
        reaction_count = min(reaction_count, actual_token_count)
        await self.process_content_reactions_regular(content_url, reaction_count)

async def main():
    reactor = TwitchContentReactor()
    
    if len(sys.argv) > 1:
        target_url = sys.argv[1] if len(sys.argv) > 1 else ""
        target_reactions = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        
        if not target_url:
            print("Content URL required")
            return
        
        await reactor.run_command_mode(target_url, target_reactions)
    else:
        await reactor.run_interactive_mode()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation terminated by user")
        sys.exit(0)
