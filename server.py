#!/usr/bin/env python3
"""
Прокси-сервер для API ФНС
Обходит проблему CORS при обращении к API kkt-online.nalog.ru
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import time
import urllib3

# Отключаем предупреждения о непроверенных HTTPS запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__, static_folder='.')
CORS(app)

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
last_request_time = 0
MIN_REQUEST_INTERVAL = 0.5  # минимальный интервал между запросами в секундах (увеличено для безопасности)


@app.route('/')
def index():
    """Возвращает главную страницу"""
    return send_from_directory('.', 'index.html')


@app.route('/api/kkt/models', methods=['GET'])
def get_models():
    """Получить список всех моделей ККТ"""
    try:
        response = requests.get(f'{API_BASE}?query=/kkt/models', headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/kkt/check', methods=['POST'])
def check_kkt():
    """Проверить ККТ по заводскому номеру"""
    global last_request_time
    
    try:
        data = request.get_json()
        model_code = data.get('model_code')
        factory_number = data.get('factory_number')
        
        if not model_code or not factory_number:
            return jsonify({'error': 'Missing required parameters'}), 400
        
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
        
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e), 'check_status': -1}), 500


@app.route('/api/kkt/check-batch', methods=['POST'])
def check_kkt_batch():
    """Проверить несколько ККТ за один раз"""
    global last_request_time
    
    try:
        data = request.get_json()
        model_code = data.get('model_code')
        factory_numbers = data.get('factory_numbers', [])
        
        if not model_code or not factory_numbers:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        results = []
        
        for factory_number in factory_numbers:
            try:
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
                
                result = response.json()
                result['factory_number'] = factory_number
                results.append(result)
                
            except Exception as e:
                results.append({
                    'factory_number': factory_number,
                    'check_status': -1,
                    'check_result': f'Ошибка при проверке: {str(e)}'
                })
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import os
    # Отключаем debug mode если запущено в фоновом режиме
    debug_mode = os.isatty(0)
    
    print('🚀 Сервер запущен на http://localhost:5001')
    print('📝 Откройте http://localhost:5001 в браузере')
    app.run(debug=debug_mode, port=5001, host='0.0.0.0', use_reloader=False)
