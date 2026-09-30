import json

from django.http import HttpResponse, JsonResponse
from django.views import View

from .services.errors import PlanError
from .services.planner import plan_trip


def health(request):
    return JsonResponse({"status": "ok"})


class RouteFuelView(View):
    """POST {"start": "...", "finish": "..."} or GET ?start=...&finish=..."""

    def get(self, request):
        return self._run(request.GET.get("start", ""), request.GET.get("finish", ""))

    def post(self, request):
        try:
            body = json.loads(request.body or b"{}")
        except ValueError:
            return JsonResponse({"error": "Request body must be valid JSON."}, status=400)
        if not isinstance(body, dict):
            return JsonResponse({"error": "Request body must be a JSON object."}, status=400)
        return self._run(str(body.get("start") or ""), str(body.get("finish") or ""))

    def _run(self, start, finish):
        start, finish = start.strip(), finish.strip()
        if not start or not finish:
            return JsonResponse({"error": "Both 'start' and 'finish' are required."}, status=400)
        if start.casefold() == finish.casefold():
            return JsonResponse({"error": "'start' and 'finish' must be different."}, status=400)
        try:
            return JsonResponse(plan_trip(start, finish))
        except PlanError as exc:
            return JsonResponse({"error": str(exc)}, status=exc.status)


MAP_HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fuel route map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
 body{margin:0;font-family:system-ui,sans-serif}
 #bar{display:flex;gap:6px;flex-wrap:wrap;padding:8px}
 #bar input{flex:1;min-width:140px;padding:8px;font-size:16px}
 #bar button{padding:8px 14px;font-size:16px}
 #map{height:65vh}
 #info{padding:8px;font-size:15px;line-height:1.5}
</style></head>
<body>
<div id="bar">
 <input id="start" value="New York, NY" placeholder="Start (City, ST or lat,lon)">
 <input id="finish" value="Los Angeles, CA" placeholder="Finish (City, ST or lat,lon)">
 <button id="go">Plan fuel stops</button>
</div>
<div id="map"></div>
<div id="info">Enter a start and finish in the USA.</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var map = L.map('map').setView([39.5, -98.35], 4);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
var layer = L.layerGroup().addTo(map);
var info = document.getElementById('info');

function popup(text) {
  var el = document.createElement('div');
  el.textContent = text;
  return el;
}

document.getElementById('go').onclick = function () {
  var s = document.getElementById('start').value;
  var f = document.getElementById('finish').value;
  info.textContent = 'Working...';
  fetch('/api/route/?start=' + encodeURIComponent(s) + '&finish=' + encodeURIComponent(f))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.error) { info.textContent = d.error; return; }
      layer.clearLayers();
      var line = L.geoJSON(d.route.geojson, {style: {weight: 4}}).addTo(layer);
      map.fitBounds(line.getBounds());
      L.marker([d.start.latitude, d.start.longitude]).bindPopup(popup('Start')).addTo(layer);
      L.marker([d.finish.latitude, d.finish.longitude]).bindPopup(popup('Finish')).addTo(layer);
      d.fuel.stops.forEach(function (st, i) {
        var label = (i + 1) + '. ' + st.station_name + ' (' + st.city + ', ' + st.state + ') - ' +
          st.fuel_gallons + ' gal @ $' + st.price_per_gallon + ' = $' + st.cost;
        L.circleMarker([st.latitude, st.longitude], {radius: 9, color: '#c0392b', fillOpacity: 0.8})
          .bindPopup(popup(label)).addTo(layer);
      });
      info.textContent = d.route.distance_miles + ' miles, ' + d.fuel.stops.length +
        ' fuel stop(s), total fuel cost $' + d.fuel.total_cost + ' (' + d.performance.external_api_calls +
        ' external API call(s), ' + d.performance.processing_ms + ' ms)';
    })
    .catch(function () { info.textContent = 'Request failed.'; });
};
</script></body></html>
"""


def map_page(request):
    return HttpResponse(MAP_HTML)
