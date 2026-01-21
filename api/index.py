"""
Vercel Serverless Function для проверки ККТ
"""
from http.server import BaseHTTPRequestHandler
import json
import requests
import time
import urllib3

# Отключаем предупреждения о непроверенных HTTPS запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_BASE = 'https://kkt-online.nalog.ru/lkip.html'

# Заголовки для имитации браузера
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://kkt-online.nalog.ru/',
    'Origin': 'https://kkt-online.nalog.ru'
}

# Ограничение частоты запросов для защиты от блокировки
MIN_REQUEST_INTERVAL = 0.5

# Глобальная переменная для хранения времени последнего запроса
last_request_time = 0


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        global last_request_time
        
        try:
            # Читаем тело запроса
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            
            model_code = data.get('model_code')
            factory_number = data.get('factory_number')
            
            if not model_code or not factory_number:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing required parameters'}).encode())
                return
            
            # Ограничение частоты запросов
            current_time = time.time()
            time_since_last_request = current_time - last_request_time
            if time_since_last_request < MIN_REQUEST_INTERVAL:
                time.sleep(MIN_REQUEST_INTERVAL - time_since_last_request)
            
            last_request_time = time.time()
            
            # Выполняем запрос к API ФНС
            url = f'{API_BASE}?query=/kkt/model/check&factory_number={factory_number}&model_code={model_code}'
            response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            response.raise_for_status()
            
            # Отправляем ответ
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response.json()).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e), 'check_status': -1}).encode())
    
    def do_OPTIONS(self):
        # Обработка preflight запросов для CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
