install:
	python -m pip install -r requirements.txt
setup:
	python manage.py migrate
enrich:
	python manage.py enrich_fuel_stations
test:
	python manage.py test
run:
	python manage.py runserver 0.0.0.0:8000
