<template>
  <q-page padding class="bg-grey-2">
    
    <div class="row items-center q-mb-md">
      <q-btn flat dense :icon="showSidebar ? 'visibility_off' : 'visibility'" 
             :label="showSidebar ? 'Hide Sidebar' : 'Show Sidebar'" 
             color="primary" 
             @click="showSidebar = !showSidebar" />
    
    <div class="row items-center q-gutter-sm">
        <span class="text-weight-bold text-grey-8">Target Anki Deck:</span>
        <q-input v-model="deckName" dense outlined bg-color="white" style="width: 250px" />
      </div>
    </div>
    <div class="row q-col-gutter-xl">
      
      <div v-if="showSidebar" class="col-12 col-md-3">
        <div style="position: sticky; top: 20px; max-height: 95vh; overflow-y: auto; padding-right: 8px;">
          
          <q-card flat bordered class="bg-white q-mb-md border-positive" style="border: 2px solid #21ba45;">
            <q-card-section class="bg-positive text-white row justify-between items-center q-pa-sm">
              <div class="text-h6"><q-icon name="style" /> Card Queue ({{ cardQueue.length }})</div>
              <q-btn v-if="cardQueue.length > 0" size="sm" color="white" text-color="positive" class="text-bold" label="Export All" @click="exportQueue" />
            </q-card-section>
            
            <q-list separator class="q-pa-sm">
              <div v-if="cardQueue.length === 0" class="text-caption text-grey italic q-pa-sm">
                Select examples and click "Stage Card" to preview them here.
              </div>
              
          <q-card v-for="(card, i) in cardQueue" :key="card.id" flat bordered class="q-mb-sm bg-grey-1 relative-position">
                <q-btn icon="cancel" color="negative" flat round dense size="xs" class="absolute-top-right z-top" @click="cardQueue.splice(i, 1)" />
                <q-card-section class="q-pa-sm">
                  
                  <div class="text-caption q-mt-xs" v-if="card.examples.length">
                    <span class="text-grey-7 text-bold">Front: </span>
                    <span v-html="highlightWord(card.examples[0], card.word)"></span>
                  </div>
                  <div class="text-caption q-mt-xs" v-else>
                    <span class="text-grey-7 text-bold">Front: </span>
                    <span style="color: #2ecc71; font-weight: bold;">{{ card.article ? card.article + ' ' : '' }}{{ card.word }}</span>
                  </div>
                  
                  <div class="text-caption q-mt-sm">
                    <span class="text-grey-7 text-bold">Back: </span> 
                    <span style="color: #2ecc71; font-weight: bold;">{{ card.article ? card.article + ' ' : '' }}{{ card.word }} = </span> 
                    {{ card.definition }}
                  </div>
                  
                  <div v-if="card.transEn.length || card.transSv.length" class="text-caption q-mt-xs text-blue-grey-8">
                    <span v-if="card.transEn.length">🇬🇧 {{ card.transEn.join(', ') }} &nbsp;&nbsp;</span>
                    <span v-if="card.transSv.length">🇸🇪 {{ card.transSv.join(', ') }}</span>
                  </div>
                  
                  <q-img v-if="card.imageUrl" :src="card.imageUrl" style="width: 80px; height: 60px; border-radius: 4px;" class="q-mt-sm shadow-1" />
                </q-card-section>
              </q-card>
            </q-list>
          </q-card>

          <q-card flat bordered class="bg-white q-mb-md">
            <q-card-section class="bg-blue-grey-9 text-white q-pa-sm">
              <div class="text-subtitle1 text-bold">Progress Summary</div>
            </q-card-section>
            
            <q-list separator>
              <div v-if="Object.keys(results).length === 0" class="q-pa-md text-caption text-grey italic">
                Search for words to see progress.
              </div>
              <q-item v-for="(data, w) in results" :key="'summary-'+w" dense>
                <q-item-section avatar>
                  <q-checkbox v-model="selections[w].skipped" color="grey" size="sm" />
                </q-item-section>
                <q-item-section>
                  <q-item-label :class="{'text-strike text-grey': selections[w].skipped}" class="text-bold text-capitalize">
                    {{ w }}
                  </q-item-label>
                  <q-item-label caption class="row items-center">
                    <q-icon :name="countCardsForWord(w) > 0 ? 'check_box' : 'check_box_outline_blank'" 
                            :color="countCardsForWord(w) > 0 ? 'green' : 'grey-4'" size="xs" class="q-mr-xs"/>
                    Cards: <b>{{ countCardsForWord(w) }}</b>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <q-card flat bordered class="bg-white">
            <q-card-section class="bg-primary text-white q-pa-sm">
              <div class="text-subtitle1 text-bold">Future Words</div>
            </q-card-section>
            <q-card-section>
              <div v-if="futureWords.length === 0" class="text-caption text-grey italic">
                Click '+' next to a synonym.
              </div>
              <div class="row q-gutter-xs">
                <q-chip v-for="(fw, idx) in futureWords" :key="'fw-'+idx" removable @remove="futureWords.splice(idx, 1)" color="blue-1" text-color="primary" dense>
                  {{ fw }}
                </q-chip>
              </div>
            </q-card-section>
          </q-card>

        </div>
      </div>

      <div :class="showSidebar ? 'col-12 col-md-9' : 'col-12'">
        
        <div class="row q-col-gutter-md q-mb-xl">
          <div class="col-12 col-md-6">
            <q-card flat bordered class="bg-white full-height">
              <q-card-section>
                <div class="text-h6"><q-icon name="library_books" /> 1. Upload Library (.txt)</div>
                <div class="row q-gutter-sm q-mt-sm">
                  <q-file v-model="bookFiles" label="Book texts" outlined multiple dense class="col-grow"/>
                  <q-btn icon="upload" color="black" @click="processBooks" :loading="indexing" />
                </div>
                <div v-if="libraryStats" class="text-caption text-positive q-mt-sm">
                  Indexed {{ libraryStats.unique_words }} unique words.
                </div>
              </q-card-section>
            </q-card>
          </div>

          <div class="col-12 col-md-6">
            <q-card flat bordered class="bg-white full-height">
              <q-card-section>
                <div class="text-h6"><q-icon name="search" /> 2. Search Words</div>
                <div class="row q-gutter-sm q-mt-sm">
                  <q-input v-model="rawInput" type="textarea" outlined dense rows="2" class="col-grow" label="Paste comma or newline separated words" />
                  <q-btn label="Fetch" color="primary" @click="fetchData" :loading="isLoading" />
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <div v-for="(data, word) in results" :key="word" class="q-mb-xl">
          
          <q-card flat bordered v-if="selections[word].skipped" class="bg-grey-4">
            <q-card-section class="row justify-between items-center q-pa-sm">
              <div class="text-h6 text-strike text-grey-7 q-ml-md text-capitalize">{{ word }}</div>
              <q-btn icon="undo" flat round color="primary" @click="selections[word].skipped = false" tooltip="Restore word" />
            </q-card-section>
          </q-card>

          <q-card flat bordered v-else>
            <q-card-section class="bg-blue-grey-9 text-white row items-center justify-between">
              <div class="row items-center">
                <div class="text-h4 text-capitalize text-weight-bold q-mr-md">{{ word }}</div>
                <span v-if="data.article" class="text-h6 text-grey-4 q-ml-md">{{ data.article }}</span>
              </div>
              <q-btn icon="close" flat round dense @click="selections[word].skipped = true" tooltip="Minimize / Skip this word" />
            </q-card-section>

            <q-card-section class="bg-grey-1 border-bottom">
              <div class="row q-col-gutter-lg">
                
                <div class="col-12 col-md-5 border-right">
                  <div class="row items-center q-mb-sm">
                    <span class="text-subtitle2 text-primary q-mr-sm">Translations</span>
                    <q-checkbox v-model="selections[word].includeTranslations" label="Include in Next Card" size="xs" color="primary" />
                  </div>
                  
                  <div class="q-mb-sm row items-center">
                    <span class="text-h6 q-mr-sm" style="line-height: 1;">🇬🇧</span>
                    <span v-if="!data.translations?.en?.length" class="text-caption text-grey italic">N/A</span>
                    <div class="row q-gutter-x-sm inline">
                      <q-checkbox v-for="t in data.translations?.en" :key="'en-'+t" 
                                  v-model="selections[word].selectedTranslations.en" :val="t" size="xs" dense color="blue-grey-6">
                        <span class="text-body2">{{ t }}</span>
                      </q-checkbox>
                    </div>
                  </div>

                  <div class="row items-center">
                    <span class="text-h6 q-mr-sm" style="line-height: 1;">🇸🇪</span>
                    <span v-if="!data.translations?.sv?.length" class="text-caption text-grey italic">N/A</span>
                    <div class="row q-gutter-x-sm inline">
                      <q-checkbox v-for="t in data.translations?.sv" :key="'sv-'+t" 
                                  v-model="selections[word].selectedTranslations.sv" :val="t" size="xs" dense color="blue-grey-6">
                        <span class="text-body2">{{ t }}</span>
                      </q-checkbox>
                    </div>
                  </div>
                </div>

                <div class="col-12 col-md-7">
                  <div class="row items-center q-mb-sm">
                    <span class="text-subtitle2 text-primary q-mr-sm">Synonyms</span>
                    <q-checkbox v-model="selections[word].includeSynonyms" label="Include in Next Card" size="xs" color="primary" />
                  </div>
                  <div class="row q-gutter-xs items-center">
                    <div v-if="!data.synonyms || data.synonyms.length === 0" class="text-caption text-grey italic">No synonyms found.</div>
                    
                    <q-chip v-for="syn in data.synonyms" :key="syn" color="grey-3" text-color="black" class="q-ma-xs">
                      {{ syn }}
                      <q-btn icon="add_circle" flat round dense size="xs" color="primary" class="q-ml-xs" @click="addFutureWord(syn)" tooltip="Add to Future Words" />
                    </q-chip>
                  </div>
                </div>

              </div>
            </q-card-section>

            <div class="row q-col-gutter-md q-pa-md">
              <div class="col-12 col-md-6" v-for="source in ['rob_definitions', 'wik_definitions']" :key="source">
                <div class="text-overline text-h6 q-mb-sm" :class="source === 'rob_definitions' ? 'text-green-8' : 'text-blue-8'">
                  {{ source === 'rob_definitions' ? 'Le Robert' : 'Wiktionary' }}
                </div>
                
                <div v-for="(entry, idx) in data[source]" :key="idx" class="q-mb-lg">
                  <div class="row no-wrap items-start">
                    <q-checkbox v-model="selections[word].activeDefs" :val="entry.definition" :color="source === 'rob_definitions' ? 'green' : 'blue'" class="q-mr-sm" />
                    <div>
                      <div v-if="entry.tags && entry.tags.length > 0" class="q-mb-xs">
                        <q-badge v-for="tag in entry.tags" :key="tag" outline :color="source === 'rob_definitions' ? 'green' : 'blue'" class="q-mr-xs">
                          {{ tag }}
                        </q-badge>
                      </div>
                      <span class="text-body1" :class="selections[word].activeDefs.includes(entry.definition) ? 'text-weight-bold' : ''">
                        {{ entry.definition }}
                      </span>
                    </div>
                  </div>

                  <div v-if="selections[word].activeDefs.includes(entry.definition)" class="q-ml-xl q-pa-sm bg-blue-grey-1 rounded-borders q-mt-sm s">
                    
                    <div class="q-mb-md bg-white q-pa-sm rounded-borders s">
                      <div class="text-caption text-primary text-bold q-mb-xs">Select Thumbnail</div>
                      <div class="row q-gutter-sm no-wrap scroll q-pb-sm">
                        <q-img v-for="img in data.images" :key="img" :src="img" 
                          @click="selections[word].selectedImages[entry.definition] = img"
                          :style="selections[word].selectedImages[entry.definition] === img ? 'border: 4px solid #1976D2; opacity: 1;' : 'opacity: 0.5; cursor: pointer;'"
                          style="width: 200px; height: 150px; border-radius: 8px; flex-shrink: 0;" 
                        />
                      </div>
                      <div class="row q-mt-sm items-center no-wrap">
                        <q-input v-model="selections[word].customImageUrls[entry.definition]" dense outlined placeholder="Paste custom image URL..." class="col-grow text-caption bg-grey-2" />
                        <q-btn icon="check" color="primary" dense flat @click="applyCustomImage(word, entry.definition)" tooltip="Apply Custom Image" />
                      </div>
                    </div>

                    <div class="text-caption text-primary text-bold q-mb-xs">Select Examples</div>
                    <div v-for="ex in entry.examples" :key="ex">
                      <q-checkbox v-if="ex" v-model="selections[word].selectedExamples[entry.definition]" :val="ex" size="xs">
                        <span class="text-caption italic">{{ ex }}</span>
                      </q-checkbox>
                    </div>

                    <div class="q-mt-sm border-top q-pt-sm">
                      <q-btn size="sm" outline color="primary" icon="add" label="Add more examples" 
                             @click="selections[word].exampleAdder[entry.definition].show = !selections[word].exampleAdder[entry.definition].show" />
                      
                      <div v-if="selections[word].exampleAdder[entry.definition].show" class="q-mt-sm bg-white q-pa-sm rounded-borders s">
                        <div class="row q-gutter-md q-mb-sm">
                          <q-radio v-model="selections[word].exampleAdder[entry.definition].tab" val="other" label="Other Dictionary" dense size="sm" color="secondary" />
                          <q-radio v-model="selections[word].exampleAdder[entry.definition].tab" val="book" label="From Book" dense size="sm" color="secondary" />
                          <q-radio v-model="selections[word].exampleAdder[entry.definition].tab" val="own" label="Own Example" dense size="sm" color="secondary" />
                        </div>

                        <div v-if="selections[word].exampleAdder[entry.definition].tab === 'other'">
                           <div class="text-caption text-grey italic q-mb-xs">Pulling examples from {{ source === 'rob_definitions' ? 'Wiktionary' : 'Le Robert' }}...</div>
                           <div v-for="otherDef in (source === 'rob_definitions' ? data.wik_definitions : data.rob_definitions)" :key="otherDef.definition">
                              <div v-for="oEx in otherDef.examples" :key="oEx">
                                <q-checkbox v-model="selections[word].selectedExamples[entry.definition]" :val="oEx" size="xs">
                                  <span class="text-caption text-blue-grey-8">{{ oEx }}</span>
                                </q-checkbox>
                              </div>
                           </div>
                        </div>

                        <div v-if="selections[word].exampleAdder[entry.definition].tab === 'book'">
                          <q-btn size="xs" color="primary" label="Search Book Text" @click="getBookExamples(word, 0)" class="q-mb-sm" />
                          <div v-if="bookResults[word]">
                            <div v-if="bookResults[word].list.length === 0" class="text-caption text-grey">No matches found.</div>
                            <q-checkbox v-for="bEx in bookResults[word].list" :key="bEx" 
                                        v-model="selections[word].selectedExamples[entry.definition]" :val="bEx" size="xs">
                               <span class="text-caption text-italic text-blue-grey-9">{{ bEx }}</span>
                            </q-checkbox>
                            <q-btn v-if="bookResults[word].hasMore" label="Load Next 5" flat size="sm" color="grey-7" class="full-width q-mt-xs"
                                   @click="getBookExamples(word, bookResults[word].offset + 5)" />
                          </div>
                        </div>

                        <div v-if="selections[word].exampleAdder[entry.definition].tab === 'own'" class="row items-center no-wrap q-gutter-sm">
                          <q-input v-model="selections[word].exampleAdder[entry.definition].text" type="textarea" outlined dense rows="2" class="col-grow" placeholder="Type or paste your example here..." />
                          <q-btn icon="add_circle" color="primary" @click="addOwnExample(word, entry.definition)" tooltip="Add to list" />
                        </div>
                      </div>
                    </div>

                    <div class="q-mt-md flex justify-end">
                      <q-btn color="positive" icon="auto_awesome_mosaic" label="Stage Card" @click="stageCard(word, entry.definition, data)" />
                    </div>

                  </div>
                </div>
              </div>
            </div>
          </q-card>
        </div>

      </div>
    </div>

  </q-page>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'

