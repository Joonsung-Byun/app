import React from "react";
import { View, StyleSheet, Dimensions } from "react-native";
import { WebView } from "react-native-webview";
import type { MapData } from "../types";

interface Props {
  data: MapData;
}

const KakaoMapView: React.FC<Props> = ({ data }) => {
  // Generate HTML for Kakao Map
  const generateMapHTML = () => {
    const markersJS = data.markers
      .map(
        (m) => `
        var marker = new kakao.maps.Marker({
          position: new kakao.maps.LatLng(${m.lat}, ${m.lng}),
          map: map
        });

        var infowindow = new kakao.maps.InfoWindow({
          content: '<div style="padding:8px 12px;font-size:14px;">${m.name}<br/><span style="color:#666;font-size:12px;">${m.desc || ""}</span></div>'
        });

        kakao.maps.event.addListener(marker, 'click', function() {
          infowindow.open(map, marker);
        });
      `
      )
      .join("\n");

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
        <style>
          * { margin: 0; padding: 0; }
          html, body { width: 100%; height: 100%; }
          #map { width: 100%; height: 100%; }
        </style>
      </head>
      <body>
        <div id="map"></div>
        <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=72f7f0c93de127ead122efdc9adda3ec&autoload=false"></script>
        <script>
          kakao.maps.load(function() {
            var container = document.getElementById('map');
            var options = {
              center: new kakao.maps.LatLng(${data.center.lat}, ${data.center.lng}),
              level: 4
            };
            var map = new kakao.maps.Map(container, options);

            ${markersJS}
          });
        </script>
      </body>
      </html>
    `;
  };

  return (
    <View style={styles.container}>
      <WebView
        source={{ html: generateMapHTML() }}
        style={styles.webview}
        scrollEnabled={false}
        javaScriptEnabled={true}
        domStorageEnabled={true}
      />
    </View>
  );
};

const { width } = Dimensions.get("window");

const styles = StyleSheet.create({
  container: {
    width: width * 0.5, // md:w-1/2
    height: 256, // h-64
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#86efac", // green-300
    marginBottom: 12,
    overflow: "hidden",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  webview: {
    flex: 1,
  },
});

export default KakaoMapView;
