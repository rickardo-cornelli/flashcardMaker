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
      <q-card flat bordered>
        <q-card-section class="bg-blue-grey-9 text-white row items-center justify-between">
          <div class="text-h5 text-capitalize text-weight-bold">{{ word }}</div>
          <q-badge color="orange" text-color="black" class="text-subtitle2 q-pa-sm">
            {{ data.occurrences }} occurrences
          </q-badge>
        </q-card-section>

        <q-card-section v-if="data.images.length > 0">
          <div class="row q-col-gutter-xs overflow-auto" style="max-height: 140px;">
            <div class="col-3 col-sm-2" v-for="img in data.images" :key="img">
              <q-card flat bordered @click="toggleSelection(word, 'images', img)" class="cursor-pointer"
                      :style="selections[word].images.includes(img) ? 'border: 3px solid #1976D2' : ''">
                <q-img :src="img" height="100px" fit="cover">
                  <div v-if="selections[word].images.includes(img)" class="absolute-full flex flex-center" style="background: rgba(25,118,210,0.3)">
                    <q-icon name="check_circle" color="white" size="md" />
                  </div>
                </q-img>
              </q-card>
            </div>
          </div>
        </q-card-section>

        <div class="row q-col-gutter-md q-pa-md">
          <div class="col-12 col-md-6" v-for="source in ['rob_definitions', 'wik_definitions']" :key="source">
            <div class="text-overline q-mb-sm">{{ source === 'rob_definitions' ? 'Le Robert' : 'Wiktionary' }}</div>
            
            <div v-for="(entry, idx) in data[source]" :key="idx" class="q-mb-md">
              <div class="row no-wrap items-start">
                <q-checkbox v-model="selections[word].activeDefs" :val="entry.definition" color="primary" class="q-mr-sm" />
                <div>
                  <div v-if="entry.tags && entry.tags.length > 0" class="q-mb-xs">
                    <q-badge v-for="tag in entry.tags" :key="tag" color="grey-4" text-color="grey-9" class="q-mr-xs">
                      {{ tag }}
                    </q-badge>
                  </div>
                  <span class="text-body1" :class="selections[word].activeDefs.includes(entry.definition) ? 'text-weight-bold' : ''">
                    {{ entry.definition }}
                  </span>
                </div>
              </div>

              <div v-if="selections[word].activeDefs.includes(entry.definition)" class="q-ml-xl q-pa-sm bg-blue-grey-1 rounded-borders q-mt-sm">
                
                <div v-for="ex in entry.examples" :key="ex">
                  <q-checkbox v-if="ex" v-model="selections[word].selectedExamples[entry.definition]" :val="ex" size="xs">
                    <span class="text-caption italic">{{ ex }}</span>
                  </q-checkbox>
                </div>

                <div class="q-mt-md border-top q-pt-sm">
                  <div class="row items-center justify-between">
                    <span class="text-weight-bold text-caption text-primary">BOOK CONTEXT</span>
                    <q-btn size="xs" outline color="primary" label="Search Library" icon="search" @click="getBookExamples(word, 0)" />
                  </div>

                  <div v-if="bookResults[word]">
                    <div v-if="bookResults[word].list.length === 0" class="text-caption text-grey">No matches found in safe zone.</div>
                    
                    <q-checkbox v-for="bEx in bookResults[word].list" :key="bEx" 
                                v-model="selections[word].selectedExamples[entry.definition]" :val="bEx" size="xs">
                       <span class="text-caption text-italic text-blue-grey-9">{{ bEx }}</span>
                    </q-checkbox>
                    
                    <q-btn v-if="bookResults[word].hasMore" label="Load Next 5" flat size="sm" color="grey-7" class="full-width q-mt-xs"
                           @click="getBookExamples(word, bookResults[word].offset + 5)" />
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>
      </q-card>
    </div>

    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="save_alt" color="positive" label="Save & Export" @click="exportToAnki" v-show="Object.keys(results).length > 0"/>
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
    
    // THE FIX: Initialize selection arrays so v-models don't crash
    for (const w in res.data) {
      if (!selections.value[w]) {
        selections.value[w] = {
          activeDefs: [],
          selectedExamples: {},
          selectedImages: [],
          transOnly: false
        }
      }
      
      // Initialize empty arrays for Le Robert examples
      if (res.data[w].rob_definitions) {
        res.data[w].rob_definitions.forEach(d => {
          if (!selections.value[w].selectedExamples[d.definition]) {
            selections.value[w].selectedExamples[d.definition] = []
          }
        })
      }
      
      // Initialize empty arrays for Wiktionary examples
      if (res.data[w].wik_definitions) {
        res.data[w].wik_definitions.forEach(d => {
          if (!selections.value[w].selectedExamples[d.definition]) {
            selections.value[w].selectedExamples[d.definition] = []
          }
        })
      }
    }
  } catch (err) {
    console.error("Fetch error:", err)
  }
  isLoading.value = false
}

const toggleSelection = (word, type, item) => {
  const arr = selections.value[word][type]
  const idx = arr.indexOf(item)
  if (idx > -1) arr.splice(idx, 1)
  else arr.push(item)
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
    // Send the selections back to Python to mark them as "Known"
    const res = await axios.post('http://127.0.0.1:8000/api/export-anki', { 
      selected_data: selections.value 
    })
    alert(`Successfully saved ${res.data.added_words.length} words to your known words list!`)
    
    // Clear the UI so you can search the next batch
    results.value = {}
    rawInput.value = ''
  } catch (e) {
    console.error("Export failed", e)
    alert("Export failed. Is the backend running?")
  }
}
</script>

<style scoped>
.border-top { border-top: 1px solid #cfd8dc; }
.italic { font-style: italic; }
</style>