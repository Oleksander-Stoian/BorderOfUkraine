"""
Виконав: Стоян Олександр
Версія: Локальна реалізація з графічним відображенням через Python

Цей код реалізує керування проєктом через об'єкти, такі як DatabaseManager,
GeoDataManager та MapVisualizer. Він дозволяє працювати з геопросторовими даними,
генерувати сітку квадратів та сектори, а також відображати результати за допомогою
графіків у Python. Логіка контролює перевірку таблиць у базі даних, завантаження
даних та візуалізацію.

"""
from DatabaseManager import DatabaseManager
from GeoDataManager import GeoDataManager
from MapVisualizer import MapVisualizer
from ProjectController import ProjectController


if __name__ == "__main__":
    db_manager = DatabaseManager(
        user='geouser',
        password='1',
        host='localhost',
        db_name='geoproject'
    )
    geo_manager = GeoDataManager()
    visualizer = MapVisualizer()

    # Запуск контролера проекту
    controller = ProjectController(db_manager, geo_manager, visualizer)
    controller.run()