#!/usr/bin/env python3
"""
Скрипт для остановки всех экземпляров бота
"""

import os
import sys
import subprocess
import time

def stop_bot():
    """Останавливает все экземпляры бота"""
    print("🛑 Остановка всех экземпляров бота...")
    
    # Останавливаем все процессы Python
    print("1. Поиск процессов Python...")
    try:
        # Сначала пробуем остановить через taskkill
        result = subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                              capture_output=True, timeout=10, text=True)
        if result.returncode == 0:
            print("   ✅ Процессы остановлены через taskkill")
        else:
            print("   ⚠️ taskkill не сработал, пробуем через psutil...")
            try:
                import psutil
                python_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                                  if p.info['name'] == 'python.exe']
                
                if python_processes:
                    print(f"   Найдено процессов Python: {len(python_processes)}")
                    for proc in python_processes:
                        try:
                            cmdline = ' '.join(proc.info['cmdline'] or [])
                            if 'main.py' in cmdline or 'run_bot.py' in cmdline:
                                proc.terminate()
                                print(f"   Остановлен процесс {proc.info['pid']}: {cmdline[:50]}...")
                            else:
                                print(f"   Пропущен процесс {proc.info['pid']}: {cmdline[:50]}...")
                        except Exception as e:
                            print(f"   ❌ Ошибка остановки процесса {proc.info['pid']}: {e}")
                    print("   ✅ Процессы остановлены через psutil")
                else:
                    print("   📝 Процессы Python не найдены")
            except ImportError:
                print("   ⚠️ psutil не установлен, используем только taskkill")
            except Exception as e:
                print(f"   ❌ Ошибка остановки через psutil: {e}")
    except Exception as e:
        print(f"   ❌ Ошибка остановки процессов: {e}")
    
    # Ждем
    print("2. Ожидание 3 секунды...")
    time.sleep(3)
    
    # Проверяем, что процессы остановлены
    print("3. Проверка остановки...")
    try:
        import psutil
        remaining_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                             if p.info['name'] == 'python.exe' and 
                             ('main.py' in ' '.join(p.info['cmdline'] or []) or 
                              'run_bot.py' in ' '.join(p.info['cmdline'] or []))]
        
        if remaining_processes:
            print(f"   ⚠️ Остались процессы: {len(remaining_processes)}")
            for proc in remaining_processes:
                print(f"   PID {proc.info['pid']}: {' '.join(proc.info['cmdline'] or [])[:50]}...")
        else:
            print("   ✅ Все процессы бота остановлены")
    except ImportError:
        print("   ⚠️ psutil не установлен, пропускаем проверку")
    except Exception as e:
        print(f"   ❌ Ошибка проверки: {e}")
    
    print("🎉 Готово!")

if __name__ == '__main__':
    stop_bot()

