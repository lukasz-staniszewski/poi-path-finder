let MAP_BOUNDS = {
    NORTH: 55,
    SOUTH: 49,
    WEST: 14,
    EAST: 25
};
let MINZOOM = 6;
let MAXZOOM = 18;

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

let orangeIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

let map = L.map('map', {
    maxBounds: [[MAP_BOUNDS.SOUTH, MAP_BOUNDS.WEST], [MAP_BOUNDS.NORTH, MAP_BOUNDS.EAST]],
    minZoom: MINZOOM,
    maxZoom: MAXZOOM
}
).setView([(MAP_BOUNDS.NORTH + MAP_BOUNDS.SOUTH) / 2, (MAP_BOUNDS.WEST + MAP_BOUNDS.EAST) / 2], MINZOOM);
let markers = [];
let polyline;
let bounds = new L.LatLngBounds([[MAP_BOUNDS.SOUTH, MAP_BOUNDS.WEST], [MAP_BOUNDS.NORTH, MAP_BOUNDS.EAST]]);

let amenities;
async function fetch_amenities() {
    try {
        const response = await fetch('http://localhost:8000/amenities/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
        });
        const data = await response.json();
        amenities = data.amenities;
    } catch (error) {
        console.error('Error fetching amenities:', error);
    }
}
async function initialize() {
    await fetch_amenities();
}
initialize();

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: MAXZOOM + 1,
    attribution: '© OpenStreetMap contributors'
}).addTo(map);



let geocoder = new L.Control.geocoder({
    defaultMarkGeocode: false
}).on('markgeocode', function (e) {
    let bbox = e.geocode.bbox;
    let poly = L.polygon([
        bbox.getSouthEast(),
        bbox.getNorthEast(),
        bbox.getNorthWest(),
        bbox.getSouthWest()
    ]).addTo(map);
    map.fitBounds(poly.getBounds());
}).addTo(map);

function isWithinMapBounds(lat, lng) {

    return lat >= MAP_BOUNDS.SOUTH && lat <= MAP_BOUNDS.NORTH &&
        lng >= MAP_BOUNDS.WEST && lng <= MAP_BOUNDS.EAST;
}

function createPOIInputs() {
    let numberOfPOIs = document.getElementById('poi').value;
    let poiInputsDiv = document.getElementById('poiInputs');
    poiInputsDiv.innerHTML = '';

    for (let i = 0; i < numberOfPOIs; i++) {
        let input = document.createElement("input");
        input.type = "number";
        input.id = "poi_minutes_" + i;
        input.name = "poi_minutes_" + i;
        input.placeholder = "Minutes for POI " + (i + 1);
        input.min = 0;

        let select = document.createElement("select");
        select.id = "poi_type_" + i;
        select.name = "poi_type_" + i;
        select.placeholder = "Type for POI " + (i + 1);
        select.value = null;

        let defaultOption = document.createElement("option");
        defaultOption.value = null;
        defaultOption.text = "Select an option";
        select.appendChild(defaultOption);

        for (let j = 0; j < amenities.length; j++) {
            let option = document.createElement("option");
            option.value = amenities[j];
            option.text = amenities[j];
            select.appendChild(option);
        }

        poiInputsDiv.appendChild(input);
        poiInputsDiv.appendChild(select);
        poiInputsDiv.appendChild(document.createElement("br"));
    }
}

function addMarker(lat, lng, isFirst) {
    let icon = isFirst ? greenIcon : redIcon;
    let marker = L.marker([lat, lng], {
        draggable: true,
        icon: icon
    }).addTo(map).bindTooltip(isFirst ? "Start" : "End", { permanent: true, offset: [0, 0] });

    let initialPosition = [lat, lng];
    marker.on('dragend', function (e) {
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
        polyline = L.polyline(latlngs, { color: 'blue' }).addTo(map);
        map.fitBounds(polyline.getBounds());
    }
};


map.on('click', function (e) {
    if (!bounds.contains(e.latlng) || !isWithinMapBounds(e.latlng.lat, e.latlng.lng)) {
        return;
    }
    if (markers.length === 0) {
        addMarker(e.latlng.lat, e.latlng.lng, true);
    } else if (markers.length === 1) {
        addMarker(e.latlng.lat, e.latlng.lng, false);
    }
});

function createPath() {
    let additional_time = document.getElementById('minutes').value;
    let additional_distance = document.getElementById('km').value;
    let n_pois = document.getElementById('poi').value;
    let pois = new Array();

    if (markers.length != 2) {
        console.log("Not enough markers");
        return;
    }

    for (let i = 0; i < n_pois; i++) {
        let poiType = document.getElementById('poi_type_' + i).value;
        let poiMinutes = document.getElementById('poi_minutes_' + i).value;

        if (poiType === "null") {
            poiType = null;
        }
        if (poiMinutes === "") {
            poiMinutes = null;
        }

        pois.push({
            "type": poiType,
            "visit_time": poiMinutes
        });
    }

    let data = {
        "start": {
            "y": markers[0].getLatLng().lat,
            "x": markers[0].getLatLng().lng
        },
        "end": {
            "y": markers[1].getLatLng().lat,
            "x": markers[1].getLatLng().lng
        },
        "additional_time": additional_time,
        "additional_distance": additional_distance,
        "pois": pois
    };


    fetch('http://localhost:8000/route/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
        .then(response => response.json())
        .then(data => {
            console.log("Successfully created path: ");
            console.log(data);
            drawPath(data.points);

        })
        .catch(error => {
            console.error('Error:', error);
        });
};

function drawPath(points) {
    if (polyline) {
        map.removeLayer(polyline);
    }

    let latlngs = points.map(point => [point.map_point.y, point.map_point.x]);

    polyline = L.polyline(latlngs, { color: 'blue' }).addTo(map);
    map.fitBounds(polyline.getBounds());

    points.forEach(point => {
        if (point.is_poi) {
            let marker = L.marker([point.map_point.y, point.map_point.x], {
                draggable: false,
                icon: orangeIcon
            })
            marker.addTo(map).bindTooltip(point.poi_details.type + "(" + point.poi_details.visit_time + "m)", { permanent: true, offset: [0, 0] });
        };}
    );
}

// {
//     "start": {
//         "y": 52.24189997298265,
//         "x": 20.931916236877445
//     },
//     "end": {
//         "y": 52.219896288011746,
//         "x": 21.011803150177002
//     },
//     "additional_time": "100000",
//     "additional_distance": "1000000",
//     "pois": [
//         {
//             "type": "School",
//             "visit_time": "10"
//         },
//         {
//             "type": "Restaurant",
//             "visit_time": "20"
//         },
//         {
//             "type": "Car wash",
//             "visit_time": "30"
//         }
//     ]
// }