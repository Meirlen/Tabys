import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --- Ваши учетные данные для PostgreSQL ---
# Используйте localhost, если скрипт запускается на той же машине,
# где доступен PostgreSQL, или если порт проброшен на localhost.
# Если 'admin-db' - это имя хоста в Docker-сети, и скрипт запускается
# вне этой сети, вам нужен хост, доступный снаружи (например, 'localhost').
DB_USER = "postgres"
DB_PASSWORD = "Apas456j!98424xss5"
DB_HOST = "localhost"  # Используем POSTGRES_DB_HOST, так как это обычно для подключения извне Docker
DB_PORT = "5432"
DB_NAME = "alem"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Таблицы, связанные с экспертами, для удаления (в правильном порядке)
# Сначала удаляем таблицы, которые ссылаются на 'experts'
TABLES_TO_DROP = [
    "education",
    "work_experience",
    "collaboration_requests",
    "experts"  # 'experts' удаляется последней
]

def delete_expert_related_tables():
    print(f"Попытка подключения к базе данных: {DB_NAME} на хосте {DB_HOST}...")
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        print("Успешное подключение к базе данных.")
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return

    print("\nВНИМАНИЕ! Следующие таблицы и все их данные будут УДАЛЕНЫ:")
    for table_name in TABLES_TO_DROP:
        print(f"- {table_name}")

    # Запрашиваем подтверждение у пользователя
    confirmation = input("Вы уверены, что хотите продолжить? (да/нет): ").strip().lower()

    if confirmation != "да":
        print("Операция отменена пользователем.")
        session.close()
        return

    print("\nНачинаем удаление таблиц...")
    try:
        for table_name in TABLES_TO_DROP:
            # Используем IF EXISTS, чтобы избежать ошибки, если таблица уже удалена или не существует
            # Для PostgreSQL также можно использовать CASCADE для автоматического удаления зависимых объектов,
            # но явное удаление в правильном порядке более контролируемо.
            # Пример с CASCADE (используйте с ОСТОРОЖНОСТЬЮ, если удаляете 'experts' первой):
            # sql_command = text(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
            sql_command = text(f"DROP TABLE IF EXISTS {table_name};")

            try:
                print(f"Удаление таблицы '{table_name}'...")
                session.execute(sql_command)
                session.commit() # Коммитим после каждого удаления таблицы
                print(f"Таблица '{table_name}' успешно удалена (если существовала).")
            except sqlalchemy.exc.ProgrammingError as prog_err:
                # Эта ошибка может возникнуть, если таблица не существует и IF EXISTS не сработало как ожидалось
                # (хотя обычно оно должно). Или из-за проблем с правами.
                session.rollback()
                print(f"Предупреждение при удалении таблицы '{table_name}': {prog_err}")
                print("Возможно, таблица не существовала или недостаточно прав. Проверьте логи БД.")
            except Exception as e:
                session.rollback() # Откатываем транзакцию в случае другой ошибки
                print(f"Ошибка при удалении таблицы '{table_name}': {e}")
                # Прерываем процесс, если одна из зависимых таблиц не может быть удалена
                if table_name != "experts": # Если это не основная таблица 'experts'
                    print("Прерывание операции из-за ошибки при удалении зависимой таблицы.")
                    return


        print("\nВсе указанные таблицы, связанные с экспертами, были удалены (если существовали).")
    except Exception as e:
        # Общая ошибка, если что-то пошло не так на верхнем уровне
        print(f"Произошла общая ошибка во время операции: {e}")
    finally:
        session.close()
        print("Соединение с базой данных закрыто.")

if __name__ == "__main__":
    print("--------------------------------------------------------------------")
    print("СКРИПТ ДЛЯ УДАЛЕНИЯ ТАБЛИЦ, СВЯЗАННЫХ С ЭКСПЕРТАМИ ИЗ БАЗЫ ДАННЫХ")
    print("--------------------------------------------------------------------")
    print("Пожалуйста, убедитесь, что вы понимаете последствия этой операции.")
    print("Будут удалены таблицы и все данные в них без возможности восстановления!")
    print("Настоятельно рекомендуется сделать резервную копию перед запуском.")
    print("--------------------------------------------------------------------")

    # Запуск основной функции
    delete_expert_related_tables()