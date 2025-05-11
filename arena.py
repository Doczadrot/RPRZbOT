# name = input(" Введите Имя: ")
# age = input("Введите возраст: ")
# print(f'Привет {name} тебе {age} лет')
from itertools import count

# count_1 = int(input("Введите первое слогаемое: "))
# count_2 = int(input("Введите Второе слогаемое: "))
# result = count_1 + count_2
# print(f'Cумма чисел ровна {result}')

#Задача №3: Проверка числа на положительность

# count = int(input('Введите любое число'))
# if count > 0:
#     print(f'{count} число положительно')
# else:
#     print(f'{count} число не является положительным')

#Задача №4: Обратный отсчет.


#Задача №5: Инвентарь героя

# inventory = ["Меч Правды", "Щит Могущества", "Зелье Исцеления", "Свиток Телепортации"]
# for i in inventory:
#     print(f"Предмет: {i}")

#Задача №6: Функция профиля героя
def display_hero_profile(hero_name, level):
    hero_name = str(hero_name)
    print(f'Герой:{hero_name} Уровень: {level}')

display_hero_profile("Axe",3)