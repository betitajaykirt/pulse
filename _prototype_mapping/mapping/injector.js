/**
 * ============================================================
 *  Bago City Barangay Boundary Injector
 * ============================================================
 *  Usage:
 *    1. Paste this entire block into your browser DevTools console, OR
 *    2. Save as `injector.js` and load via <script src="injector.js"></script>
 *
 *  What it does:
 *    - POSTs an Overpass QL query targeting all admin_level=7 relations
 *      nested inside "Bago City, Negros Occidental" (the area search).
 *    - Parses the raw OSM JSON elements array (nodes, ways, relations).
 *    - Resolves node IDs → [lng, lat] coordinates.
 *    - Assembles way IDs → ordered coordinate arrays.
 *    - Stitches outer-role ways into closed polygon rings.
 *    - Packages everything into a standard GeoJSON FeatureCollection.
 *    - console.log()s the prettified JSON for easy copy-paste.
 *
 *  Output properties per feature:
 *    { name: "Barangay Name", type: "barangay" }
 * ============================================================
 */
(async function BagoBarangayInjector() {
  'use strict';

  const OVERPASS_ENDPOINT = 'https://overpass-api.de/api/interpreter';

  // ── Overpass QL Query ──────────────────────────────────────
  // Uses area geocoding for "Bago City" (Negros Occidental).
  // Targets all child relations with admin_level=7 (barangays).
  // Requests full geometry resolution (node coords, way members, relation members).
  const query = `
    [out:json][timeout:120];

    /* Geocode "Bago City" as a search area */
    area["name"="Bago"]["admin_level"="6"]["boundary"="administrative"]
      ["official_name"="City of Bago"]->.searchArea;

    /* Fetch all barangay-level relations inside it */
    relation["admin_level"="7"]["boundary"="administrative"](area.searchArea);

    /* Recurse down to get all member ways and their nodes */
    (._;>;);

    out body;
  `;

  console.log('%c🌐 Bago Barangay Injector — Starting Overpass fetch...', 'color: #00b4ff; font-weight: bold;');

  // ── 1. Fetch from Overpass API ─────────────────────────────
  let rawElements;
  try {
    const response = await fetch(OVERPASS_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'data=' + encodeURIComponent(query)
    });

    if (!response.ok) {
      throw new Error(`Overpass API returned HTTP ${response.status}: ${response.statusText}`);
    }

    const json = await response.json();
    rawElements = json.elements;

    if (!rawElements || rawElements.length === 0) {
      throw new Error('Overpass returned zero elements. The query area or admin_level filter may be incorrect.');
    }

    console.log(`%c✅ Received ${rawElements.length} raw OSM elements.`, 'color: #34d399;');
  } catch (err) {
    console.error('%c❌ Network / Overpass Fetch Failed:', 'color: #ef4444; font-weight: bold;', err.message);
    return;
  }

  // ── 2. Index nodes, ways, and relations ────────────────────
  const nodeMap = new Map();     // id → { lat, lon }
  const wayMap  = new Map();     // id → [nodeId, nodeId, ...]
  const relations = [];          // relation elements with tags + members

  for (const el of rawElements) {
    switch (el.type) {
      case 'node':
        nodeMap.set(el.id, { lat: el.lat, lon: el.lon });
        break;
      case 'way':
        wayMap.set(el.id, el.nodes || []);
        break;
      case 'relation':
        if (el.tags && el.tags.admin_level === '7' && el.tags.boundary === 'administrative') {
          relations.push(el);
        }
        break;
    }
  }

  console.log(`%c📊 Indexed: ${nodeMap.size} nodes, ${wayMap.size} ways, ${relations.length} barangay relations.`,
    'color: #a78bfa;');

  // ── 3. Helper: Resolve a single way ID → coordinate array ─
  function resolveWay(wayId) {
    const nodeIds = wayMap.get(wayId);
    if (!nodeIds) {
      console.warn(`⚠️  Way ${wayId} not found in response — skipping.`);
      return null;
    }

    const coords = [];
    for (const nid of nodeIds) {
      const node = nodeMap.get(nid);
      if (!node) {
        console.warn(`⚠️  Node ${nid} in way ${wayId} has no coordinate data — skipping node.`);
        continue;
      }
      coords.push([node.lon, node.lat]); // GeoJSON: [lng, lat]
    }
    return coords;
  }

  // ── 4. Helper: Stitch an ordered list of ways into closed rings ─
  //    OSM relation members may be split across multiple ways
  //    that share endpoint nodes. This function chains them
  //    end-to-end into one or more closed polygon rings.
  function stitchWaysIntoRings(wayRefs) {
    // Resolve each way into its coordinate sequence
    const segments = [];
    for (const ref of wayRefs) {
      const coords = resolveWay(ref);
      if (coords && coords.length >= 2) {
        segments.push(coords);
      }
    }

    if (segments.length === 0) return [];

    const rings = [];
    const used = new Array(segments.length).fill(false);

    while (true) {
      // Find the first unused segment to start a new ring
      let startIdx = -1;
      for (let i = 0; i < segments.length; i++) {
        if (!used[i]) { startIdx = i; break; }
      }
      if (startIdx === -1) break; // all segments consumed

      used[startIdx] = true;
      const ring = [...segments[startIdx]];

      // Iteratively try to append/prepend matching segments
      let changed = true;
      while (changed) {
        changed = false;
        const ringStart = ring[0];
        const ringEnd   = ring[ring.length - 1];

        // Check if already closed
        if (ring.length >= 4 &&
            Math.abs(ringStart[0] - ringEnd[0]) < 1e-8 &&
            Math.abs(ringStart[1] - ringEnd[1]) < 1e-8) {
          break;
        }

        for (let i = 0; i < segments.length; i++) {
          if (used[i]) continue;
          const seg = segments[i];
          const segStart = seg[0];
          const segEnd   = seg[seg.length - 1];

          // Try matching segment start → ring end
          if (Math.abs(segStart[0] - ringEnd[0]) < 1e-8 &&
              Math.abs(segStart[1] - ringEnd[1]) < 1e-8) {
            ring.push(...seg.slice(1)); // skip duplicate join point
            used[i] = true;
            changed = true;
          }
          // Try matching segment end → ring end (reversed)
          else if (Math.abs(segEnd[0] - ringEnd[0]) < 1e-8 &&
                   Math.abs(segEnd[1] - ringEnd[1]) < 1e-8) {
            const reversed = [...seg].reverse();
            ring.push(...reversed.slice(1));
            used[i] = true;
            changed = true;
          }
          // Try matching segment end → ring start
          else if (Math.abs(segEnd[0] - ringStart[0]) < 1e-8 &&
                   Math.abs(segEnd[1] - ringStart[1]) < 1e-8) {
            ring.unshift(...seg.slice(0, -1));
            used[i] = true;
            changed = true;
          }
          // Try matching segment start → ring start (reversed)
          else if (Math.abs(segStart[0] - ringStart[0]) < 1e-8 &&
                   Math.abs(segStart[1] - ringStart[1]) < 1e-8) {
            const reversed = [...seg].reverse();
            ring.unshift(...reversed.slice(0, -1));
            used[i] = true;
            changed = true;
          }
        }
      }

      // Ensure ring closure
      const first = ring[0];
      const last  = ring[ring.length - 1];
      if (Math.abs(first[0] - last[0]) > 1e-8 ||
          Math.abs(first[1] - last[1]) > 1e-8) {
        console.warn(`⚠️  Ring could not be closed (${ring.length} coords). Forcing closure.`);
        ring.push([...first]);
      }

      if (ring.length >= 4) {
        rings.push(ring);
      } else {
        console.warn(`⚠️  Discarding degenerate ring with only ${ring.length} points.`);
      }
    }

    return rings;
  }

  // ── 5. Build GeoJSON features from relations ───────────────
  const features = [];
  let skipped = 0;

  for (const rel of relations) {
    const name = (rel.tags && rel.tags.name) || 'Unnamed Barangay';

    // Separate outer and inner (hole) members
    const outerWayIds = [];
    const innerWayIds = [];

    for (const member of (rel.members || [])) {
      if (member.type !== 'way') continue;
      if (member.role === 'inner') {
        innerWayIds.push(member.ref);
      } else {
        // 'outer' or '' (default role = outer for boundary relations)
        outerWayIds.push(member.ref);
      }
    }

    if (outerWayIds.length === 0) {
      console.warn(`⚠️  Relation "${name}" (${rel.id}) has no outer way members — skipping.`);
      skipped++;
      continue;
    }

    const outerRings = stitchWaysIntoRings(outerWayIds);
    const innerRings = stitchWaysIntoRings(innerWayIds);

    if (outerRings.length === 0) {
      console.warn(`⚠️  Relation "${name}" (${rel.id}) produced no valid outer rings — skipping.`);
      skipped++;
      continue;
    }

    // Determine geometry type
    let geometry;
    if (outerRings.length === 1) {
      // Single polygon (possibly with holes)
      const coordinates = [outerRings[0], ...innerRings];
      geometry = {
        type: 'Polygon',
        coordinates: coordinates
      };
    } else {
      // MultiPolygon — each outer ring is its own polygon
      // (simplified: inner rings assigned to first polygon for now)
      const polygons = outerRings.map((ring, idx) => {
        if (idx === 0) return [ring, ...innerRings];
        return [ring];
      });
      geometry = {
        type: 'MultiPolygon',
        coordinates: polygons
      };
    }

    features.push({
      type: 'Feature',
      properties: {
        name: name,
        type: 'barangay'
      },
      geometry: geometry
    });
  }

  // ── 6. Assemble FeatureCollection & output ─────────────────
  const featureCollection = {
    type: 'FeatureCollection',
    features: features
  };

  // Sort features alphabetically by barangay name for consistency
  featureCollection.features.sort((a, b) =>
    a.properties.name.localeCompare(b.properties.name)
  );

  const output = JSON.stringify(featureCollection, null, 2);

  console.log('%c' + '═'.repeat(60), 'color: #00b4ff;');
  console.log(
    `%c✅ GeoJSON FeatureCollection ready — ${features.length} barangays resolved, ${skipped} skipped.`,
    'color: #34d399; font-weight: bold; font-size: 14px;'
  );
  console.log('%c' + '═'.repeat(60), 'color: #00b4ff;');
  console.log(
    '%cCopy the output below and paste into data/barangays.geojson:',
    'color: #fbbf24; font-weight: bold;'
  );
  console.log(output);
  console.log('%c' + '═'.repeat(60), 'color: #00b4ff;');

  // Also make it available on the window object for programmatic access
  window.__bagoBarangayGeoJSON = featureCollection;
  console.log(
    '%c💡 TIP: The FeatureCollection is also stored at window.__bagoBarangayGeoJSON',
    'color: #a78bfa;'
  );

  return featureCollection;
})();
