let map = L.map('map', {
    maxBounds: [[49, 14], [55, 25]],
    minZoom: 6,
    maxZoom: 18
    }
).setView([51.9189, 19.1343786], 6);
let markers = [];
let polyline;

let boundsOfPoland = {
    north: 55.03,
    south: 49.05,
    west: 14.11,
    east: 24.00
};
let boundsOfPoland2 = [[49.05, 14.11], [55.03, 24.00]];
let bounds = new L.LatLngBounds(boundsOfPoland2);
console.log(bounds);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

let geocoder = new L.Control.geocoder({
    defaultMarkGeocode: false
}).on('markgeocode', function(e) {
    let bbox = e.geocode.bbox;
    let poly = L.polygon([
        bbox.getSouthEast(),
        bbox.getNorthEast(),
        bbox.getNorthWest(),
        bbox.getSouthWest()
    ]).addTo(map);
    map.fitBounds(poly.getBounds());
}).addTo(map);

function isWithinPoland(lat, lng) {
    return lat >= boundsOfPoland.south && lat <= boundsOfPoland.north &&
           lng >= boundsOfPoland.west && lng <= boundsOfPoland.east;
}

function createPOIInputs() {
    let numberOfPOIs = document.getElementById('poi').value;
    let poiInputsDiv = document.getElementById('poiInputs');
    poiInputsDiv.innerHTML = '';

    for (let i = 0; i < numberOfPOIs; i++) {
        let input = document.createElement("input");
        input.type = "number";
        input.id = "minutes_" + i;
        input.name = "minutes_" + i;
        input.placeholder = "Minutes for POI " + (i + 1);

        poiInputsDiv.appendChild(input);
        poiInputsDiv.appendChild(document.createElement("br"));
    }
}

function logValues() {
    let minutes = document.getElementById('minutes').value;
    let km = document.getElementById('km').value;
    let numberOfPOIs = document.getElementById('poi').value;

    console.log("Minutes:", minutes);
    console.log("Kilometers:", km);
    console.log("Number of POIs:", numberOfPOIs);

    for (let i = 0; i < numberOfPOIs; i++) {
        let poiMinutes = document.getElementById('minutes_' + i).value;
        console.log("Minutes for POI " + (i + 1) + ":", poiMinutes);
    }

    if (markers.length >= 2) {
        console.log("Start Point Lat, Lon:", markers[0].getLatLng());
        console.log("End Point Lat, Lon:", markers[1].getLatLng());
    }
}

let greenIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

let redIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

function addMarker(lat, lng, isFirst) {
    var icon = isFirst ? greenIcon : redIcon;
    var marker = L.marker([lat, lng], {
        draggable: true,
        icon: icon
    }).addTo(map).bindTooltip(isFirst ? "Start" : "End", {permanent: true, offset: [0, 0]});

    var initialPosition = [lat, lng];
    marker.on('dragend', function(e) {
        if (!bounds.contains(e.target.getLatLng())) {
            e.target.setLatLng(initialPosition);
        } else {
            initialPosition = e.target.getLatLng();
        }
        updatePath();
    });

    markers.push(marker);
    updatePath();
}


function updatePath() {
    if (polyline) {
        map.removeLayer(polyline);
    }

    if (markers.length === 2) {
        let latlngs = [markers[0].getLatLng(), markers[1].getLatLng()];
        polyline = L.polyline(latlngs, {color: 'blue'}).addTo(map);
        map.fitBounds(polyline.getBounds());
    }
}

map.on('click', function(e) {
    if (!bounds.contains(e.latlng)) {
        alert("Please place markers within Poland.");
        return;
    }
    if (!isWithinPoland(e.latlng.lat, e.latlng.lng)) {
        alert("Please place markers within Poland.");
        return;
    }
    if (markers.length === 0) {
        addMarker(e.latlng.lat, e.latlng.lng, true);
    } else if (markers.length === 1) {
        addMarker(e.latlng.lat, e.latlng.lng, false);
    }
});
