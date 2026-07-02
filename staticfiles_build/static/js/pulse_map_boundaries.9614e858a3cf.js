/**

 * PULSE — Barangay boundary choropleth layer (prototype-accurate GeoJSON + interactions).

 * Expects Leaflet map instance + static GeoJSON / APTAS risk API URLs.

 */

window.PulseMapBoundaries = (function () {

  'use strict';



  var BASE_BARANGAY_STYLE = {

    color: '#a0a0a0',

    weight: 1,

    opacity: 0.75,

    fillColor: 'transparent',

    fillOpacity: 0,

  };



  var CITY_STYLE = {

    color: '#000000',

    weight: 3,

    opacity: 0.85,

    fillColor: 'transparent',

    fillOpacity: 0,

    dashArray: '6, 4',

  };



  var RISK_STYLES = {

    Low: {

      fillColor: '#16A34A',

      fillOpacity: 0.08,

      color: '#a0a0a0',

      weight: 1,

      opacity: 0.75,

    },

    Moderate: {

      fillColor: '#F59E0B',

      fillOpacity: 0.22,

      color: '#B45309',

      weight: 1.25,

      opacity: 0.8,

    },

    High: {

      fillColor: '#DC2626',

      fillOpacity: 0.28,

      color: '#B91C1C',

      weight: 1.5,

      opacity: 0.85,

    },

    Critical: {

      fillColor: '#7C3AED',

      fillOpacity: 0.34,

      color: '#6D28D9',

      weight: 2,

      opacity: 0.9,

    },

    Default: BASE_BARANGAY_STYLE,

  };



  var HOVER_STYLE = {

    weight: 3.5,

    opacity: 1,

    fillColor: '#000000',

    fillOpacity: 0.04,

  };



  var SELECTED_STYLE = {

    color: '#0F4C81',

    weight: 3,

    opacity: 1,

    dashArray: null,

  };



  var GEOJSON_NAME_ALIASES = {

    'jorge l. araneta': 'Don Jorge Araneta',

    'jorgel.araneta': 'Don Jorge Araneta',

    'don jorge araneta': 'Don Jorge Araneta',

    'lag-asan': 'Lag-asan',

    'lag asan': 'Lag-asan',

    'ma-ao barrio': 'Ma-ao',

    'ma-aobarrio': 'Ma-ao',

    'ma-ao': 'Ma-ao',

  };



  function canonicalBarangayName(name) {

    if (!name) return '';

    var trimmed = String(name).trim();

    var key = trimmed.toLowerCase();

    return GEOJSON_NAME_ALIASES[key] || trimmed;

  }



  function resolveBarangayName(props) {

    if (!props) return '';

    return props.name || props.psa_name || props.NAME_3 || '';

  }



  function lookupRisk(riskData, name) {

    if (!name || !riskData) return null;

    var canonical = canonicalBarangayName(name);

    if (riskData[canonical]) return riskData[canonical];

    if (riskData[name]) return riskData[name];

    var lower = canonical.toLowerCase();

    for (var key in riskData) {

      if (key.toLowerCase() === lower) return riskData[key];

    }

    return null;

  }



  function barangayStyle(feature, riskData, isSelected) {

    var rawName = resolveBarangayName(feature.properties);

    var canonical = canonicalBarangayName(rawName);

    var risk = lookupRisk(riskData, canonical) || lookupRisk(riskData, rawName);

    var level = (risk && risk.level) ? risk.level : 'Low';

    var base = RISK_STYLES[level] || RISK_STYLES.Default;

    var style = {

      fill: true,

      fillColor: base.fillColor,

      fillOpacity: base.fillOpacity,

      color: base.color,

      weight: base.weight,

      opacity: base.opacity,

    };

    if (isSelected) {

      style.color = SELECTED_STYLE.color;

      style.weight = SELECTED_STYLE.weight;

      style.opacity = SELECTED_STYLE.opacity;

      style.fillOpacity = Math.min(0.45, (base.fillOpacity || 0) + 0.12);

      style.dashArray = null;

    }

    return style;

  }



  function buildPopupHtml(name, risk) {

    var displayName = canonicalBarangayName(name) || name;

    var scoreText = risk && typeof risk.score === 'number' ? risk.score.toFixed(2) : '—';

    var levelText = (risk && risk.level) ? risk.level : 'Low';

    var levelClass = levelText.toLowerCase();

    return (

      '<div class="map-barangay-popup">' +

      '<span class="map-barangay-popup__badge map-barangay-popup__badge--' + levelClass + '">' + levelText + '</span>' +

      '<strong>Barangay: ' + displayName + '</strong>' +

      '<div class="map-barangay-popup__score">APTAS Risk Index: <strong>' + scoreText + '</strong></div>' +

      '<p class="map-barangay-popup__hint">Click to filter cases for this barangay. Composite score from anomaly, temporal, environmental, and spatial signals.</p>' +

      '</div>'

    );

  }



  function findLayerByName(layersByName, barangayName) {

    if (!barangayName || !layersByName) return null;

    var canonical = canonicalBarangayName(barangayName);

    return (

      layersByName[canonical] ||

      layersByName[barangayName] ||

      layersByName[canonical.toLowerCase()] ||

      layersByName[String(barangayName).toLowerCase()] ||

      null

    );

  }



  function findFeatureByName(geojson, barangayName) {

    if (!geojson || !geojson.features || !barangayName) return null;

    var target = canonicalBarangayName(barangayName).toLowerCase();

    for (var i = 0; i < geojson.features.length; i++) {

      var feature = geojson.features[i];

      var rawName = resolveBarangayName(feature.properties);

      var canonical = canonicalBarangayName(rawName).toLowerCase();

      if (rawName && rawName.toLowerCase() === target) return feature;

      if (canonical === target) return feature;

    }

    return null;

  }



  function flyToBarangay(map, context, barangayName, zoom) {

    var layer = null;

    if (context && context.layersByName) {

      layer = findLayerByName(context.layersByName, barangayName);

    }

    if (layer && typeof layer.getBounds === 'function') {

      map.fitBounds(layer.getBounds(), {

        maxZoom: zoom || 15,

        animate: true,

        padding: [24, 24],

      });

      return true;

    }

    return false;

  }



  /**

   * Load city + barangay GeoJSON layers and bind APTAS risk styling.

   * @returns {Promise<object>}

   */

  function load(map, options) {

    var barangayGeoUrl = options.barangayGeoUrl;

    var cityGeoUrl = options.cityGeoUrl;

    var riskUrl = options.riskUrl;

    var casePinsLayer = options.casePinsLayer;

    var onReady = options.onReady;

    var onBarangaySelect = options.onBarangaySelect;



    if (!map.getPane('barangayBoundaries')) {

      map.createPane('barangayBoundaries');

      map.getPane('barangayBoundaries').style.zIndex = 350;

    }



    var fetches = [

      fetch(riskUrl).then(function (r) { return r.json(); }),

      fetch(barangayGeoUrl).then(function (r) { return r.json(); }),

    ];

    if (cityGeoUrl) {

      fetches.push(fetch(cityGeoUrl).then(function (r) { return r.json(); }));

    }



    return Promise.all(fetches).then(function (results) {

      var riskData = results[0] || {};

      var barangayGeo = results[1];

      var cityGeo = cityGeoUrl ? results[2] : null;



      var layersByName = {};

      var selectedLayer = null;

      var selectedName = null;



      function registerLayer(rawName, layer) {

        var canonical = canonicalBarangayName(rawName);

        layersByName[rawName] = layer;

        layersByName[canonical] = layer;

        layersByName[rawName.toLowerCase()] = layer;

        layersByName[canonical.toLowerCase()] = layer;

      }



      function setLayerSelectedState(layer, isSelected) {
        if (layer && layer._path) {
          layer._path.classList.toggle('pulse-barangay-selected', !!isSelected);
        }
      }

      function applyLayerStyle(layer, feature, isSelected) {
        layer.setStyle(barangayStyle(feature, riskData, isSelected));
        setLayerSelectedState(layer, isSelected);
      }



      function selectBarangay(name, opts) {

        opts = opts || {};

        if (!name) {

          if (selectedLayer && selectedLayer.feature) {

            applyLayerStyle(selectedLayer, selectedLayer.feature, false);

          }

          selectedLayer = null;

          selectedName = null;

          return false;

        }



        var layer = findLayerByName(layersByName, name);

        if (!layer || !layer.feature) return false;



        if (selectedLayer && selectedLayer !== layer && selectedLayer.feature) {

          applyLayerStyle(selectedLayer, selectedLayer.feature, false);

        }



        selectedLayer = layer;

        selectedName = canonicalBarangayName(name);

        applyLayerStyle(layer, layer.feature, true);

        layer.bringToFront();



        if (opts.zoom !== false) {

          map.fitBounds(layer.getBounds(), {

            maxZoom: opts.maxZoom || 15,

            animate: true,

            padding: [24, 24],

          });

        }



        if (opts.openPopup !== false) {

          setTimeout(function () {

            layer.openPopup();

          }, opts.zoom === false ? 0 : 350);

        }



        if (!opts.silent && typeof onBarangaySelect === 'function') {

          onBarangaySelect(selectedName, layer);

        }



        return true;

      }



      var cityLayer = null;

      if (cityGeo) {

        cityLayer = L.geoJSON(cityGeo, {

          pane: 'barangayBoundaries',

          interactive: false,

          style: CITY_STYLE,

        }).addTo(map);

      }



      var boundaryLayer = L.geoJSON(barangayGeo, {

        pane: 'barangayBoundaries',

        style: function (feature) {

          return barangayStyle(feature, riskData, false);

        },

        onEachFeature: function (feature, layer) {

          var rawName = resolveBarangayName(feature.properties);

          var canonical = canonicalBarangayName(rawName);

          var risk = lookupRisk(riskData, canonical) || lookupRisk(riskData, rawName);



          registerLayer(rawName, layer);

          if (canonical !== rawName) {

            registerLayer(canonical, layer);

          }



          layer.bindPopup(buildPopupHtml(rawName, risk), {

            maxWidth: 280,

            className: 'map-barangay-popup-wrap',

          });



          layer.on('mouseover', function () {

            if (selectedLayer === layer) return;

            layer.setStyle(HOVER_STYLE);

            layer.bringToFront();

          });



          layer.on('mouseout', function () {

            if (selectedLayer === layer) {

              applyLayerStyle(layer, feature, true);

              return;

            }

            applyLayerStyle(layer, feature, false);

          });



          layer.on('click', function (e) {

            if (e && e.originalEvent) {

              L.DomEvent.stopPropagation(e);

            }

            selectBarangay(canonical || rawName, { silent: false });

          });

        },

      }).addTo(map);



      if (cityLayer && typeof cityLayer.getBounds === 'function') {

        map.fitBounds(cityLayer.getBounds().pad(0.05), { animate: false });

      } else if (boundaryLayer && typeof boundaryLayer.getBounds === 'function') {

        map.fitBounds(boundaryLayer.getBounds().pad(0.05), { animate: false });

      }



      if (casePinsLayer && typeof casePinsLayer.bringToFront === 'function') {

        casePinsLayer.bringToFront();

      }



      var payload = {

        boundaryLayer: boundaryLayer,

        cityLayer: cityLayer,

        riskData: riskData,

        barangayGeo: barangayGeo,

        layersByName: layersByName,

        selectBarangay: selectBarangay,

        getSelectedBarangay: function () { return selectedName; },

        refreshRiskStyles: function () {

          boundaryLayer.eachLayer(function (layer) {

            if (!layer.feature) return;

            applyLayerStyle(layer, layer.feature, selectedLayer === layer);

          });

        },

      };



      if (typeof onReady === 'function') {

        onReady(payload);

      }



      return payload;

    });

  }



  return {

    load: load,

    flyToBarangay: flyToBarangay,

    findLayerByName: findLayerByName,

    lookupRisk: lookupRisk,

    resolveBarangayName: resolveBarangayName,

    canonicalBarangayName: canonicalBarangayName,

    RISK_STYLES: RISK_STYLES,

    BASE_BARANGAY_STYLE: BASE_BARANGAY_STYLE,

    CITY_STYLE: CITY_STYLE,

  };

})();


