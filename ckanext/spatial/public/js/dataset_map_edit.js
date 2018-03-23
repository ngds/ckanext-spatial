// Dataset map module
this.ckan.module('dataset-map-edit', function (jQuery, _) {

  return {
    options: {
      i18n: {
      },
      styles: {
        point:{
          iconUrl: '/img/marker.png',
          iconSize: [14, 25],
          iconAnchor: [7, 25]
        },
        default_:{
          color: '#B52',
          weight: 2,
          opacity: 1,
          fillColor: '#FCF6CF',
          fillOpacity: 0.4
        }
      }
    },

    initialize: function () {
      var module = this;
      this.extent = this.el.data('extent');

      // hack to make leaflet use a particular location to look for images
      L.Icon.Default.imagePath = this.options.site_url + 'js/vendor/leaflet/images';

      jQuery.proxyAll(this, /_on/);
      this.el.ready(this._onReady);

    },

    _onReady: function(){
      var module = this;
      var map, backgroundLayer, extentLayer, ckanIcon;

      if (!this.extent) {
          return false;
      }

      map = ckan.commonLeafletMap('dataset-map-container', this.options.map_config, {attributionControl: false});

      // Initialize the draw control - this is new GH
      map.addControl(new L.Control.Draw({
        position: 'topright',
        polyline: false, polygon: false,
        circle: false, marker: false,
        rectangle: {
          shapeOptions: module.options.style,
          title: 'Draw rectangle'
        }
      }));

       // handle a click
      $('.leaflet-control-draw a', module.el).on('click', function(e) {
          console.log("New Click draw button");
      });

      var ckanIcon = L.Icon.extend({options: this.options.styles.point});

      var extentLayer = L.geoJson(this.extent, {
          style: this.options.styles.default_,
          pointToLayer: function (feature, latLng) {
            return new L.Marker(latLng, {icon: new ckanIcon})
          }});
      extentLayer.addTo(map);

      if (this.extent.type == 'Point'){
        map.setView(L.latLng(this.extent.coordinates[1], this.extent.coordinates[0]), 9);
      } else {
        map.fitBounds(extentLayer.getBounds());
      }

      map.on('draw:rectangle-created', function (e) {
        if (extentLayer) {
          map.removeLayer(extentLayer);
        }
        extentLayer = e.rect;
        bounds = extentLayer.getBounds();
        var NWcoord = bounds.getNorthWest();
        var SEcoord = bounds.getSouthEast();
        console.log(NWcoord);
        $('#md-geo-north').val(NWcoord.lat);
        $('#md-geo-west').val(NWcoord.lng);
        $('#md-geo-south').val(SEcoord.lat);
        $('#md-geo-east').val(SEcoord.lng);
        map.addLayer(extentLayer);
      
      });

    }
  }
});
