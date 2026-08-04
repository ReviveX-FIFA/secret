import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import os
import pickle
import urllib.parse
import random
from itertools import cycle

class RobloxCookieExtractor:
    def __init__(self):
        self.cookies = []
        self.failed_accounts = []
        self.successful_accounts = []
        self.session_file = 'cookie_session.pkl'
        self.cookies_file = 'extracted_cookies.json'
        self.browser_cookies_file = 'browser_cookies.txt'
        
        # Initialize files
        self.initialize_files()
        
        # Load proxies
        self.proxies = self.load_proxies()
        self.proxy_cycle = cycle(self.proxies) if self.proxies else None
        
    def load_proxies(self):
        """Load proxies from proxies.txt file"""
        proxies = []
        try:
            with open('proxies.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        # Format: host:port:username:password
                        parts = line.split(':')
                        if len(parts) >= 2:
                            if len(parts) == 4:  # host:port:username:password
                                proxy = {
                                    'http': f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}",
                                    'https': f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                                }
                            else:  # host:port
                                proxy = {
                                    'http': f"http://{parts[0]}:{parts[1]}",
                                    'https': f"http://{parts[0]}:{parts[1]}"
                                }
                            proxies.append(proxy)
            print(f"Loaded {len(proxies)} proxies")
        except FileNotFoundError:
            print("No proxies.txt found - running without proxies")
        except Exception as e:
            print(f"Error loading proxies: {e}")
        return proxies
        
    def get_random_proxy(self):
        """Get a random proxy from the list"""
        if self.proxies:
            return random.choice(self.proxies)
        return None
        
    def get_next_proxy(self):
        """Get next proxy from cycle"""
        if self.proxy_cycle:
            return next(self.proxy_cycle)
        return None
        
    def initialize_files(self):
        """Create output files if they don't exist"""
        try:
            # Create empty JSON file for cookies
            if not os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'w') as f:
                    json.dump([], f)
                print(f"Created {self.cookies_file}")
            
            # Create empty browser cookies file
            if not os.path.exists(self.browser_cookies_file):
                with open(self.browser_cookies_file, 'w') as f:
                    f.write("# Roblox Cookie Extractor - Browser Compatible Cookies\n")
                    f.write("# Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                print(f"Created {self.browser_cookies_file}")
                
        except Exception as e:
            print(f"Error initializing files: {e}")
    
    def load_accounts(self):
        """Load accounts from accounts.txt file"""
        accounts = []
        try:
            with open('accounts/accounts.txt', 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and ':' in line:
                        try:
                            # Split on first ':' to get username and password
                            parts = line.split(':', 1)
                            if len(parts) >= 2:
                                username = parts[0].strip()
                                password = parts[1].strip()
                                # Remove :_ suffix from password if present
                                if password.endswith(':_'):
                                    password = password[:-2]
                                elif password.endswith('_'):
                                    password = password[:-1]
                                
                                accounts.append({
                                    'username': username,
                                    'password': password,
                                    'line_number': line_num
                                })
                        except Exception as e:
                            print(f"Error parsing line {line_num}: {line} - {e}")
                            continue
                            
        except FileNotFoundError:
            print("accounts.txt not found!")
            return []
        except Exception as e:
            print(f"Error reading accounts.txt: {e}")
            return []
            
        print(f"Loaded {len(accounts)} accounts from file")
        return accounts
    
    def extract_cookies(self, max_retries=3, delay=10):
        """Extract cookies from Roblox accounts using API with proxy rotation"""
        # Use test accounts if available (for testing)
        if hasattr(self, 'accounts_to_process'):
            accounts = self.accounts_to_process
        else:
            accounts = self.load_accounts()
        
        if not accounts:
            print("No accounts to process!")
            return
        
        print(f"Starting cookie extraction for {len(accounts)} accounts...")
        print(f"Using {len(self.proxies)} proxies with anti-detection measures...")
        
        # User agents to rotate
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        for i, account in enumerate(accounts, 1):
            print(f"\nProcessing account {i}/{len(accounts)}: {account['username']}")
            
            # Get proxy for this account
            current_proxy = self.get_next_proxy()
            proxy_info = f" (Proxy: {current_proxy['http'].split('@')[-1] if current_proxy and '@' in current_proxy['http'] else 'No Proxy'})"
            
            for attempt in range(max_retries):
                try:
                    # Create new session for each attempt
                    session = requests.Session()
                    
                    # Set proxy if available
                    if current_proxy:
                        session.proxies.update(current_proxy)
                        print(f"  Using proxy {attempt + 1}: {current_proxy['http'].split('@')[-1] if '@' in current_proxy['http'] else current_proxy['http']}")
                    
                    # Rotate user agent
                    user_agent = user_agents[(i + attempt) % len(user_agents)]
                    
                    # Set realistic headers
                    session.headers.update({
                        'User-Agent': user_agent,
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Origin': 'https://www.roblox.com',
                        'Referer': 'https://www.roblox.com/login'
                    })
                    
                    # Random human-like delay before first request
                    initial_delay = random.uniform(2, 5)
                    print(f"  Waiting {initial_delay:.1f} seconds before initializing...")
                    time.sleep(initial_delay)
                    
                    # First, visit Roblox homepage to get initial cookies and session
                    print(f"  Initializing session for {account['username']}{proxy_info}")
                    try:
                        home_response = session.get('https://www.roblox.com/', timeout=15)
                    except requests.exceptions.ProxyError:
                        print(f"  ✗ Proxy connection failed for {account['username']}")
                        # Try next proxy
                        current_proxy = self.get_next_proxy()
                        if current_proxy:
                            session.proxies.update(current_proxy)
                            proxy_info = f" (Proxy: {current_proxy['http'].split('@')[-1] if '@' in current_proxy['http'] else 'No Proxy'})"
                        continue
                    
                    if not home_response.ok:
                        print(f"  ✗ Failed to access homepage: {home_response.status_code}")
                        continue
                    
                    # Random delay to seem more human
                    human_delay = random.uniform(3, 7)
                    print(f"  Waiting {human_delay:.1f} seconds...")
                    time.sleep(human_delay)
                    
                    # Visit login page to get CSRF token
                    try:
                        login_page = session.get('https://www.roblox.com/login', timeout=15)
                    except requests.exceptions.ProxyError:
                        print(f"  ✗ Proxy failed during login page access")
                        continue
                    
                    if not login_page.ok:
                        print(f"  ✗ Failed to access login page: {login_page.status_code}")
                        continue
                    
                    # Random delay before login attempt
                    login_delay = random.uniform(2, 4)
                    time.sleep(login_delay)
                    
                    # Try newer authentication endpoint
                    login_url = 'https://auth.roblox.com/v2/login'
                    
                    # Prepare login data with proper format
                    login_data = {
                        'ctype': 'Username',
                        'cvalue': account['username'],
                        'password': account['password'],
                        'challengeId': '',
                        'rememberDevice': 'false'
                    }
                    
                    print(f"  Attempting login for {account['username']} (Attempt {attempt + 1}/{max_retries})...")
                    # Make login request with timeout
                    try:
                        response = session.post(login_url, json=login_data, timeout=20)
                    except requests.exceptions.ProxyError:
                        print(f"  ✗ Proxy failed during login attempt")
                        continue
                    
                    print(f"  Response status: {response.status_code}")
                    
                    # Check response
                    if response.status_code == 200:
                        try:
                            login_result = response.json()
                            
                            if login_result.get('user'):
                                # Login successful - get cookies
                                cookies_dict = session.cookies.get_dict()
                                
                                if cookies_dict:
                                    cookie_data = {
                                        'username': account['username'],
                                        'cookies': cookies_dict,
                                        'extracted_at': datetime.now().isoformat(),
                                        'line_number': account['line_number'],
                                        'user_id': login_result.get('user', {}).get('id', 'N/A'),
                                        'proxy_used': current_proxy['http'].split('@')[-1] if current_proxy and '@' in current_proxy['http'] else 'No Proxy'
                                    }
                                    
                                    self.cookies.append(cookie_data)
                                    self.successful_accounts.append(account['username'])
                                    print(f"  ✓ Successfully extracted cookies for {account['username']}")
                                    print(f"    Found {len(cookies_dict)} cookies")
                                    print(f"    User ID: {login_result.get('user', {}).get('id', 'N/A')}")
                                    break
                                else:
                                    print(f"  ✗ No cookies found for {account['username']}")
                            else:
                                print(f"  ✗ Login failed - invalid response for {account['username']}")
                                print(f"    Response: {login_result}")
                                
                        except json.JSONDecodeError:
                            print(f"  ✗ Invalid JSON response for {account['username']}")
                            print(f"    Response text: {response.text[:200]}...")
                            
                    elif response.status_code == 401:
                        print(f"  ✗ Invalid credentials for {account['username']}")
                        break  # Don't retry invalid credentials
                        
                    elif response.status_code == 403:
                        print(f"  ✗ Rate limited/blocked for {account['username']}")
                        if attempt < max_retries - 1:
                            # Try different proxy for next attempt
                            current_proxy = self.get_next_proxy()
                            if current_proxy:
                                proxy_info = f" (Proxy: {current_proxy['http'].split('@')[-1] if '@' in current_proxy['http'] else 'No Proxy'})"
                            wait_time = delay * (attempt + 1)  # Exponential backoff
                            print(f"  Waiting {wait_time} seconds before retry with new proxy...")
                            time.sleep(wait_time)
                        continue
                    elif response.status_code == 429:
                        print(f"  ✗ Too many requests for {account['username']}")
                        if attempt < max_retries - 1:
                            # Try different proxy for next attempt
                            current_proxy = self.get_next_proxy()
                            if current_proxy:
                                proxy_info = f" (Proxy: {current_proxy['http'].split('@')[-1] if '@' in current_proxy['http'] else 'No Proxy'})"
                            wait_time = delay * 3  # Longer wait for rate limit
                            print(f"  Waiting {wait_time} seconds before retry with new proxy...")
                            time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ✗ HTTP {response.status_code} for {account['username']}")
                        print(f"    Response: {response.text[:200]}...")
                        
                except requests.exceptions.Timeout:
                    print(f"  ✗ Request timeout for {account['username']}")
                except requests.exceptions.ProxyError:
                    print(f"  ✗ Proxy error for {account['username']}")
                    # Try next proxy
                    current_proxy = self.get_next_proxy()
                    if current_proxy:
                        proxy_info = f" (Proxy: {current_proxy['http'].split('@')[-1] if '@' in current_proxy['http'] else 'No Proxy'})"
                except Exception as e:
                    print(f"  ✗ Attempt {attempt + 1} failed for {account['username']}: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"  Retrying in {delay} seconds...")
                        time.sleep(delay)
                    continue
            
            else:  # This runs if the for loop completes without break
                print(f"  ✗ All {max_retries} attempts failed for {account['username']}")
                self.failed_accounts.append(account['username'])
            
            # Longer delay between accounts to avoid rate limiting
            if i < len(accounts):
                between_delay = random.uniform(delay, delay * 1.5)
                print(f"  Waiting {between_delay:.1f} seconds before next account...")
                time.sleep(between_delay)
    
    def save_cookies(self):
        """Save extracted cookies to JSON file"""
        if not self.cookies:
            print("No cookies to save!")
            return
        
        try:
            with open(self.cookies_file, 'w') as f:
                json.dump(self.cookies, f, indent=2)
            print(f"Saved {len(self.cookies)} cookie sets to {self.cookies_file}")
        except Exception as e:
            print(f"Error saving cookies: {e}")
    
    def save_session(self):
        """Save session state"""
        session_data = {
            'successful_accounts': self.successful_accounts,
            'failed_accounts': self.failed_accounts,
            'last_run': datetime.now().isoformat()
        }
        
        try:
            with open(self.session_file, 'wb') as f:
                pickle.dump(session_data, f)
            print(f"Session saved to {self.session_file}")
        except Exception as e:
            print(f"Error saving session: {e}")
    
    def load_session(self):
        """Load previous session state"""
        try:
            with open(self.session_file, 'rb') as f:
                session_data = pickle.load(f)
            self.successful_accounts = session_data.get('successful_accounts', [])
            self.failed_accounts = session_data.get('failed_accounts', [])
            print(f"Loaded previous session: {len(self.successful_accounts)} successful, {len(self.failed_accounts)} failed")
            return True
        except FileNotFoundError:
            print("No previous session found")
            return False
        except Exception as e:
            print(f"Error loading session: {e}")
            return False
    
    def print_summary(self):
        """Print extraction summary"""
        print("\n" + "="*50)
        print("COOKIE EXTRACTION SUMMARY")
        print("="*50)
        print(f"Total cookies extracted: {len(self.cookies)}")
        print(f"Successful accounts: {len(self.successful_accounts)}")
        print(f"Failed accounts: {len(self.failed_accounts)}")
        
        if self.successful_accounts:
            print(f"\nSuccessful accounts:")
            for username in self.successful_accounts:
                print(f"  ✓ {username}")
        
        if self.failed_accounts:
            print(f"\nFailed accounts:")
            for username in self.failed_accounts:
                print(f"  ✗ {username}")
        
        print("="*50)
    
    def get_cookies_by_username(self, username):
        """Get cookies for specific username"""
        for cookie_data in self.cookies:
            if cookie_data['username'] == username:
                return cookie_data['cookies']
        return None
    
    def export_cookies_for_browser(self, output_file=None):
        """Export cookies in browser-compatible format"""
        if output_file is None:
            output_file = self.browser_cookies_file
            
        try:
            with open(output_file, 'w') as f:
                f.write("# Roblox Cookie Extractor - Browser Compatible Cookies\n")
                f.write("# Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                
                for cookie_data in self.cookies:
                    f.write(f"# Account: {cookie_data['username']}\n")
                    f.write(f"# Extracted: {cookie_data['extracted_at']}\n")
                    for name, value in cookie_data['cookies'].items():
                        f.write(f"{name}={value}; ")
                    f.write("\n\n")
            print(f"Browser-compatible cookies exported to {output_file}")
        except Exception as e:
            print(f"Error exporting browser cookies: {e}")

def main():
    """Main execution function"""
    extractor = RobloxCookieExtractor()
    
    # Load previous session if exists
    extractor.load_session()
    
    # Check if we have accounts to process
    accounts = extractor.load_accounts()
    if not accounts:
        print("No accounts found in accounts.txt!")
        return
    
    print(f"Found {len(accounts)} accounts to process")
    print("Files created and ready:")
    print(f"  - {extractor.cookies_file} (JSON format)")
    print(f"  - {extractor.browser_cookies_file} (Browser format)")
    print(f"  - {extractor.session_file} (Session state)")
    
    # Extract cookies
    extractor.extract_cookies(max_retries=3, delay=2)
    
    # Save results
    extractor.save_cookies()
    extractor.save_session()
    
    # Print summary
    extractor.print_summary()
    
    # Export browser-compatible format
    extractor.export_cookies_for_browser()
    
    print(f"\nCookie extraction completed! Check {extractor.cookies_file} for results.")

if __name__ == "__main__":
    main()
