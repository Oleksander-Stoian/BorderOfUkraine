
import pandas as pd

import geopandas as gpd
import numpy as np
import multiprocessing as mp

from shapely.geometry import Point, Polygon, shape, box
from geopy.distance import distance


def _find_intersections_for_sector(sector_id, sector, grid):
    """Допоміжна функція для паралельного знаходження перетинів для одного сектора."""
    sector_intersections = []
    for point_id, row in grid.iterrows():
        point = row.geometry
        if sector.contains(point):
            sector_intersections.append({
                'sector_id': sector_id,
                'point_id': point_id,
                'point_coordinates': point
            })
        print(point_id)
    return sector_intersections
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
        # Перетворюємо систему координат кордону України в метричну систему
        border_m = bounds.to_crs(epsg=3857)

        # Отримуємо межі в метрах
        minx, miny, maxx, maxy = border_m.total_bounds

        # Крок у метрах (10 км = 10000 м)
        step_m = step_km * 1000

        # Генерація сітки
        polygons = []
        x_coords = np.arange(minx, maxx, step_m)
        y_coords = np.arange(miny, maxy, step_m)

        for x in x_coords:
            for y in y_coords:
                polygon = Polygon([
                    (x, y),
                    (x + step_m, y),
                    (x + step_m, y + step_m),
                    (x, y + step_m)
                ])
                polygons.append(polygon)

        # Створюємо GeoDataFrame з усіма квадратами в метричній системі координат
        grid = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:3857")

        # Перетворюємо сітку назад у систему координат EPSG:4326 для подальшого використання
        grid = grid.to_crs(epsg=4326)
        return grid

    def filter_grid_by_border_squares(self, grid, border):
        """Повертає сітку квадратів, які перетинаються з кордоном України."""
        try:
            # Об'єднуємо всі частини кордону України в одну геометрію
            border_union = border.unary_union

            # Залишаємо тільки ті квадрати, що перетинають або знаходяться всередині кордону
            clipped_grid = grid[grid.intersects(border_union)]

        except Exception as e:
            print(f"Помилка при фільтрації квадратів: {e}")
            clipped_grid = gpd.GeoDataFrame(geometry=[], crs=grid.crs)  # Порожній GeoDataFrame у разі помилки

        return clipped_grid

    def filter_grid_by_border(self, grid, border):
        """Повертає тільки точки вершин квадратів, які знаходяться на території України."""
        try:
            # Об'єднуємо всі частини кордону України в одну геометрію
            border_union = border.unary_union

            # Список для зберігання вершин, що знаходяться всередині кордону
            valid_points = []

            # Перевірка кожного квадрата в сітці
            for _, row in grid.iterrows():
                geometry = row.geometry
                if geometry.geom_type == 'Polygon':
                    for coord in geometry.exterior.coords:
                        point = Point(coord)
                        # Додаємо точку, якщо вона знаходиться всередині кордону
                        if border_union.contains(point):
                            valid_points.append(point)

            # Створюємо GeoDataFrame з унікальними точками
            unique_points = gpd.GeoDataFrame(geometry=list(set(valid_points)), crs=grid.crs)

        except Exception as e:
            print(f"Помилка при фільтрації вершин: {e}")
            unique_points = gpd.GeoDataFrame(geometry=[], crs=grid.crs)  # Порожній GeoDataFrame у разі помилки

        return unique_points

    def generate_sector(self, point, azimuth, radius_km=10):
        """Генерує сектор для заданої точки та азимуту."""
        angle_step = 1  # Крок для малювання сектору
        angles = np.arange(azimuth - 30, azimuth + 30 + angle_step, angle_step)

        points = [
            (
                distance(kilometers=radius_km).destination((point.y, point.x), angle).longitude,
                distance(kilometers=radius_km).destination((point.y, point.x), angle).latitude
            )
            for angle in angles
        ]
        points.append((point.x, point.y))  # Додаємо початкову точку

        return Polygon(points)

    def generate_sectors_parallel(self, clipped_grid, border_union):
        """Паралельна генерація секторів для всіх вершин сітки на території України."""
        pool = mp.Pool(mp.cpu_count())  # Пул процесів
        tasks = []

        # Створюємо завдання для кожної вершини та азимуту
        for _, row in clipped_grid.iterrows():
            geometry = row.geometry

            if geometry.geom_type == 'Point':  # Перевірка, що геометрія є точкою
                for azimuth in [0, 120, 240]:
                    tasks.append((geometry, azimuth))

        # Виконуємо завдання паралельно
        results = pool.map(self._generate_sector_for_task, tasks)
        pool.close()
        pool.join()

        # Фільтруємо сектори, щоб залишити тільки ті, що повністю знаходяться в межах кордону України
        valid_sectors = [sector for sector in results if border_union.contains(sector)]

        return gpd.GeoDataFrame(geometry=valid_sectors, crs="EPSG:4326")

    def _generate_sector_for_task(self, args):
        """Функція для паралельного виклику, генерує сектор для однієї точки та азимуту."""
        point, azimuth = args
        return self.generate_sector(Point(point), azimuth)



    def find_intersections(self, sectors, grid):
        """Знаходить перетини вершин квадратів з секторами з використанням паралельної обробки."""
        # Підготовка завдань для паралельної обробки
        tasks = [(sector_id, sector, grid) for sector_id, sector in enumerate(sectors.geometry)]

        # Використання пулу процесів для паралельної обробки
        with mp.Pool(mp.cpu_count()) as pool:
            results = pool.starmap(_find_intersections_for_sector, tasks)

        # Об'єднання результатів з усіх процесів
        intersections = [item for sublist in results for item in sublist]

        return intersections