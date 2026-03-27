/** Zustand global chat + map state store. */

import { create } from 'zustand'
import { api, ApiError } from '../api/client'
import type {
  ChatState,
  ChoroplethFeatureCollection,
  GeographyLevel,
  MapPlan,
  Message,
  SelectedRegion,
} from '../types'

let idCounter = 0
const uid = () => `msg-${Date.now()}-${++idCounter}`

// ── Greeting fast-path (instant response, no backend call) ────────────────────
const _GREETINGS = new Set([
  'hi', 'hello', 'hoi', 'hey', 'hallo', 'dag', 'yo', 'sup', 'howdy',
  'goedemorgen', 'goedemiddag', 'goedenavond', 'good morning', 'good afternoon',
])
const _GREETING_REPLIES = [
  'Hallo! Vraag me iets over Nederlandse regionale statistieken. Probeer: "Toon bevolkingsdichtheid per gemeente" of "WOZ-waarde per buurt in Amsterdam".',
  'Hey! Ik maak interactieve kaarten van CBS-kerncijfers op gemeente-, wijk- en buurtniveau. Wat wil je weten?',
  'Hi! Ask me about Dutch regional stats — housing values, population, income, or demographics. Type a question or pick an example.',
  'Hoi! Ik laat CBS-statistieken op een kaart zien. Probeer: "Inkomen per wijk in Rotterdam" of "Vergelijk buurten in Utrecht".',
]
function _isGreeting(text: string): boolean {
  const words = text.trim().toLowerCase().replace(/[!?.,]+$/, '').split(/\s+/)
  return words.length <= 3 && words.some(w => _GREETINGS.has(w))
}
function _randomGreetingReply(): string {
  return _GREETING_REPLIES[Math.floor(Math.random() * _GREETING_REPLIES.length)]
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  currentPlan: null,
  currentGeoJSON: null,
  selectedRegion: null,
  isLoading: false,
  isLayerLoading: false,
  error: null,

  sendMessage: async (text: string) => {
    const { messages, selectedRegion } = get()

    // Build history BEFORE adding the new user message to avoid sending it twice.
    // Include plan context in assistant messages so the LLM can handle follow-ups.
    const history = messages
      .filter(m => m.role !== 'error')
      .slice(-10)
      .map(m => ({
        role: m.role as 'user' | 'assistant',
        content:
          m.role === 'assistant' && m.plan
            ? `${m.content}\n(Map context: level=${m.plan.geography_level}, scope=${m.plan.region_scope ?? 'all Netherlands'}, measure=${m.plan.measure_code}, table=${m.plan.table_id})`
            : m.content,
      }))

    // Append selected region context to the message if one is active
    const contextualText = selectedRegion
      ? `${text}\n[Selected region: ${selectedRegion.statnaam} (${selectedRegion.statcode})]`
      : text

    const userMsg: Message = {
      id: uid(),
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }

    // Fast-path: pure greeting → instant reply, no LLM call needed
    if (_isGreeting(text)) {
      const greetMsg: Message = {
        id: uid(),
        role: 'assistant',
        content: _randomGreetingReply(),
        timestamp: Date.now(),
      }
      set({ messages: [...messages, userMsg, greetMsg] })
      return
    }

    set({ messages: [...messages, userMsg], isLoading: true, error: null })

    try {
      const response = await api.chat({ message: contextualText, history })

      const assistantMsg: Message = {
        id: uid(),
        role: 'assistant',
        content: response.message,
        plan: response.plan,
        warnings: response.warnings,
        timestamp: Date.now(),
      }

      const hasFeatures = response.geojson?.features?.length > 0

      set({
        messages: [...get().messages, assistantMsg],
        currentPlan: response.plan,
        // Only update the map if the response contains actual geometry
        ...(hasFeatures
          ? { currentGeoJSON: response.geojson as ChoroplethFeatureCollection }
          : {}),
        isLoading: false,
      })
    } catch (err) {
      const detail =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
          ? err.message
          : 'An unexpected error occurred.'

      const errMsg: Message = {
        id: uid(),
        role: 'error',
        content: detail,
        timestamp: Date.now(),
      }

      set({
        messages: [...get().messages, errMsg],
        isLoading: false,
        error: detail,
      })
    }
  },

  selectRegion: (region: SelectedRegion | null) => {
    if (region) {
      const sysMsg: Message = {
        id: uid(),
        role: 'system',
        content: `📍 ${region.statnaam} (${region.statcode}) selected — your next question will be scoped to this region.`,
        timestamp: Date.now(),
      }
      set({ selectedRegion: region, messages: [...get().messages, sysMsg] })
    } else {
      set({ selectedRegion: null })
    }
  },

  switchLayer: async (level: GeographyLevel) => {
    const { currentPlan } = get()

    // Skip if already on this level
    if (currentPlan?.geography_level === level) return

    // Use isLayerLoading — keeps chat input enabled and map controls usable
    set({ isLayerLoading: true, error: null })

    try {
      const scope = level === 'gemeente' ? null : (currentPlan?.region_scope ?? null)
      const geojson = await api.boundaries(level, scope)
      const newPlan = currentPlan
        ? { ...currentPlan, geography_level: level, region_scope: scope }
        : null

      set({
        currentPlan: newPlan,
        currentGeoJSON: geojson as ChoroplethFeatureCollection,
        selectedRegion: null,
        isLayerLoading: false,
      })
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message
        : err instanceof Error ? err.message
        : 'Layer switch failed.'
      set({ isLayerLoading: false, error: detail })
    }
  },

  initBoundaries: async () => {
    // Silently load gemeente boundaries on startup so the map is immediately interactive
    try {
      const geojson = await api.boundaries('gemeente', null)
      // Only set if no chat has happened yet (don't overwrite user's map)
      if (!get().currentGeoJSON) {
        set({
          currentGeoJSON: geojson as ChoroplethFeatureCollection,
          currentPlan: {
            intent: 'map_choropleth',
            table_id: '86165NED',
            measure_code: 'AantalInwoners_5',
            geography_level: 'gemeente',
            region_scope: null,
            period: null,
            classification: 'quantile',
            n_classes: 5,
            message: '',
          } as MapPlan,
        })
      }
    } catch {
      // Silently ignore — user can still interact via chat
    }
  },

  clearError: () => set({ error: null }),

  reset: () =>
    set({
      messages: [],
      currentPlan: null,
      currentGeoJSON: null,
      selectedRegion: null,
      error: null,
    }),
}))
