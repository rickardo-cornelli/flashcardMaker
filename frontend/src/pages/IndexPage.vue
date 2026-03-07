<template>
  <q-page padding class="bg-grey-2">
    
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
          <div class="text-h6 text-strike text-grey-7 q-ml-md">{{ word }}</div>
          <q-btn icon="undo" flat round color="primary" @click="selections[word].skipped = false" tooltip="Restore word" />
        </q-card-section>
      </q-card>

      <q-card flat bordered v-else>
        <q-card-section class="bg-blue-grey-9 text-white row items-center justify-between">
          <div class="row items-center">
            <div class="text-h4 text-capitalize text-weight-bold q-mr-md">{{ word }}</div>
            <q-badge color="orange" text-color="black" class="text-subtitle2 q-pa-sm">
              {{ data.occurrences }} occurrences
            </q-badge>
            <span v-if="data.article" class="text-h6 text-grey-4 q-ml-md">{{ data.article }}</span>
          </div>
          <q-btn icon="close" flat round dense @click="selections[word].skipped = true" tooltip="Skip this word" />
        </q-card-section>

        <q-card-section class="bg-grey-1 border-bottom">
          <div class="row q-col-gutter-lg">
            
            <div class="col-12 col-md-6 border-right">
              <div class="row items-center q-mb-sm">
                <span class="text-subtitle2 text-primary q-mr-sm">Translations</span>
                <q-checkbox v-model="selections[word].includeTranslations" label="Include in Anki" size="xs" color="primary" />
              </div>
              <div class="text-body2"><b>EN:</b> {{ data.translations?.en || 'N/A' }}</div>
              <div class="text-body2 q-mt-xs"><b>SV:</b> {{ data.translations?.sv || 'N/A' }}</div>
            </div>

            <div class="col-12 col-md-6">
              <div class="row items-center q-mb-sm">
                <span class="text-subtitle2 text-primary q-mr-sm">Synonyms</span>
                <q-checkbox v-model="selections[word].includeSynonyms" label="Include in Anki" size="xs" color="primary" />
              </div>
              <div class="row q-gutter-xs">
                <div v-if="!data.synonyms || data.synonyms.length === 0" class="text-caption text-grey italic">No synonyms found.</div>
                <q-badge v-for="syn in data.synonyms" :key="syn" color="grey-3" text-color="black" class="text-body2 q-px-sm q-py-xs">
                  {{ syn }}
                </q-badge>
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

              <div v-if="selections[word].activeDefs.includes(entry.definition)" class="q-ml-xl q-pa-sm bg-blue-grey-1 rounded-borders q-mt-sm">
                
                <div class="q-mb-md bg-white q-pa-sm rounded-borders s">
                  <div class="text-caption text-primary text-bold q-mb-xs">Select Thumbnail for this specific Card</div>
                  <div class="row q-gutter-sm no-wrap scroll q-pb-xs">
                    <q-img v-for="img in data.images" :key="img" :src="img" 
                      @click="selections[word].selectedImages[entry.definition] = img"
                      :style="selections[word].selectedImages[entry.definition] === img ? 'border: 3px solid #1976D2; opacity: 1; transform: scale(1.05)' : 'opacity: 0.5; cursor: pointer;'"
                      style="width: 80px; height: 60px; border-radius: 6px;" 
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

              </div>
            </div>
          </div>
        </div>
      </q-card>
    </div>

    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="save_alt" color="positive" label="Save & Export to Anki" @click="exportToAnki" v-show="Object.keys(results).length > 0"/>
    </q-page-sticky>

  </q-page>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'

const bookFiles = ref([])
const indexing = ref(false)
const libraryStats = ref(null)

const rawInput = ref('')
const isLoading = ref(false)
const results = ref({})
const selections = ref({})
const bookResults = reactive({}) 

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
    
    // Complex initialization for all the new features
    for (const w in res.data) {
      if (!selections.value[w]) {
        selections.value[w] = {
          activeDefs: [],
          selectedExamples: {},
          selectedImages: {}, // Maps definition -> Image URL
          customImageUrls: {}, // Maps definition -> text input
          exampleAdder: {}, // Maps definition -> state of the (+) menu
          includeSynonyms: false,
          includeTranslations: false,
          skipped: false
        }
      }
      
      const robDefs = res.data[w].rob_definitions || []
      const wikDefs = res.data[w].wik_definitions || []
      const allDefs = [...robDefs, ...wikDefs]

      allDefs.forEach(d => {
        // Initialize example array
        if (!selections.value[w].selectedExamples[d.definition]) {
          selections.value[w].selectedExamples[d.definition] = []
        }
        // Initialize (+) Adder state
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

const applyCustomImage = (word, def) => {
  const url = selections.value[word].customImageUrls[def]
  if (url && url.trim() !== '') {
    selections.value[word].selectedImages[def] = url.trim()
    // Optionally push to global images list so it appears in the gallery
    if (!results.value[word].images.includes(url.trim())) {
      results.value[word].images.unshift(url.trim())
    }
  }
}

const addOwnExample = (word, def) => {
  const txt = selections.value[word].exampleAdder[def].text.trim()
  if (txt) {
    // Add it to the selected examples array directly
    if (!selections.value[word].selectedExamples[def].includes(txt)) {
      selections.value[word].selectedExamples[def].push(txt)
    }
    // Clear input
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

const exportToAnki = async () => {
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/export-anki', { 
      selected_data: selections.value 
    })
    alert(`Successfully saved ${res.data.added_words.length} words!`)
    
    // Clear the UI
    results.value = {}
    rawInput.value = ''
  } catch (e) {
    console.error("Export failed", e)
    alert("Export failed. Is the backend running?")
  }
}
</script>

<style scoped>
.border-bottom { border-bottom: 1px solid #cfd8dc; }
.border-right { border-right: 1px solid #cfd8dc; }
.border-top { border-top: 1px solid #cfd8dc; }
.border-all { border: 1px solid #cfd8dc; }
.italic { font-style: italic; }
.s { box-shadow: 0 1px 3px rgba(0,0,0,0.12); }
</style>