export async function fetchFacilities(category2?: string, bounds?: any) {
  if (!bounds) return [];

  const { minLat, maxLat, minLon, maxLon } = bounds;

  let url = `http://localhost:8080/facilities?minLat=${minLat}&maxLat=${maxLat}&minLon=${minLon}&maxLon=${maxLon}`;

  if (category2) {
    url += `&category2=${encodeURIComponent(category2)}`;
  }

  console.log("Fetching:", url);

  const res = await fetch(url);
  const json = await res.json();

  return json; // FastAPI returns array directly
}
