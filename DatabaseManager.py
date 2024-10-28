from sqlalchemy import create_engine, text

class DatabaseManager:
    """
       Клас DatabaseManager відповідає за керування базою даних PostgreSQL з підтримкою PostGIS.

       Основні функції:
       1. Підключення до бази даних.
       2. Перевірка наявності таблиць та даних.
       3. Створення необхідних таблиць (кордонів, квадратів, секторів).
       4. Збереження геопросторових даних у базі.

       Використовує SQLAlchemy для роботи з базою даних та GeoPandas для геопросторових операцій.
    """

    def __init__(self, user, password, host, db_name):
        self.engine = create_engine(f'postgresql://{user}:{password}@{host}/{db_name}')

    def data_exists(self, table_name):
        """Перевіряє, чи є дані у таблиці."""
        # Перевіряємо, чи існує таблиця
        if not self.table_exists(table_name):
            print(f"В Таблиця '{table_name}' немає даних. Додаємо...")
            return False

        # Якщо таблиця існує, перевіряємо наявність даних
        query = f"SELECT COUNT(*) FROM {table_name};"
        with self.engine.connect() as conn:
            result = conn.execute(text(query)).scalar()
        return result > 0

    def table_exists(self, table_name):
        """Перевіряє, чи існує таблиця в базі даних."""
        query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = '{table_name}'
        );
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query)).scalar()
        return result

    def create_tables(self):
        """Створює таблиці лише, якщо їх немає."""
        if not self.table_exists('ukraine_border'):
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE ukraine_border (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100),
                        geometry GEOMETRY(Polygon, 4326)
                    );
                """))
                print("Таблиця 'ukraine_border' створена.")

        if not self.table_exists('grid_squares'):
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE grid_squares (
                        id SERIAL PRIMARY KEY,
                        geometry GEOMETRY(Polygon, 4326)
                    );
                """))
                print("Таблиця 'grid_squares' створена.")

        if not self.table_exists('grid_sectors'):
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE grid_sectors (
                        id SERIAL PRIMARY KEY,
                        geometry GEOMETRY(Polygon, 4326)
                    );
                """))
                print("Таблиця 'grid_sectors' створена.")

    def save_geodata(self, geodata, table_name):
        geodata.to_postgis(table_name, self.engine, if_exists='replace', index=False)
        print(f"Дані успішно збережено в таблиці {table_name}.")

