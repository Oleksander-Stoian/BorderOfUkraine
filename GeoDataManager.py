import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np
import multiprocessing as mp
class GeoDataManager:
    """
        Клас GeoDataManager відповідає за роботу з геопросторовими даними, такими як кордон України,
        сітка квадратів та сектори. Він забезпечує генерацію, фільтрацію та обробку цих даних.

        Основні функції:
        1. Завантаження кордону України.
        2. Генерація сітки квадратів заданого розміру.
        3. Фільтрація сітки, щоб залишити тільки частини, що перетинають кордон України.
        4. Генерація секторів для заданих точок сітки з певним азимутом.
        5. Використання багатопоточності для оптимізації генерації секторів.
    """
    def load_ukraine_border(self):
        try:
                url = "https://datahub.io/core/geo-countries/r/0.geojson"
                countries = gpd.read_file(url)
                ukraine = countries[countries['ADMIN'] == 'Ukraine']
                print("Кордони України завантажено з інтернету.")
        except Exception as e:
                print(f"Помилка при завантаженні кордону України: {e}")
                return None  # Повертаємо None у разі помилки

        return ukraine

    def generate_grid(self, bounds, step_km):
        """Генерує сітку квадратів заданого розміру (step_km у км)."""
        minx, miny, maxx, maxy = bounds
        step_deg = step_km / 111  # Перетворюємо кілометри в градуси (приблизно)

        polygons = []
        for x in np.arange(minx, maxx, step_deg):
            for y in np.arange(miny, maxy, step_deg):
                polygon = Polygon([
                    (x, y),
                    (x + step_deg, y),
                    (x + step_deg, y + step_deg),
                    (x, y + step_deg)
                ])
                polygons.append(polygon)

        # Створюємо GeoDataFrame з усіма квадратами
        grid = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326")
        return grid

    def filter_grid_by_border(self, grid, border):
        """ Фільтрує сітку квадратів, залишаючи тільки ті, що перетинають кордон України."""
        # Перетин сітки з кордоном
        try:
            clipped_grid = gpd.overlay(grid, border, how='intersection', keep_geom_type=False)

        except Exception as e:
            print(f"Помилка при фільтрації сітки: {e}")
            clipped_grid = gpd.GeoDataFrame(geometry=[], crs=grid.crs)  # Порожній GeoDataFrame у разі помилки

        return clipped_grid

    def generate_sector(self, point, azimuth, radius_km=5):
        """Генерує сектор для заданої точки та азимуту."""
        angle_step = 1  # Крок для малювання сектору
        angles = np.arange(azimuth - 30, azimuth + 30 + angle_step, angle_step)

        points = [
            (
                point.x + radius_km * np.cos(np.deg2rad(angle)) / 111,
                point.y + radius_km * np.sin(np.deg2rad(angle)) / 111
            )
            for angle in angles
        ]
        points.append((point.x, point.y))  # Додаємо початкову точку

        return Polygon(points)

    # Метод не використовується, оскільки замість нього використовується generate_sectors_parallel() для покращення продуктивності.
    # Можна використовувати для порівняння продуктивності.
    def generate_sectors_for_grid(self, grid):
        """Генерує сектори для всіх вершин сітки."""
        sectors = []
        for _, row in grid.iterrows():
            geometry = row.geometry

            # Перевірка на тип геометрії
            if geometry.geom_type == 'Polygon':
                polygons = [geometry]
            elif geometry.geom_type == 'MultiPolygon':
                polygons = list(geometry.geoms)  # Отримуємо окремі полігони
            else:
                continue  # Пропускаємо, якщо це не Polygon або MultiPolygon

            # Проходимо по кожному полігону та його вершинах
            for polygon in polygons:
                for point in polygon.exterior.coords:
                    for azimuth in [0, 120, 240]:
                        sector = self.generate_sector(Point(point), azimuth)
                        sectors.append(sector)

        return gpd.GeoDataFrame(geometry=sectors, crs="EPSG:4326")

    # Розпаралелиння
    def generate_sector_for_point(args):
        """Функція для генерації сектору для однієї точки."""
        point, azimuth = args
        return GeoDataManager().generate_sector(Point(point), azimuth)

    def generate_sectors_parallel(self, grid):
        """Паралельна генерація секторів для всіх вершин сітки."""
        pool = mp.Pool(mp.cpu_count())  # пул процесів
        tasks = []

        # Створюємо завдання для кожної вершини та азимуту
        for _, row in grid.iterrows():
            geometry = row.geometry
            polygons = (
                [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
            )
            for polygon in polygons:
                for point in polygon.exterior.coords:
                    for azimuth in [0, 120, 240]:
                        tasks.append((point, azimuth))

        # Виконуємо завдання паралельно
        results = pool.map(self._generate_sector_for_task, tasks)
        pool.close()
        pool.join()

        return gpd.GeoDataFrame(geometry=results, crs="EPSG:4326")

    def _generate_sector_for_task(self, args):
        """Функція для паралельного виклику, генерує сектор для однієї точки та азимуту."""
        point, azimuth = args
        return self.generate_sector(Point(point), azimuth)