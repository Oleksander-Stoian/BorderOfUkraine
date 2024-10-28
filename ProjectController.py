import geopandas as gpd

class ProjectController:
    """
        Клас ProjectController відповідає за координацію роботи проекту,
        керуючи взаємодією між базою даних, геопросторовими даними та візуалізацією.

        Завдання цього класу:
        1. Перевірити наявність таблиць та даних у базі PostgreSQL.
        2. Завантажити кордон України з джерела або бази даних.
        3. Генерувати сітку квадратів та сектори, якщо їх ще не існує.
        4. Відображати отримані дані у вигляді графіків через MapVisualizer.

        Використовує бібліотеку GeoPandas для роботи з геопросторовими даними.
    """

    def __init__(self, db_manager, geo_manager, visualizer):
        self.db_manager = db_manager
        self.geo_manager = geo_manager
        self.visualizer = visualizer

    def run(self):
        """Основна логіка програми: перевірка, створення та завантаження даних."""
        # Створення таблиць, якщо їх ще немає
        self.db_manager.create_tables()

        # Завантаження кордону України
        if not self.db_manager.data_exists('ukraine_border'):
            print("Завантажуємо кордон України...")
            ukraine = self.geo_manager.load_ukraine_border()
            self.db_manager.save_geodata(ukraine, 'ukraine_border')
        else:
            print("Кордони України вже завантажені.")
            ukraine = gpd.read_postgis(
                "SELECT * FROM ukraine_border",
                self.db_manager.engine,
                geom_col='geometry'
            )

        # Генерація сітки квадратів
        if not self.db_manager.data_exists('grid_squares'):
            print("Генеруємо сітку квадратів...")
            grid = self.geo_manager.generate_grid(ukraine.total_bounds, 10)

            # Обрізання сітки по кордону України
            clipped_grid = self.geo_manager.filter_grid_by_border(grid, ukraine)

            # Зберігаємо обрізану сітку, а не початкову
            self.db_manager.save_geodata(clipped_grid, 'grid_squares')
        else:
            print("Сітка квадратів вже завантажена.")
            clipped_grid = gpd.read_postgis(
                "SELECT * FROM grid_squares",
                self.db_manager.engine,
                geom_col='geometry'
            )

        # Генерація та збереження секторів
        if not self.db_manager.data_exists('grid_sectors'):
            print("Генеруємо сектори...")
            sectors = self.geo_manager.generate_sectors_parallel(clipped_grid)
            self.db_manager.save_geodata(sectors, 'grid_sectors')
        else:
            print("Сектори вже згенеровані.")
            sectors = gpd.read_postgis(
                "SELECT * FROM grid_sectors",
                self.db_manager.engine,
                geom_col='geometry'
            )

        # Обрізання секторів по кордону України
        clipped_sectors = self.geo_manager.filter_grid_by_border(sectors, ukraine)

        # Візуалізація кордону, сітки та секторів
        self.visualizer.display_combined(ukraine, clipped_grid, clipped_sectors,
                                         "Карта України із сіткою та секторами")


