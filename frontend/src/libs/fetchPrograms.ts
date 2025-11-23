// libs/fetchPrograms.ts

export async function fetchPrograms(facilityId: number) {
  const res = await fetch(`http://localhost:8080/programs?facility_id=${facilityId}`);
  const data = await res.json();

  console.log("Fetched programs:", data);
  return data; // 배열 형태
}
