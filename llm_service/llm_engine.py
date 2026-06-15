import os
import json
import uuid
import requests
import urllib3
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LLMEngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.auth_key = os.getenv('GIGACHAT_CREDENTIALS')
        self.scope = os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS')
        
        if not self.auth_key:
            raise ValueError("❌ GIGACHAT_CREDENTIALS не найден в .env")
        
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.model = "GigaChat-2-Max"
        
        self._update_token()
        print(f"✅ LLM Engine ({self.model}) инициализирован")
    
    def _update_token(self):
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            'Authorization': f'Basic {self.auth_key}',
            'RqUID': str(uuid.uuid4()),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        payload = {'scope': self.scope}
        
        response = requests.post(url, headers=headers, data=payload, verify=False)
        
        if response.status_code != 200:
            raise Exception(f"Ошибка получения токена: {response.status_code}")
        
        self.access_token = response.json()['access_token']
        print("✅ Токен получен")
    
    def correct_table(self, rows: dict) -> dict:
        input_data = []
        for row_num in sorted(rows.keys()):
            row_data = rows[row_num]
            input_data.append({
                "row": row_num,
                "Имя родившегося": row_data.get("Имя родившегося", "—"),
                "Родители": row_data.get("Родители", "—"),
                "Восприемники (крестные)": row_data.get("Восприемники (крестные)", "—"),
                "Священник": row_data.get("Священник", "—")
            })
        
        input_json = json.dumps(input_data, ensure_ascii=False, indent=2)
        
        prompt = f"""Ты - специалист по метрическим книгам.

Исправь орфографические ошибки и склей разорванные слова.

Правила:
1. "государст венным" → "государственным"
2. "Симо новъ" → "Симоновъ"
3. "Бон 9 дарев" → "Бондарев"
4. "Во-" удалить
5. Добавляй ъ: "крестьянин" → "крестьянинъ"

Входные данные:
{input_json}

Верни ТОЛЬКО JSON в формате: {{"rows": [{{"row": 1, "Имя родившегося": "...", "Родители": "...", "Восприемники (крестные)": "...", "Священник": "..."}}]}}"""
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 8000,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            verify=False,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"❌ Ошибка: {response.status_code}")
            return rows
        
        content = response.json()['choices'][0]['message']['content']
        
        try:
            parsed = json.loads(content)
            if "rows" in parsed:
                corrected = {}
                for item in parsed["rows"]:
                    corrected[item["row"]] = {
                        "Имя родившегося": item["Имя родившегося"],
                        "Родители": item["Родители"],
                        "Восприемники (крестные)": item["Восприемники (крестные)"],
                        "Священник": item["Священник"]
                    }
                return corrected
        except:
            pass
        
        return rows