const showSidebar = ref(true)
const bookFiles = ref([])
const indexing = ref(false)
const libraryStats = ref(null)
const rawInput = ref('')
const isLoading = ref(false)
const results = ref({})
const selections = ref({})
const bookResults = reactive({}) 
const deckName = ref('French words') // Default deck name

// Queues and Trackers
const futureWords = ref([])
const cardQueue = ref([])

const processBooks = async () => {
  indexing.value = true
  const formData = new FormData()
  bookFiles.value.forEach(file => formData.append('files', file))
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/upload-books', formData)
    libraryStats.value = res.data
  } catch (e) { console.error(e) }
  indexing.value = false
}

const fetchData = async () => {
  const words = rawInput.value.split(/[,\n]/).map(w => w.trim()).filter(w => w)
  if (!words.length) return
  
  isLoading.value = true
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/fetch-words', { words })
    results.value = res.data
    
    for (const w in res.data) {
      if (!selections.value[w]) {
        selections.value[w] = {
          activeDefs: [],
          selectedExamples: {},
          selectedImages: {},
          customImageUrls: {},
          exampleAdder: {},
          includeSynonyms: false,
          includeTranslations: false,
          selectedTranslations: { en: [], sv: [] },
          skipped: false
        }
      }
      
      const robDefs = res.data[w].rob_definitions || []
      const wikDefs = res.data[w].wik_definitions || []
      const allDefs = [...robDefs, ...wikDefs]

      allDefs.forEach(d => {
        if (!selections.value[w].selectedExamples[d.definition]) {
          selections.value[w].selectedExamples[d.definition] = []
        }
        if (!selections.value[w].exampleAdder[d.definition]) {
          selections.value[w].exampleAdder[d.definition] = { show: false, tab: 'other', text: '' }
        }
      })
    }
  } catch (err) {
    console.error("Fetch error:", err)
  }
  isLoading.value = false
}

