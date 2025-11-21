// libs/fetchFacilities.ts

export async function fetchFacilities(category2?: string) {
  const url = category2
    ? `http://localhost:8080/facilities?category2=${category2}`
    : `http://localhost:8080/facilities`;

  const res = await fetch(url);
  const json = await res.json();

  console.log("Fetched data:", json);
  return json.items; // Supabase REST 형태일 때 items 사용
}
