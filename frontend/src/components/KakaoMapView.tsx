import React, { useEffect, useRef } from "react";
import type { MapData } from "../types";

interface Props {
  data: MapData;
}

// Kakao 타입 선언
declare global {
  interface Window {
    kakao: any;
  }
}

const KakaoMapView: React.FC<Props> = ({ data }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 이미 스크립트가 로드되어 있는지 확인
    if (window.kakao && window.kakao.maps) {
      initMap();
      return;
    }

    // 스크립트 로드
    const script = document.createElement("script");
    script.src = import.meta.env.VITE_KAKAO_MAP_URL;
    console.log(import.meta.env.VITE_KAKAO_MAP_URL);
    script.async = true;
    
    script.onload = () => {
      // kakao.maps.load()를 통해 실제로 라이브러리를 로드
      window.kakao.maps.load(() => {
        console.log("Kakao Maps loaded successfully");
        initMap();
      });
    };

    script.onerror = (e) => {
      console.log(e)
      console.error("Failed to load Kakao Maps script");
    };

    document.head.appendChild(script);

    return () => {
      // cleanup: 스크립트 제거는 하지 않음 (재사용을 위해)
    };
  }, [data]);

  const initMap = () => {
    if (!mapContainerRef.current) return;

    try {
      const { kakao } = window;
      
      const options = {
        center: new kakao.maps.LatLng(data.center.lat, data.center.lng),
        level: 4,
      };
      
      const map = new kakao.maps.Map(mapContainerRef.current, options);

      // 마커 추가
      data.markers.forEach((m) => {
        const marker = new kakao.maps.Marker({
          position: new kakao.maps.LatLng(m.lat, m.lng),
          map,
        });

        const infowindow = new kakao.maps.InfoWindow({
          content: `<div style="padding:8px 12px;font-size:14px;">${m.name}<br/><span style="color:#666;font-size:12px;">${m.desc ?? ""}</span></div>`,
        });

        kakao.maps.event.addListener(marker, "click", () => {
          infowindow.open(map, marker);
        });
      });

      console.log("Map initialized successfully");
    } catch (error) {
      console.error("Error initializing map:", error);
    }
  };

  return (
    <div
      ref={mapContainerRef}
      className="w-full md:w-1/2 h-64 rounded-xl border border-green-300 mb-3 shadow-sm"
    />
  );
};

export default KakaoMapView;