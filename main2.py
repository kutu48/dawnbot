import random
import time
import requests
from loguru import logger
from PIL import Image
from io import BytesIO
import base64
import ddddocr
from PIL import ImageOps
import numpy as np
import names  # Library untuk mendapatkan nama acak
import string

# Inisialisasi OCR
ocr = ddddocr.DdddOcr(show_ad=False, det=False, ocr=False, import_onnx_path="dawn.onnx", charsets_path="charsets.json")

# Fungsi untuk menghasilkan kata sandi acak
def generate_random_password():
    upper_case = random.choice(string.ascii_uppercase)
    lower_case = ''.join(random.choice(string.ascii_lowercase) for _ in range(random.randint(6, 7)))
    digits = ''.join(random.choice(string.digits) for _ in range(2))
    symbol = random.choice(string.punctuation)

    password_list = list(upper_case + lower_case + digits + symbol)
    random.shuffle(password_list)
    password = ''.join(password_list)

    return password

# Fungsi untuk memproses gambar
def process_image(image):
    gray_img = ImageOps.grayscale(image)
    img_array = np.array(gray_img)
    processed_img_array = np.ones_like(img_array) * 255
    black_threshold_low = 0
    black_threshold_high = 50
    mask = (img_array >= black_threshold_low) & (img_array <= black_threshold_high)
    processed_img_array[mask] = 0
    processed_img = Image.fromarray(processed_img_array)
    return processed_img

# Mengambil proxy dari file
def get_proxies_from_file():
    with open('proxy.txt', 'r') as f:
        proxies = [line.strip() for line in f if line.strip()]
    return proxies

# Mengambil email dari file
def get_emails_from_file():
    with open('email.txt', 'r') as f:
        emails = [line.strip() for line in f if line.strip()]
    return emails

# Fungsi untuk menyimpan hasil registrasi ke file register.txt dengan format email:password
def save_registration_details(email, password):
    with open('register.txt', 'a') as f:
        f.write(f"{email}:{password}\n")
    logger.info(f"Registration details saved to register.txt for {email}")

# Fungsi registrasi
def register(session, email, password, puzzle_id, answer):
    json_data = {
        "firstname": names.get_first_name(),
        "lastname": names.get_last_name(),
        "email": email,
        "mobile": "",
        "password": password,
        "country": "+91",
        "referralCode": "z1zqkdrn",
        "puzzle_id": puzzle_id,
        "ans": answer,
    }

    logger.info(f"Payload for registration: {json_data}")

    response = session.post(
        'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/validate-register',
        json=json_data,
    )

    logger.debug(f"Registration response content: {response.text}")

    if response.status_code in (200, 201):
        try:
            response_json = response.json()
            success = response_json.get('success', False)
            message = response_json.get('message', 'No message provided')
            msgcode = response_json.get('msgcode', 'No code provided')

            # Menambahkan log untuk mencetak nilai respons
            logger.info(f"Registration Response - Success: {success}, Message: {message}, MsgCode: {msgcode}")

            return response_json
        except ValueError:
            logger.error(f"Failed to parse JSON. Response content: {response.text}")
            return {}
    else:
        logger.error(f"Failed to register. Status code: {response.status_code}, Content: {response.text}")
        return {}

# Fungsi utama untuk menjalankan proses registrasi
def run(email, password, proxy, max_retries=3):
    session = requests.Session()
    session.verify = False
    logger.info(f"Load email: {email} dari email.txt")
    logger.info(f"{email} Using proxy: {proxy}")

    for attempt in range(1, max_retries + 1):
        try:
            proxy_dict = {
                "http": proxy,
                "https": proxy
            }

            headers = {
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                'origin': 'chrome-extension://fpdkjdnhkakefebpekbdhillbhonfjjp',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            }
            
            # Dapatkan puzzle
            puzzle_response = session.get(
                'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle',
                headers=headers,
                proxies=proxy_dict
            )
            
            logger.debug(f"Puzzle response: {puzzle_response.text}") 
            
            if puzzle_response.status_code in (200, 201):
                puzzle_id = puzzle_response.json().get('puzzle_id')

                params = {'puzzle_id': puzzle_id}
                image_response = session.get(
                    'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle-image',
                    headers=headers,
                    params=params,
                    proxies=proxy_dict
                )
                
                if image_response.status_code == 200:
                    base64_image = image_response.json().get('imgBase64')
                    image_data = base64.b64decode(base64_image)
                    image = Image.open(BytesIO(image_data))
                    new_image = process_image(image)
                    result = ocr.classification(new_image)

                    logger.debug(f"Captcha result: {result}")

                    # Panggil fungsi registrasi
                    response_json = register(session, email, password, puzzle_id, result)

                    status = response_json.get('status', False)
                    message = response_json.get('message', '')

                    if status:
                        logger.success(f"{email} Successfully registered!")
                        save_registration_details(email, password)
                        return True
                    else:
                        logger.warning(f"{email} Registration failed: {message}")
                        if attempt < max_retries:
                            logger.info(f"{email} Retrying... Attempt {attempt + 1} of {max_retries}")
                            time.sleep(random.uniform(2, 5))
                        else:
                            logger.error(f"{email} Max retries reached for {email}. Skipping to the next account.")
                else:
                    logger.error(f"{email} Failed to fetch puzzle image. Status code: {image_response.status_code}")
                    if attempt < max_retries:
                        logger.info(f"{email} Retrying... Attempt {attempt + 1} of {max_retries}")
                        time.sleep(random.uniform(2, 5))
                    else:
                        logger.error(f"{email} Max retries reached for {email}. Skipping to the next account.")
            else:
                logger.error(f"{email} Failed to fetch puzzle. Status code: {puzzle_response.status_code}")
                if attempt < max_retries:
                    logger.info(f"{email} Retrying... Attempt {attempt + 1} of {max_retries}")
                    time.sleep(random.uniform(2, 5))
                else:
                    logger.error(f"{email} Max retries reached for {email}. Skipping to the next account.")

        except requests.exceptions.ProxyError as pe:
            logger.error(f"{email} Proxy error: {pe}. Retrying...")
            if attempt < max_retries:
                logger.info(f"{email} Retrying... Attempt {attempt + 1} of {max_retries}")
                time.sleep(random.uniform(2, 5))
            else:
                logger.error(f"{email} Max retries reached for {email}. Skipping to the next account.")

        except Exception as e:
            logger.error(f"{email} Error: {e}. Retrying...")
            if attempt < max_retries:
                logger.info(f"{email} Retrying... Attempt {attempt + 1} of {max_retries}")
                time.sleep(random.uniform(2, 5))
            else:
                logger.error(f"{email} Max retries reached for {email}. Skipping to the next account.")

    return False

# Proses semua akun
def run_all_accounts(emails, proxies):
    error_accounts = []

    for email in emails:
        password = generate_random_password()
        proxy = random.choice(proxies) if proxies else None

        # Jeda acak antara 5 hingga 7 detik
        time.sleep(random.uniform(5, 7))

        success = run(email, password, proxy)
        if not success:
            error_accounts.append(email)

    return error_accounts

# Memproses ulang akun yang error
def retry_error_accounts(error_accounts, proxies):
    if error_accounts:
        logger.info("Retrying accounts that failed...")
        error_accounts = run_all_accounts(error_accounts, proxies)
    else:
        logger.info("No accounts failed.")

# Main function
def main():
    proxies = get_proxies_from_file()
    emails = get_emails_from_file()
    error_accounts = run_all_accounts(emails, proxies)
    retry_error_accounts(error_accounts, proxies)

if __name__ == "__main__":
    main()
