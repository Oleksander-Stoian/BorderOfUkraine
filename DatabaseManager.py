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
                        geometry GEOMETRY(Polygon, 4326) NOT NULL,
                        CONSTRAINT grid_squares_geometry_unique UNIQUE (geometry)
                    );
                """))
                print("Таблиця 'grid_squares' створена.")

        if not self.table_exists('grid_sectors'):
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE grid_sectors (
                        id SERIAL PRIMARY KEY,
                        geometry GEOMETRY(Polygon, 4326) NOT NULL,
                        CONSTRAINT grid_sectors_geometry_unique UNIQUE (geometry)
                    );
                """))
                print("Таблиця 'grid_sectors' створена.")

        if not self.table_exists('sector_intersections'):
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE sector_intersections (
                        id SERIAL PRIMARY KEY,
                        sector_id INTEGER NOT NULL,
                        point_id INTEGER NOT NULL,
                        point_coordinates GEOMETRY(Point, 4326) NOT NULL,
                        FOREIGN KEY (sector_id) REFERENCES grid_sectors(id),
                        FOREIGN KEY (point_id) REFERENCES grid_squares(id)
                    );
                """))
                print("Таблиця 'sector_intersections' створена.")

    def save_geodata(self, geodata, table_name):
        try:
            with self.engine.connect() as conn:
                # Перевірка, чи є залежні таблиці, та їх очищення
                if table_name == 'grid_squares':
                    conn.execute(text("DELETE FROM sector_intersections;"))

                # Очищення основної таблиці з використанням CASCADE
                conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"))

            # Збереження нових даних
            geodata.to_postgis(table_name, self.engine, if_exists='append', index=False)
            print(f"Дані успішно збережено в таблиці {table_name}.")
        except Exception as e:
            print(f"Помилка при збереженні даних у таблицю {table_name}: {e}")
            raise e

    def save_intersections(self, intersections):
        """Зберігає результати перетину у таблицю sector_intersections."""
        with self.engine.connect() as conn:
            for intersection in intersections:
                query = text("""
                    INSERT INTO sector_intersections (sector_id, point_id, point_coordinates)
                    VALUES (:sector_id, :point_id, ST_GeomFromText(:point_wkt, 4326))
                """)
                conn.execute(query, {
                    'sector_id': intersection['sector_id'],
                    'point_id': intersection['point_id'],
                    'point_wkt': intersection['point_coordinates'].wkt
                })
        print("Перетини успішно збережені у таблиці sector_intersections.")