const countCardsForWord = (word) => {
  return cardQueue.value.filter(c => c.word === word).length
}

const addFutureWord = (word) => {
  if (!futureWords.value.includes(word)) {
    futureWords.value.push(word)
  }
}

const applyCustomImage = (word, def) => {
  const url = selections.value[word].customImageUrls[def]
  if (url && url.trim() !== '') {
    selections.value[word].selectedImages[def] = url.trim()
    if (!results.value[word].images.includes(url.trim())) {
      results.value[word].images.unshift(url.trim())
    }
  }
}

const addOwnExample = (word, def) => {
  const txt = selections.value[word].exampleAdder[def].text.trim()
  if (txt) {
    if (!selections.value[word].selectedExamples[def].includes(txt)) {
      selections.value[word].selectedExamples[def].push(txt)
    }
    selections.value[word].exampleAdder[def].text = ''
  }
}

const getBookExamples = async (word, offset) => {
  const formData = new FormData()
  formData.append('word', word)
  formData.append('offset', offset)
  const res = await axios.post('http://127.0.0.1:8000/api/book-examples', formData)
  
  if (!bookResults[word] || offset === 0) {
    bookResults[word] = { list: res.data.examples, offset: 0, hasMore: res.data.hasMore }
  } else {
    bookResults[word].list.push(...res.data.examples)
    bookResults[word].offset = offset
    bookResults[word].hasMore = res.data.hasMore
  }
}

