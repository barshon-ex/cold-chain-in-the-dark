/**
 * Cold Chain in the Dark - Google Earth Engine export
 * ----------------------------------------------------
 * For every Bangladesh district and every day in the window, computes:
 *   ntl_ratio    mean of (tonight's radiance / baseline-season median) over
 *                pixels that are normally lit; ~1 = normal, <1 = darker
 *   dark_share   share of normally-lit pixels below 50% of their baseline
 *   good_frac    share of normally-lit pixels with a usable (cloud-free,
 *                high-quality) observation tonight; drop days where this is low
 *   tmax_c       ERA5-Land daily maximum 2 m temperature, deg C
 *
 * Why not the gap-filled band? VNP46A2's Gap_Filled band copies the last good
 * night into cloudy nights, which would hide outages. We use the observed
 * DNB_BRDF_Corrected_NTL and keep only Mandatory_Quality_Flag 0 or 1.
 *
 * Caveat: the VIIRS overpass is around 01:30 local time. The proxy sees
 * outages at that hour only; evening-peak load shedding is measured by the
 * BPDB zone data (scripts/02_fetch_bpdb.py), which is used to validate it.
 *
 * HOW TO RUN
 *   1. Open https://code.earthengine.google.com (free for research; you need
 *      a Google account and a Cloud project registered for Earth Engine).
 *   2. Paste this file, press Run.
 *   3. In the Tasks tab, press RUN on each export. Files land in Google Drive
 *      folder "cold_chain_in_the_dark". Download them into data/raw/gee/.
 */

// ---------------------------------------------------------------- settings
var START = '2026-03-01';   // inclusive
var END   = '2026-10-01';   // exclusive
var BASE_START = '2025-12-01';
var BASE_END   = '2026-03-01';
var LIT_NW = 2.0;            // a pixel is "normally lit" above this baseline radiance
var FOLDER = 'cold_chain_in_the_dark';

// ---------------------------------------------------------------- districts
// geoBoundaries v6 ADM2 = the 64 zila. Fallback if unavailable in your
// catalogue: ee.FeatureCollection('FAO/GAUL/2015/level2')
//   .filter(ee.Filter.eq('ADM0_NAME', 'Bangladesh')) and use 'ADM2_NAME'.
var districts = ee.FeatureCollection('WM/geoLab/geoBoundaries/600/ADM2')
  .filter(ee.Filter.eq('shapeGroup', 'BGD'))
  .map(function (f) { return f.set('district', f.get('shapeName')); })
  .select(['district']);
print('districts (expect 64):', districts.size());

// ---------------------------------------------------------------- night lights
var vnp = ee.ImageCollection('NASA/VIIRS/002/VNP46A2');

function goodRadiance(img) {
  var q = img.select('Mandatory_Quality_Flag');
  var ok = q.eq(0).or(q.eq(1));
  return ee.Image(img.select('DNB_BRDF_Corrected_NTL').updateMask(ok)
            .copyProperties(img, ['system:time_start']));
}

var baseline = vnp.filterDate(BASE_START, BASE_END).map(goodRadiance)
                  .median().rename('base');
var litMask = baseline.gt(LIT_NW);

function nightly(img) {
  var rad = goodRadiance(img);
  var ratio = rad.divide(baseline).updateMask(litMask).rename('ratio');
  var dark = ratio.lt(0.5).rename('dark');
  var good = rad.mask().reduce(ee.Reducer.min()).unmask(0)
                .updateMask(litMask).rename('good');
  return ratio.addBands(dark).addBands(good)
              .set('date', img.date().format('YYYY-MM-dd'))
              .set('system:time_start', img.get('system:time_start'));
}

// ---------------------------------------------------------------- temperature
var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR').select('temperature_2m_max');

function tmaxOn(dateStr) {
  var d = ee.Date(dateStr);
  var img = era5.filterDate(d, d.advance(1, 'day')).first();
  return ee.Image(ee.Algorithms.If(img, ee.Image(img).subtract(273.15),
                                   ee.Image.constant(-999))).rename('tmax_c');
}

// ---------------------------------------------------------------- reduce
function perNight(img) {
  var n = nightly(img);
  var t = tmaxOn(n.get('date'));
  var stack = n.addBands(t);
  var stats = stack.reduceRegions({
    collection: districts,
    reducer: ee.Reducer.mean(),
    scale: 500,
    tileScale: 4
  });
  return stats.map(function (f) {
    return f.set('date', n.get('date'))
            .set('ntl_ratio', f.get('ratio'))
            .set('dark_share', f.get('dark'))
            .set('good_frac', f.get('good'))
            .select(['date', 'district', 'ntl_ratio', 'dark_share', 'good_frac', 'tmax_c'],
                    null, false);
  });
}

// One export per month keeps each task small enough to finish.
var months = ee.List.sequence(0, ee.Date(END).difference(ee.Date(START), 'month').subtract(1));
months.evaluate(function (list) {
  list.forEach(function (i) {
    var m0 = ee.Date(START).advance(i, 'month');
    var m1 = m0.advance(1, 'month');
    var label = m0.format('YYYY_MM').getInfo();
    var table = vnp.filterDate(m0, m1).map(perNight).flatten();
    Export.table.toDrive({
      collection: table,
      description: 'ntl_tmax_district_' + label,
      folder: FOLDER,
      fileFormat: 'CSV',
      selectors: ['date', 'district', 'ntl_ratio', 'dark_share', 'good_frac', 'tmax_c']
    });
  });
});

// Baseline-season values too, for the placebo test (same columns).
var basetable = vnp.filterDate(BASE_START, BASE_END).map(perNight).flatten();
Export.table.toDrive({
  collection: basetable, description: 'ntl_tmax_district_baseline',
  folder: FOLDER, fileFormat: 'CSV',
  selectors: ['date', 'district', 'ntl_ratio', 'dark_share', 'good_frac', 'tmax_c']
});

// District shapes for the dashboard map (simplified to ~1 km).
Export.table.toDrive({
  collection: districts.map(function (f) { return f.simplify(1000); }),
  description: 'districts_geojson', folder: FOLDER, fileFormat: 'GeoJSON'
});

Map.centerObject(districts, 7);
Map.addLayer(baseline.updateMask(litMask), {min: 0, max: 40}, 'baseline radiance (lit pixels)');
Map.addLayer(districts.style({color: 'white', fillColor: '00000000', width: 1}), {}, 'districts');
