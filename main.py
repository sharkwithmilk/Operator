import os
import json
import sys
import pyautogui
import queue
import sounddevice as sd
import vosk
import keyboard

if getattr(sys, 'frozen', False):  # Если запущено из .exe
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "vosk-model-small-ru-0.22")

if not os.path.exists(MODEL_PATH):
    raise Exception(f"Модель {MODEL_PATH} не найдена! Поместите её рядом с .exe.")

model = vosk.Model(MODEL_PATH)
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

# Запуск микрофона
device_info = sd.query_devices(None, "input")
samplerate = int(device_info["default_samplerate"])

# Словарь команд
COMMANDS = {
    "браузер": lambda: os.system("start msedge"),
    "блокнот": lambda: os.system("notepad.exe"),
    "закрыть": lambda: pyautogui.hotkey("alt", "f4"),
    "вкладка": lambda: pyautogui.hotkey("ctrl", "t"),
    "открой календарь": lambda: os.system("start outlookcal:"),
    "открой я класс": lambda: os.system('start msedge --profile-directory="Profile 1" "https://www.yaklass.ru"'),
}

def load_commands_from_file(filename=BASE_DIR+r'\Commands.dat'):
    commands = {}
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден!")
        return commands

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if "=" in line:
                key, action = line.split("=", 1)
                key = key.strip().lower()
                action = action.strip()

                if action.startswith("hotkey"):
                    keys = action.split()[1:]  # Убираем "hotkey"
                    commands[key] = lambda k=keys: pyautogui.hotkey(*k)
                else:
                    commands[key] = lambda a=action: os.system(a)

    return commands

# Загрузка команд
COMMANDS = load_commands_from_file()

def execute_command(command):
    command = command.strip().lower()
    if command in COMMANDS:
        COMMANDS[command]()

def recognize_speech():
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, device=None,
                           dtype="int16", channels=1, callback=callback):
        rec = vosk.KaldiRecognizer(model, samplerate)
        print("Говорите команду...")

        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())["text"]
                print(f"Распознано: {result}")
                execute_command(result)  # Выполняем команду сразу
                break # Завершаем прослушивание после одной команды



def listen_on_press():

    while True:
        print("Нажмите home, чтобы сказать команду...")
        keyboard.wait("home")  # Ждем нажатия
        recognize_speech()  # Запускаем распознавание одной команды

# Запускаем режим Push-to-Talk
listen_on_press()