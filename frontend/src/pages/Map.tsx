import React, { useEffect, useRef, useState } from "react";
import FacilityCard from "../components/FacilityCard";
import { fetchFacilities } from "../libs/fetchFacilities";

declare global {
  interface Window {
    kakao: any;
  }
}

export default function MapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapObjRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);

  const [selected, setSelected] = useState<any>(null);
  const [kakaoLoaded, setKakaoLoaded] = useState(false);

  // ---------- Kakao JS SDK load ----------
  useEffect(() => {
    const script = document.createElement("script");
    script.src = import.meta.env.VITE_KAKAO_MAP_URL;

    script.onload = () => {
      window.kakao.maps.load(() => setKakaoLoaded(true));
    };

    document.head.appendChild(script);
  }, []);

  // ---------- Map initialization ----------
  useEffect(() => {
    if (!kakaoLoaded || !mapRef.current) return;

    const savedLat = localStorage.getItem("map_center_lat");
    const savedLon = localStorage.getItem("map_center_lon");

    const center = savedLat && savedLon
      ? new window.kakao.maps.LatLng(parseFloat(savedLat), parseFloat(savedLon))
      : new window.kakao.maps.LatLng(37.4979, 127.0276);

    const map = new window.kakao.maps.Map(mapRef.current, {
      center,
      level: 7,
    });

    mapObjRef.current = map;
  }, [kakaoLoaded]);

  // ---------- Save map center on movement ----------
  useEffect(() => {
    if (!kakaoLoaded) return;

    const map = mapObjRef.current;
    if (!map) return;

    window.kakao.maps.event.addListener(map, "idle", () => {
      const center = map.getCenter();
      localStorage.setItem("map_center_lat", center.getLat());
      localStorage.setItem("map_center_lon", center.getLng());
    });
  }, [kakaoLoaded]);

  // ---------- Get map bounds ----------
  const getMapBounds = () => {
    const map = mapObjRef.current;
    if (!map) return null;

    const bounds = map.getBounds();
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();

    return {
      minLat: sw.getLat(),
      minLon: sw.getLng(),
      maxLat: ne.getLat(),
      maxLon: ne.getLng(),
    };
  };

  // ---------- Render markers ----------
  const renderMarkers = (items: any[]) => {
    const map = mapObjRef.current;

    // remove previous markers
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    items.forEach((f: any) => {
      const marker = new window.kakao.maps.Marker({
        position: new window.kakao.maps.LatLng(f.lat, f.lon),
        map,
      });

      markersRef.current.push(marker);

      window.kakao.maps.event.addListener(marker, "click", () => {
        setSelected(f);
      });
    });

    console.log("Markers rendered:", markersRef.current.length);
  };

  // ---------- Category button click ----------
  async function handleCategorySelect(category: string) {
    const bounds = getMapBounds();
    const items = await fetchFacilities(category, bounds);
    renderMarkers(items);
  }

  return (
    <div className="relative w-full h-screen flex items-center justify-center">
      <div className="relative w-4/5 h-4/5 border rounded-xl shadow-xl overflow-hidden">

        {/* Category buttons */}
        <div className="absolute top-4 left-4 bg-white p-3 shadow-lg rounded-lg z-50 flex gap-2">
          <button
            className="px-3 py-1 bg-blue-500 text-white rounded hover:cursor-pointer"
            onClick={() => handleCategorySelect("생활체육관")}
          >
            생활체육관
          </button>

          <button
            className="px-3 py-1 bg-green-500 text-white rounded hover:cursor-pointer"
            onClick={() => handleCategorySelect("전시/기념관")}
          >
            전시
          </button>

          <button
            className="px-3 py-1 bg-purple-500 text-white rounded hover:cursor-pointer"
            onClick={() => handleCategorySelect("관광지")}
          >
            관광지
          </button>
        </div>

        {/* MAP */}
        <div ref={mapRef} className="w-full h-full" />
      </div>

      {selected && (
        <FacilityCard
          facility={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