// -------------------------------------------------------------------
// NEW: Card Generation Logic
// -------------------------------------------------------------------

// -------------------------------------------------------------------
// NEW: Card Generation Logic (Updated Highlighting & Translations)
// -------------------------------------------------------------------

const highlightWord = (text, word) => {
  if (!text || !word) return text
  
  // Create a "stem" of the word (first 5 letters, or the whole word if it's short)
  // This catches things like 'dissimuler' -> 'dissimul' matching 'dissimulerai'
  const stemLength = Math.min(word.length, 5)
  const stem = word.substring(0, stemLength)
  
  // Regex: Find any word boundary, followed by our stem, followed by any letters
  const regex = new RegExp(`\\b(${stem}[a-zàâçéèêëîïôûùüÿñæœ]*)\\b`, 'gi')
  
  return text.replace(regex, '<span style="color: #2ecc71; font-weight: bold;">$1</span>')
}

const stageCard = (word, defText, wordData) => {
  const sel = selections.value[word]
  
  const examples = sel.selectedExamples[defText] || []
  
  let transEn = []
  let transSv = []
  // Only pull translations if the user checked "Include in Next Card"
  if (sel.includeTranslations) {
    transEn = sel.selectedTranslations?.en || []
    transSv = sel.selectedTranslations?.sv || []
  }

  let syns = []
  if (sel.includeSynonyms) {
    syns = wordData.synonyms || []
  }

  const newCard = {
    id: Date.now() + Math.random(),
    word: word,
    article: wordData.article,
    definition: defText,
    examples: [...examples], 
    imageUrl: sel.selectedImages[defText] || '',
    transEn: [...transEn],
    transSv: [...transSv],
    synonyms: [...syns]
  }

  cardQueue.value.unshift(newCard) 
}

const exportQueue = async () => {
  if (cardQueue.value.length === 0) return
  
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/export-anki', { 
      cards: cardQueue.value,
      deck_name: deckName.value 
    })
    alert(`Successfully saved ${res.data.added_words.length} words to known list!`)
    
    // Clear Queue after export
    cardQueue.value = []
    
  } catch (e) {
    console.error("Export failed", e)
    alert("Export failed. Check console.")
  }
}
</script>

<style scoped>
.border-bottom { border-bottom: 1px solid #cfd8dc; }
.border-right { border-right: 1px solid #cfd8dc; }
.border-top { border-top: 1px solid #cfd8dc; }
.italic { font-style: italic; }
.s { box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
</style>