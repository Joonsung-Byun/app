// libs/mapStorage.ts

const KEY_LAT = "map_center_lat";
const KEY_LON = "map_center_lon";

export function saveMapCenter(lat: number, lon: number) {
  localStorage.setItem(KEY_LAT, String(lat));
  localStorage.setItem(KEY_LON, String(lon));
}

export function loadMapCenter() {
  const lat = localStorage.getItem(KEY_LAT);
  const lon = localStorage.getItem(KEY_LON);

  if (!lat || !lon) return null;

  return {
    lat: parseFloat(lat),
    lon: parseFloat(lon),
  };
}
