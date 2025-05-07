def normalize_phone_number(phone_number):
    # Удаляем все символы, кроме цифр
    digits = ''.join(filter(str.isdigit, phone_number))

    # Проверяем длину номера и добавляем недостающие префиксы
    if len(digits) == 11 and digits.startswith('8'):
        return '7' + digits[1:]  # Заменяем '8' на '7'
    elif len(digits) == 10:
        return '7' + digits  # Добавляем '7' в начало
    elif len(digits) == 12 and digits.startswith('7'):
        return digits  # Номер уже в нужном формате
    elif len(digits) == 11 and digits.startswith('7'):
        return digits  # Считаем корректным
    else:
        return phone_number





# Примеры использования
phone_numbers = [
    "877711745741",
    "7711745741",
    "+7711745741",
    "7711745741",
    "77711745741"
]

for number in phone_numbers:
    try:
        print(normalize_phone_number(number))
    except ValueError as e:
        print(e)
