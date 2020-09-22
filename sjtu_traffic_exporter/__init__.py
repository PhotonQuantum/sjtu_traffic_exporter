from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from prometheus_client import Gauge, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from requests.exceptions import Timeout
import logging

from .models import SubCanteen
from .traffic import CanteenTraffic, LibraryTraffic

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
scheduler = BackgroundScheduler()

canteen_traffic = CanteenTraffic()
library_traffic = LibraryTraffic()

canteen_fields = canteen_traffic.fields()
library_fields = library_traffic.fields()
canteen_occupied_metric = Gauge("sjtu_canteen_occupied_seats", "上海交大餐厅在位人数",  ["place", "subplace"])
canteen_capacity_metric = Gauge("sjtu_canteen_capacity_seats", "上海交大餐厅可承载人数", ["place", "subplace"])
canteen_utilizaion_metric = Gauge("sjtu_canteen_utilization_percentage", "上海交大餐厅利用率", ["place", "subplace"])
library_occupied_metric = Gauge("sjtu_library_occupied_seats", "上海交大图书馆在位人数", ["place"])
library_capacity_metric = Gauge("sjtu_library_capacity_seats", "上海交大图书馆可承载人数", ["place"])
library_utilizaion_metric = Gauge("sjtu_library_utilization_percentage", "上海交大图书馆利用率", ["place"])

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})


@scheduler.scheduled_job("interval", seconds=30)
def update_canteen_metrics():
    try:
        canteens = canteen_traffic.get()
    except Timeout:
        logging.error("Timeout when fetching canteen metric.")
        return
    for canteen in canteens:
        if canteen.name in canteen_fields:
            if isinstance(canteen, SubCanteen):
                canteen_occupied_metric.labels(canteen.parent.name, canteen.name).set(canteen.occupied)
                canteen_capacity_metric.labels(canteen.parent.name, canteen.name).set(canteen.overall)
                canteen_utilizaion_metric.labels(canteen.parent.name, canteen.name).set(
                    (canteen.occupied / canteen.overall) if canteen.overall != 0 else 0)
            else:
                canteen_occupied_metric.labels(canteen.name, "").set(canteen.occupied)
                canteen_capacity_metric.labels(canteen.name, "").set(canteen.overall)
                canteen_utilizaion_metric.labels(canteen.name, "").set(
                    (canteen.occupied / canteen.overall) if canteen.overall != 0 else 0)


@scheduler.scheduled_job("interval", seconds=30)
def update_library_metrics():
    try:
        libraries = library_traffic.get()
    except Timeout:
        logging.error("Timeout when fetching canteen metric.")
        return
    for library in libraries:
        if library.name in library_fields:
            library_occupied_metric.labels(library.name).set(library.occupied)
            library_capacity_metric.labels(library.name).set(library.overall)
            library_utilizaion_metric.labels(library.name).set(
                (library.occupied / library.overall) if library.overall != 0 else 0)


scheduler.start()
