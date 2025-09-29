#!/usr/bin/env python3
"""
Принудительная остановка всех процессов бота
"""

import os
import sys
import subprocess
import time
import psutil

def force_stop_all():
    """Принудительно останавливает все процессы"""
    print("Принудительная остановка всех процессов...")
    
    # 1. Останавливаем через taskkill
    print("1. Остановка через taskkill...")
    try:
        result = subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                              capture_output=True, timeout=10)
        print(f"   Результат: {result.returncode}")
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    # 2. Останавливаем через psutil
    print("2. Остановка через psutil...")
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == 'python.exe':
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main.py' in cmdline or 'run_bot.py' in cmdline:
                        proc.terminate()
                        print(f"   Остановлен процесс {proc.info['pid']}")
                        time.sleep(0.5)
                except:
                    pass
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    # 3. Ждем
    print("3. Ожидание 5 секунд...")
    time.sleep(5)
    
    # 4. Проверяем
    print("4. Проверка...")
    try:
        remaining = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] == 'python.exe':
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'main.py' in cmdline or 'run_bot.py' in cmdline:
                    remaining.append(proc.info['pid'])
        
        if remaining:
            print(f"   Остались процессы: {remaining}")
            # Принудительно убиваем
            for pid in remaining:
                try:
                    os.kill(pid, 9)
                    print(f"   Принудительно остановлен {pid}")
                except:
                    pass
        else:
            print("   Все процессы остановлены")
    except Exception as e:
        print(f"   Ошибка проверки: {e}")
    
    print("Готово!")

if __name__ == '__main__':
    force_stop_all()
