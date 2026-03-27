import { useEffect, useRef, useState, useCallback } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useChatStore } from '../../store/chatStore'
import { MapLegend } from './MapLegend'
import { MapTooltip } from './MapTooltip'
import { MapControls } from './MapControls'
import type { ChoroplethFeatureProperties, ChoroplethMeta } from '../../types'

const NL_CENTER: [number, number] = [5.2913, 52.1326]
const NL_ZOOM = 7
const SOURCE_ID = 'choropleth-source'
const FILL_LAYER = 'choropleth-fill'
const OUTLINE_LAYER = 'choropleth-outline'
const SELECTED_LAYER = 'choropleth-selected'
const BASE_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

interface TooltipState {
  x: number
  y: number
  props: ChoroplethFeatureProperties
}

export function MapPanel() {
  const mapContainer = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const hoveredId    = useRef<string | number | null>(null)
  const selectedId   = useRef<string | number | null>(null)

  const [tooltip,  setTooltip]  = useState<TooltipState | null>(null)
  const [meta,     setMeta]     = useState<ChoroplethMeta | null>(null)
  const [measureCode, setMeasureCode] = useState('')
  const [mapReady, setMapReady] = useState(false)

  const currentGeoJSON  = useChatStore(s => s.currentGeoJSON)
  const currentPlan     = useChatStore(s => s.currentPlan)
  const isLoading       = useChatStore(s => s.isLoading)
  const selectedRegion  = useChatStore(s => s.selectedRegion)
  const selectRegion    = useChatStore(s => s.selectRegion)

  // ── Init map ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: BASE_STYLE,
      center: NL_CENTER,
      zoom: NL_ZOOM,
      attributionControl: true,
    })

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left')

    map.on('load', () => setMapReady(true))
    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // ── Update choropleth when GeoJSON changes ──────────────────────────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady || !currentGeoJSON) return

    // Clear any selected state when data changes
    selectedId.current = null

    const geojson  = currentGeoJSON
    const fc_meta  = geojson.meta

    // Remove old layers/source
    ;[SELECTED_LAYER, OUTLINE_LAYER, FILL_LAYER].forEach(id => {
      if (map.getLayer(id)) map.removeLayer(id)
    })
    if (map.getSource(SOURCE_ID)) map.removeSource(SOURCE_ID)

    if (!geojson.features.length) return

    // Add source with generateId so feature-state works
    map.addSource(SOURCE_ID, {
      type: 'geojson',
      data: geojson as GeoJSON.FeatureCollection,
      generateId: true,
    })

    // Boundary-only mode (no CBS data) vs choropleth mode
    const isBoundaryOnly = !fc_meta

    // Fill layer
    map.addLayer({
      id: FILL_LAYER,
      type: 'fill',
      source: SOURCE_ID,
      paint: {
        'fill-color': isBoundaryOnly
          ? ['case',
              ['boolean', ['feature-state', 'selected'], false], '#dbeafe',
              ['boolean', ['feature-state', 'hover'],    false], '#e5e7eb',
              'transparent']
          : ['coalesce', ['get', 'color'], '#cccccc'],
        'fill-opacity': isBoundaryOnly
          ? ['case',
              ['boolean', ['feature-state', 'selected'], false], 0.6,
              ['boolean', ['feature-state', 'hover'],    false], 0.4,
              0.0]
          : ['case',
              ['boolean', ['feature-state', 'selected'], false], 0.95,
              ['boolean', ['feature-state', 'hover'],    false], 0.85,
              0.72],
        'fill-opacity-transition': { duration: 200 },
      },
    })

    // Outline layer — thicker + different colour when selected
    map.addLayer({
      id: OUTLINE_LAYER,
      type: 'line',
      source: SOURCE_ID,
      paint: {
        'line-color': [
          'case',
          ['boolean', ['feature-state', 'selected'], false], '#f59e0b',
          ['boolean', ['feature-state', 'hover'],    false], '#1d4ed8',
          isBoundaryOnly ? '#6b7280' : '#ffffff',
        ],
        'line-width': [
          'case',
          ['boolean', ['feature-state', 'selected'], false], 2.5,
          ['boolean', ['feature-state', 'hover'],    false], 1.5,
          isBoundaryOnly ? 1.0 : 0.5,
        ],
        'line-opacity': 0.9,
      },
    })

    if (fc_meta) {
      setMeta(fc_meta)
      setMeasureCode(fc_meta.measure_code)
    }

    // Fly to bounds — zoom to the scoped region if set, otherwise all features
    const scopeCode = currentPlan?.region_scope?.toUpperCase() ?? null
    const targetFeatures =
      scopeCode && currentPlan?.geography_level === 'gemeente'
        ? geojson.features.filter(
            f => (f.properties as { statcode?: string })?.statcode?.toUpperCase() === scopeCode
          )
        : geojson.features

    const flyFeatures = targetFeatures.length > 0 ? targetFeatures : geojson.features
    const bounds = new maplibregl.LngLatBounds()
    let hasCoords = false
    flyFeatures.forEach(f => {
      if (!f.geometry) return
      collectCoords(f.geometry).forEach(([lng, lat]) => {
        bounds.extend([lng, lat])
        hasCoords = true
      })
    })
    if (hasCoords) {
      map.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 800 })
    }
  }, [currentGeoJSON, mapReady])

  // ── Sync external deselect (X button in MapControls) ───────────────────────
  useEffect(() => {
    if (selectedRegion === null && selectedId.current !== null) {
      const map = mapRef.current
      if (map && map.getSource(SOURCE_ID)) {
        map.setFeatureState({ source: SOURCE_ID, id: selectedId.current }, { selected: false })
      }
      selectedId.current = null
    }
  }, [selectedRegion])

  // ── Hover + click interactions ──────────────────────────────────────────────
  const setupInteractions = useCallback(() => {
    const map = mapRef.current
    if (!map) return

    // Hover
    map.on('mousemove', FILL_LAYER, e => {
      if (!e.features?.length) return
      map.getCanvas().style.cursor = 'pointer'

      const feat = e.features[0]
      const fid  = feat.id ?? null

      if (fid !== hoveredId.current) {
        if (hoveredId.current !== null)
          map.setFeatureState({ source: SOURCE_ID, id: hoveredId.current }, { hover: false })
        hoveredId.current = fid
        if (fid !== null)
          map.setFeatureState({ source: SOURCE_ID, id: fid }, { hover: true })
      }

      setTooltip({ x: e.point.x, y: e.point.y, props: feat.properties as ChoroplethFeatureProperties })
    })

    map.on('mouseleave', FILL_LAYER, () => {
      map.getCanvas().style.cursor = ''
      if (hoveredId.current !== null) {
        map.setFeatureState({ source: SOURCE_ID, id: hoveredId.current }, { hover: false })
        hoveredId.current = null
      }
      setTooltip(null)
    })

    // Click → select / deselect
    map.on('click', FILL_LAYER, e => {
      if (!e.features?.length) return
      const feat  = e.features[0]
      const fid   = feat.id ?? null
      const props = feat.properties as ChoroplethFeatureProperties & { gm_code?: string }

      if (fid === selectedId.current) {
        // Clicking the same feature deselects it
        if (fid !== null)
          map.setFeatureState({ source: SOURCE_ID, id: fid }, { selected: false })
        selectedId.current = null
        selectRegion(null)
      } else {
        // Deselect previous
        if (selectedId.current !== null)
          map.setFeatureState({ source: SOURCE_ID, id: selectedId.current }, { selected: false })
        // Select new
        selectedId.current = fid
        if (fid !== null)
          map.setFeatureState({ source: SOURCE_ID, id: fid }, { selected: true })
        selectRegion({
          statcode: props.statcode,
          statnaam: props.statnaam,
          gm_code:  props.gm_code,
        })
      }
    })

    // Click on empty map → deselect
    map.on('click', e => {
      const features = map.queryRenderedFeatures(e.point, { layers: [FILL_LAYER] })
      if (!features.length && selectedId.current !== null) {
        map.setFeatureState({ source: SOURCE_ID, id: selectedId.current }, { selected: false })
        selectedId.current = null
        selectRegion(null)
      }
    })
  }, [selectRegion])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapReady) return
    setupInteractions()
  }, [mapReady, setupInteractions])

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="relative w-full h-full bg-gray-100 dark:bg-gray-900">
      <div ref={mapContainer} className="absolute inset-0" />

      {/* Layer toggles + selected region badge */}
      <MapControls />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white/30 dark:bg-gray-900/30 backdrop-blur-[1px]
                        flex items-center justify-center z-20 pointer-events-none">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg px-5 py-3
                          flex items-center gap-3 border border-gray-200 dark:border-gray-700">
            <div className="w-4 h-4 border-2 border-brand-600 border-t-transparent
                            rounded-full animate-spin" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Loading data…
            </span>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!currentGeoJSON && !isLoading && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
          <div className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm rounded-2xl
                          px-6 py-4 text-center shadow-lg border border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Ask a question in the chat
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              The map will update with your data
            </p>
          </div>
        </div>
      )}

      {/* Legend */}
      {meta && <MapLegend meta={meta} measureCode={measureCode} />}

      {/* Tooltip — boundary mode shows only region name; choropleth mode shows value */}
      {tooltip && (
        <MapTooltip
          x={tooltip.x}
          y={tooltip.y}
          statnaam={tooltip.props.statnaam}
          value={meta ? tooltip.props.value : null}
          label={meta ? tooltip.props.label : 'Click to select'}
          measureCode={meta ? (currentPlan?.measure_code ?? '') : ''}
          period={meta?.period ?? ''}
        />
      )}

      {/* Attribution */}
      <div className="absolute bottom-1 right-2 text-[10px] text-gray-400 dark:text-gray-600
                      pointer-events-none z-10">
        CBS StatLine × PDOK
      </div>
    </div>
  )
}

// ── Utility ────────────────────────────────────────────────────────────────────

function collectCoords(geom: GeoJSON.Geometry): [number, number][] {
  const coords: [number, number][] = []
  const walk = (g: GeoJSON.Geometry) => {
    if (g.type === 'Point') coords.push(g.coordinates as [number, number])
    else if (g.type === 'LineString' || g.type === 'MultiPoint')
      (g.coordinates as [number, number][]).forEach(c => coords.push(c))
    else if (g.type === 'Polygon' || g.type === 'MultiLineString')
      (g.coordinates as [number, number][][]).flat().forEach(c => coords.push(c))
    else if (g.type === 'MultiPolygon')
      (g.coordinates as [number, number][][][]).flat(2).forEach(c => coords.push(c))
    else if (g.type === 'GeometryCollection')
      g.geometries.forEach(walk)
  }
  walk(geom)
  return coords
}
