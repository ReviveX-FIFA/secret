import os,tkinter as tk,time,sys,requests;from tkinter import filedialog;from tkinter import filedialog;from colorama import Fore, Back;from time import sleep;from threading import Thread;from concurrent.futures import ThreadPoolExecutor

def clear():
    os.system('cls||clear')

def banner():
    print(f"""{Fore.MAGENTA}
    ___        ___  __          ___  __        ___          __        ___  __        ___  __  
     |  |  | |  |  /  ` |__|     |  /  \ |__/ |__  |\ |    /  ` |__| |__  /  ` |__/ |__  |__) 
     |  |/\| |  |  \__, |  |     |  \__/ |  \ |___ | \|    \__, |  | |___ \__, |  \ |___ |  \ 
                                                                                              {Fore.RESET}""")
def check(token):
    response = requests.get('https://id.twitch.tv/oauth2/validate', headers = {'Authorization': f'Bearer {token}'})
    if response.status_code == 200:
        return True
    else:
        return False


def check_tokens(tokens_file_path, valid_tokens_file_path, num_threads=10):
    global totalchecked, valid, invalid
    with open(tokens_file_path.replace("/", "\\"), 'r') as f:
        tokens = f.read().splitlines()

    def check_thread(start, end):
        global valid, invalid
        for i in range(start, end):
            if check(tokens[i]):
                valid += 1
                with open(valid_tokens_file_path.replace("/", "\\"), "a") as f:
                    f.write(tokens[i] + '\n')
                print(f'{tokens[i]} is {Fore.GREEN}valid{Fore.RESET}')
            else:
                invalid += 1
                print(f'{tokens[i]} is {Fore.RED}invalid{Fore.RESET}')

    totalchecked = 0
    valid = 0
    invalid = 0
    threads = []
    for i in range(num_threads):
        start = i * (len(tokens) // num_threads)
        end = start + (len(tokens) // num_threads)
        if i == num_threads - 1:
            end = len(tokens)
        t = Thread(target=check_thread, args=(start, end))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    clear()
    banner()
    print(f"""
        Total Tokens: {Fore.YELLOW}{len(tokens)}{Fore.RESET}
        Valid: {Fore.GREEN}{valid}{Fore.RESET}
        Invalid {Fore.RED}{invalid}{Fore.RESET}

        Saved all valid tokens in {Back.LIGHTBLACK_EX}{valid_tokens_file_path}{Back.RESET}
    """)
    sleep(100)
    sys.exit()



def main():
    global valid, invalid
    valid = 0
    invalid = 0
    banner()
    print(f"    [ {Fore.MAGENTA} Tokens To Check {Fore.RESET} ] ")
    sleep(1)
    tokens_file_path = filedialog.askopenfilename(title="CHOOSE THE TOKENS YOU WANT TO CHECK", filetypes=[('Text files', '*.txt')])
    print(f"    [ {Fore.MAGENTA} File To Save Valid Tokens in{Fore.RESET} ]")
    sleep(2)
    valid_tokens_file_path = filedialog.askopenfilename(title="FILE TO WRITE VALID TOKENS IN", filetypes=[('Text files', '*.txt')])
    with open(tokens_file_path.replace("/", "\\"), 'r') as f:
        tokens = f.read().splitlines()
    print(f'    [ {Fore.YELLOW} {len(tokens)} {Fore.RESET}Tokens Loaded ] ')
    check_tokens(tokens_file_path, valid_tokens_file_path)
   

os.system('title Twitch Token Checker')
Thread(target=main).start()
