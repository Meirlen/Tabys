import re
from typing import Optional

class InstanceConfig:
    def __init__(self, city: str, address: str, category: str, name: str):
        self.city = city
        self.address = address
        self.category = category
        self.name = name

    def __repr__(self):
        return f"InstanceConfig(city={self.city}, category={self.category}, name={self.name})"

def extract_config(text: str) -> Optional[InstanceConfig]:
    """
    Извлекает параметры конфигурации из текста и создает объект InstanceConfig.
    """
    # Используем регулярные выражения для извлечения значений
    city_match = re.search(r'"city":\s*"(.*?)"', text)
    category_match = re.search(r'"category":\s*"(.*?)"', text)
    name_match = re.search(r'"name":\s*"(.*?)"', text)
    address_match = re.search(r'"address":\s*"(.*?)"', text)
    if city_match and category_match and name_match:
        city = city_match.group(1)
        category = category_match.group(1)
        name = name_match.group(1)
        try:
            address = address_match.group(1)
        except:
            address = None
        return InstanceConfig(city=city,address = address, category=category, name=name)

    return None


def extract_services(text):
    """
    Извлекает массив services из текста.

    Args:
        text (str): Текст, содержащий данные с ключами "service".

    Returns:
        list: Список значений ключа "service".
    """
    # Используем регулярное выражение для поиска всех значений "service"
    services = re.findall(r'"service":\s*"(.*?)"', text)
    return services