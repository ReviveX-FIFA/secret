import requests
import json
import random
import threading
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

class AuthenticationManager:
    def __init__(self):
        self._credentials = self._load_file("tokens.txt")
        self._proxy_servers = self._load_file("proxies.txt")
        self._credential_counter = 0
        self._proxy_counter = 0

    def _load_file(self, filename):
        try:
            with open(filename, "r") as file:
                return file.read().splitlines()
        except FileNotFoundError:
            print(f"Warning: {filename} not found. Using empty list.")
            return []
    
    def get_next_authentication(self):
        if not self._credentials:
            return ""
        current = self._credentials[self._credential_counter % len(self._credentials)]
        self._credential_counter += 1
        return current.split('|')[1] if '|' in current else current.strip()
    
    def get_next_proxy_config(self):
        if not self._proxy_servers:
            return None
        current = self._proxy_servers[self._proxy_counter % len(self._proxy_servers)]
        self._proxy_counter += 1
        parts = current.split(':')
        if len(parts) == 4:
            ip, port, user, pw = parts
            formatted = f"{user}:{pw}@{ip}:{port}"
            return {"http": f"http://{formatted}", "https": f"http://{formatted}"}
        return {"http": f"http://{current}", "https": f"http://{current}"}

class HTTPClientManager:
    def __init__(self):
        self._session = self._create_optimized_session()

    def _create_optimized_session(self):
        client = requests.Session()
        client.verify = False

        retry_config = Retry(
            total=1,
            backoff_factor=0.05,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_config, pool_connections=100, pool_maxsize=100)
        client.mount("http://", adapter)
        client.mount("https://", adapter)

        client.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        return client
    
    def execute_request(self, endpoint, payload, headers, proxy_config):
        return self._session.post(endpoint, json=payload, headers=headers, proxies=proxy_config, timeout=3)

class RaidOperation:
    def __init__(self, raid_id, operation_count):
        self.raid_id = raid_id
        self.operation_count = operation_count
        self.auth_manager = AuthenticationManager()
        self.http_client = HTTPClientManager()
        self.api_endpoint = "https://gql.twitch.tv/gql"

    def _construct_payload(self):
        return [
            {
                "operationName": "JoinRaid",
                "variables": {
                    "input": {
                        "raidID": self.raid_id
                    }
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "c6a332a86d1087fbbb1a8623aa01bd1313d2386e7c63be60fdb2d1901f01a4ae"
                    }
                }
            }
        ]
    
    def _build_headers(self):
        return {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US",
            "Authorization": "OAuth " + self.auth_manager.get_next_authentication(),
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Host": "gql.twitch.tv",
        }
    
    def execute_single_join(self, worker_identifier):
        try:
            request_payload = self._construct_payload()
            request_headers = self._build_headers()
            proxy_configuration = self.auth_manager.get_next_proxy_config()
            
            response = self.http_client.execute_request(
                self.api_endpoint, request_payload, request_headers, proxy_configuration
            )
            response_data = response.json()
            print(f"Worker {worker_identifier}: {response_data}")
            return True
        except Exception as error:
            print(f"Worker {worker_identifier} encountered error: {error}")
            return False
    
    def execute_mass_join(self):
        print(f"Initiating raid operation with {self.operation_count} participants by daddy ReviveX...")
        operation_start = time.time()
        
        maximum_concurrent_workers = min(100, self.operation_count)
        completed_operations = 0
        successful_operations = 0
        unsuccessful_operations = 0
        
        with ThreadPoolExecutor(max_workers=maximum_concurrent_workers) as task_executor:
            submitted_tasks = [
                task_executor.submit(self.execute_single_join, worker_id + 1) 
                for worker_id in range(self.operation_count)
            ]
            
            for completed_task in as_completed(submitted_tasks):
                try:
                    if completed_task.result():
                        successful_operations += 1
                    else:
                        unsuccessful_operations += 1
                except Exception as error:
                    print(f"Task execution error: {error}")
                    unsuccessful_operations += 1

                completed_operations = successful_operations + unsuccessful_operations
                if completed_operations % 10 == 0 or completed_operations == self.operation_count:
                    elapsed_time = time.time() - operation_start
                    print(f"Status: {completed_operations}/{self.operation_count} | Successful: {successful_operations} | Failed: {unsuccessful_operations} | Duration: {elapsed_time:.1f}s")

        operation_end = time.time()
        total_duration = operation_end - operation_start
        success_percentage = (successful_operations / self.operation_count) * 100
        
        print(f"\nRaid operation concluded in {total_duration:.1f} seconds by ReviveX")
        print(f"Successful participants: {successful_operations}/{self.operation_count}")
        print(f"Failed participants: {unsuccessful_operations}")
        print(f"Success rate: {success_percentage:.1f}%")

def parse_command_arguments():
    if len(sys.argv) > 1:
        raid_identifier = sys.argv[1] if len(sys.argv) > 1 else ""
        participant_count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    else:
        raid_identifier = input("raid id: ")
        participant_count = int(input("joins: "))

    return raid_identifier, participant_count

def main():
    raid_target, join_quantity = parse_command_arguments()
    raid_handler = RaidOperation(raid_target, join_quantity)
    raid_handler.execute_mass_join()

if __name__ == "__main__":
    main()
