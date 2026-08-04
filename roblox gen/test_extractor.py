from cookie_extractor import RobloxCookieExtractor

# Test with just first 3 accounts
extractor = RobloxCookieExtractor()

# Load accounts and get first 3
all_accounts = extractor.load_accounts()
test_accounts = all_accounts[:3]  # Test first 3 accounts only

print(f"Testing with first {len(test_accounts)} accounts...")
print("Accounts to test:")
for acc in test_accounts:
    print(f"  - {acc['username']}")

# Override the accounts list with test accounts
extractor.accounts_to_process = test_accounts

# Test extraction
extractor.extract_cookies(max_retries=2, delay=1)

# Print results
extractor.print_summary()
