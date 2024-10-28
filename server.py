"""
Виконав: Стоян Олександр
Версія: Веб-реалізація

Цей код реалізує сервер на Flask для відображення геопросторових даних.
Дані кордону України, сітки квадратів та секторів завантажуються з бази даних
PostgreSQL з розширенням PostGIS. Сервер також віддає статичний файл index.html для
візуалізації карти через Leaflet.

"""
from flask import Flask, Response, send_from_directory
from sqlalchemy import create_engine
import geopandas as gpd
from flask_cors import CORS
import os

from DatabaseManager import DatabaseManager
from GeoDataManager import GeoDataManager


app = Flask(__name__)
CORS(app)

# Параметри підключення до бази даних
USER = 'geouser'
PASSWORD = '1'
HOST = 'localhost'
DB_NAME = 'geoproject'


engine = create_engine(f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}/{DB_NAME}")
db_manager = DatabaseManager(USER, PASSWORD, HOST, DB_NAME)
geo_manager = GeoDataManager()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

@app.route("/")
def serve_index():
    """Віддає index.html з папки проекту."""
    return send_from_directory(PROJECT_ROOT, "index.html")


@app.route("/api/ukraine_border")
def get_ukraine_border():
    ukraine = gpd.read_postgis("SELECT * FROM ukraine_border", engine, geom_col='geometry')
    return Response(ukraine.to_json(), mimetype='application/json')

@app.route("/api/grid_squares")
def get_grid_squares():
    grid = gpd.read_postgis("SELECT * FROM grid_squares", engine, geom_col='geometry')
    return Response(grid.to_json(), mimetype='application/json')

@app.route("/api/grid_sectors")
def get_grid_sectors():
    sectors = gpd.read_postgis("SELECT * FROM grid_sectors", engine, geom_col='geometry')
    return Response(sectors.to_json(), mimetype='application/json')

#Якщо у бд немає таблиць або даних, спершу потрібно запустити main.py
if __name__ == "__main__":
    app.run(port='5000')