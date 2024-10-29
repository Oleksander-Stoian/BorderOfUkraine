import geopandas as gpd
def remove_shared_points_from_grid(grid, border):
    """
        Видаляє з сітки ті точки, які збігаються з точками кордону України.
        !Тимчасове вирішення проблеми, з малювання секторів з точок кордону!
    """

    def extract_points(geometry):
        """Витягує всі точки з Polygon та MultiPolygon."""
        if geometry.geom_type == 'Polygon':
            return list(geometry.exterior.coords)
        elif geometry.geom_type == 'MultiPolygon':
            points = []
            for polygon in geometry.geoms:
                points.extend(polygon.exterior.coords)
            return points
        else:
            return []  # Ігноруємо інші типи геометрій

    # Отримуємо унікальні координати з кордону України
    border_points = set(
        (round(point[0], 6), round(point[1], 6))
        for geometry in border.geometry
        for point in extract_points(geometry)
    )

    def filter_grid_points(geometry):
        """Видаляє з полігону ті вершини, які збігаються з точками кордону."""
        if geometry.geom_type == 'Polygon':
            new_coords = [coord for coord in geometry.exterior.coords
                          if (round(coord[0], 6), round(coord[1], 6)) not in border_points]
            return Polygon(new_coords) if len(new_coords) >= 3 else None
        elif geometry.geom_type == 'MultiPolygon':
            new_polygons = [filter_grid_points(polygon) for polygon in geometry.geoms]
            return MultiPolygon([p for p in new_polygons if p is not None])
        else:
            return geometry  # Інші типи залишаємо без змін

    # Оновлюємо геометрії сітки з видаленими точками
    cleaned_geometries = grid.geometry.apply(filter_grid_points)
    grid_cleaned = grid.copy()
    grid_cleaned.geometry = cleaned_geometries

    # Видаляємо порожні або некоректні геометрії
    grid_cleaned = grid_cleaned[~grid_cleaned.is_empty]

    return grid_cleaned
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
        #Тимчасове рішення, потрібно змінити
        cleaned_border = remove_shared_points_from_grid(clipped_grid, ukraine)

        # Генерація та збереження секторів
        if not self.db_manager.data_exists('grid_sectors'):
            print("Генеруємо сектори...")
            sectors = self.geo_manager.generate_sectors_parallel(cleaned_border)
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


