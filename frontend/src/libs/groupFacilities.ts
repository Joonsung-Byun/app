export function groupByFacility(rows: any[]) {
  const map = new Map();

  rows.forEach((item: any) => {
    const lat = item.LAT;   // ← 대문자
    const lon = item.LON;   // ← 대문자

    const key = `${item.Name}-${lat}-${lon}`;

    if (!map.has(key)) {
      map.set(key, {
        name: item.Name,
        address: item.Address,
        lat,
        lon,
        programs: [],
      });
    }

    map.get(key).programs.push({
      note: item.Note,
      time: item.Time,
      day: item.Day,
      cost: item.Cost,
      age_min: item.age_min,
      age_max: item.age_max,
    });
  });

  return Array.from(map.values());
}
