import os
import json
import queue
import subprocess
import requests
import keyboard
import sounddevice as sd
import vosk
import pyautogui

# Настройки
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_PATH = "vosk-model-small-ru-0.22"
COMMANDS_FILE = "Commands.dat"

# Очередь для аудиопотока
q = queue.Queue()

# Проверяем и загружаем Vosk-модель
if not os.path.exists(MODEL_PATH):
    raise Exception(f"Модель {MODEL_PATH} не найдена!")
model = vosk.Model(MODEL_PATH)

# Загрузка команд из файла

def load_commands():
    commands = {}
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, "r", encoding="utf-8") as file:
            for line in file:
                key, action = map(str.strip, line.split("=", 1))
                commands[key.lower()] = action
    return commands

COMMANDS = load_commands()

# Функция выполнения команд

def execute_command(command):
    command = command.lower().strip()
    if command in COMMANDS:
        action = COMMANDS[command]
        if action.startswith("hotkey"):
            keys = action.split()[1:]
            pyautogui.hotkey(*keys)
        else:
            os.system(action)
    else:
        handle_unknown_command(command)

# Отправка запроса в LM Studio

def handle_unknown_command(command):
    print(f"Отправляю команду в LM Studio: {command}")
    data = {
        "model": "qwen-14b",
        "messages": [{"role": "user", "content": command}]
    }
    try:
        response = requests.post(LM_STUDIO_URL, json=data)
        result = response.json()
        process_ai_response(result)
    except Exception as e:
        print(f"Ошибка связи с LM Studio: {e}")

# Обработка ответа от LM Studio

def process_ai_response(response):
    try:
        if "command_type" in response:
            if response["command_type"] == "script":
                execute_powershell(response["content"])
            elif response["command_type"] == "sequence":
                for step in response["steps"]:
                    if step["type"] == "script":
                        execute_powershell(step["content"])
                    elif step["type"] == "click":
                        pyautogui.click(step["x"], step["y"])
    except Exception as e:
        print(f"Ошибка обработки ответа AI: {e}")

# Выполнение PowerShell команд

def execute_powershell(command):
    print(f"Выполняю PowerShell: {command}")
    subprocess.run(["powershell", "-Command", command])

# Автоматический запуск LM Studio при необходимости

def start_lm_studio():
    try:
        response = requests.get(LM_STUDIO_URL, timeout=3)
        if response.status_code == 200:
            print("LM Studio уже запущен.")
            return
    except:
        print("Запуск LM Studio...")
        subprocess.Popen(["lm-studio.exe"])

# Запуск микрофона

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

device_info = sd.query_devices(None, "input")
samplerate = int(device_info["default_samplerate"])

# Распознавание речи

def recognize_speech():
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype="int16", channels=1, callback=callback):
        rec = vosk.KaldiRecognizer(model, samplerate)
        print("Говорите команду...")
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())["text"]
                print(f"Распознано: {result}")
                execute_command(result)
                break

# Прослушивание кнопки

def listen_on_press():
    start_lm_studio()
    while True:
        print("Нажмите Home, чтобы сказать команду...")
        keyboard.wait("home")
        recognize_speech()

# Запуск
listen_on_press()