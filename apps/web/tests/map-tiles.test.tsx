import assert from "node:assert/strict";
import { test } from "node:test";
import { OSM_TILES, osmAttribution, resolveBaseMap } from "../src/lib/map-tiles";

test("auto follows the site theme; an explicit choice wins", () => {
  assert.equal(resolveBaseMap("auto", "light"), "streets");
  assert.equal(resolveBaseMap("auto", "dark"), "dark");
  assert.equal(resolveBaseMap("light", "dark"), "light");
  assert.equal(resolveBaseMap("streets", "dark"), "streets");
});

test("every style uses keyless OpenStreetMap tiles with localized credit", () => {
  assert.equal(OSM_TILES, "https://tile.openstreetmap.org/{z}/{x}/{y}.png");
  assert.ok(osmAttribution("en").includes("OpenStreetMap contributors"));
  assert.ok(osmAttribution("bn").includes("অবদানকারী"));
});
