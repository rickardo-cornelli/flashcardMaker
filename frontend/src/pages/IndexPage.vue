<template>
  <q-page padding class="bg-grey-2">
    
    <div class="row items-center justify-between q-mb-md">
      <div class="row q-gutter-md items-center">
        <q-btn flat dense :icon="showSidebar ? 'visibility_off' : 'visibility'" 
               :label="showSidebar ? 'Hide Sidebar' : 'Show Sidebar'" 
               color="primary" 
               @click="showSidebar = !showSidebar" />
        <q-btn outline color="positive" icon="auto_awesome_mosaic" label="Stage Selected Cards (Cmd+Enter)" @click="stageSelectedCards" />
      </div>
             
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
            
            <q-list separator class="q-pa-sm bg-grey-3">
              <div v-if="cardQueue.length === 0" class="text-caption text-grey italic q-pa-sm">
                Select definitions and press Cmd+Enter to stage cards here.
              </div>
              
              <q-card v-for="(card, i) in cardQueue" :key="card.id" flat bordered class="q-mb-md bg-white relative-position">
                <q-btn icon="cancel" color="negative" flat round dense size="xs" class="absolute-top-right z-top" @click="cardQueue.splice(i, 1)" />
                <q-card-section class="q-pa-sm q-gutter-y-xs">
                  <div class="text-bold text-primary text-subtitle2">{{ card.article ? card.article + ' ' : '' }}{{ card.word }}</div>
                  
           <div class="text-caption text-bold text-grey-8 q-mt-xs">Front (Example)</div>
                  <q-editor v-model="card.example" min-height="3rem"
                    :toolbar="[['bold', 'italic', 'green', 'removeFormat']]"
                    :definitions="{
                      green: {
                        tip: 'Toggle Green Highlight', 
                        icon: 'palette', 
                        label: 'Green',
                        handler: applyGreenHighlight
                      }
                    }" 
                  />
                  
                  <div class="text-caption text-bold text-grey-8 q-mt-sm">Back (Definition)</div>
                  <q-editor v-model="card.definition" min-height="3rem" class="q-mb-sm"
                    :toolbar="[['bold', 'italic', 'green', 'removeFormat']]"
                    :definitions="{
                      green: {
                        tip: 'Toggle Green Highlight', 
                        icon: 'palette', 
                        label: 'Green',
                        handler: applyGreenHighlight
                      }
                    }" 
                  />
                  
                  <div class="row q-gutter-x-sm">
                    <q-input v-model="card.transEn" label="🇬🇧 EN" dense outlined class="col text-caption" />
                    <q-input v-model="card.transSv" label="🇸🇪 SV" dense outlined class="col text-caption" />
                  </div>
                  
                  <q-input v-model="card.synonyms" label="Synonyms" dense outlined class="text-caption" />
                  
                  <q-img v-if="card.imageUrl" :src="card.imageUrl" style="width: 100%; max-height: 100px; border-radius: 4px;" class="q-mt-sm shadow-1" fit="contain" />
                </q-card-section>
              </q-card>
            </q-list>
          </q-card>

          <q-card flat bordered class="bg-white q-mb-md">
            <q-card-section class="bg-blue-grey-9 text-white q-pa-sm">
              <div class="text-subtitle1 text-bold">Progress Summary</div>
            </q-card-section>
            <q-list separator>
              <div v-if="Object.keys(results).length === 0" class="q-pa-md text-caption text-grey italic">Search for words to see progress.</div>
              <q-item v-for="(data, w) in results" :key="'summary-'+w" dense>
                <q-item-section avatar>
                  <q-checkbox v-model="selections[w].skipped" color="grey" size="sm" @update:model-value="(val) => { if(val) markWordProcessed(w) }" />
                </q-item-section>
                <q-item-section>
                  <q-item-label :class="{'text-strike text-grey': selections[w].skipped}" class="text-bold text-capitalize">{{ w }}</q-item-label>
                  <q-item-label caption class="row items-center">
                    <q-icon :name="countCardsForWord(w) > 0 ? 'check_box' : 'check_box_outline_blank'" :color="countCardsForWord(w) > 0 ? 'green' : 'grey-4'" size="xs" class="q-mr-xs"/>
                    Cards: <b>{{ countCardsForWord(w) }}</b>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
          <div class="col-12 q-mt-md">
            <q-card flat bordered class="bg-white">
              <q-card-section>
                <div class="text-h6"><q-icon name="library_add" color="primary" /> 3. Aggregate "To Learn" Lists</div>
                <div class="text-caption text-grey-7 q-mb-md">
                  Select multiple text files using your file browser. They will be merged, duplicates removed, and saved to the server.
                </div>
                <div class="row q-gutter-sm items-center">
                  <q-file 
                    v-model="listsToAggregate" 
                    label="Select lists to merge (.txt)" 
                    outlined 
                    dense 
                    multiple 
                    class="col-grow"
                    accept=".txt"
                  >
                    <template v-slot:prepend>
                      <q-icon name="attach_file" />
                    </template>
                  </q-file>
                  <q-btn label="Merge Lists" color="secondary" @click="runAggregation" :loading="isAggregating" icon="merge_type" />
                </div>
              </q-card-section>
            </q-card>
          </div>
          <q-card flat bordered class="bg-white">
            <q-card-section class="bg-primary text-white q-pa-sm">
              <div class="text-subtitle1 text-bold">Future Words</div>
            </q-card-section>
            <q-card-section>
              <div class="row q-gutter-xs">
                <q-chip v-for="(fw, idx) in futureWords" :key="'fw-'+idx" removable @remove="futureWords.splice(idx, 1)" color="blue-1" text-color="primary" dense>{{ fw }}</q-chip>
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
                <div v-if="libraryStats" class="text-caption text-positive q-mt-sm">Indexed {{ libraryStats.unique_words }} unique words.</div>
              </q-card-section>
            </q-card>
          </div>

        <div class="col-12 col-md-6">
            <q-card flat bordered class="bg-white full-height">
              <q-card-section>
                <div class="text-h6"><q-icon name="search" /> 2. Process Word List</div>
                
                <div class="row q-gutter-sm q-mt-sm items-center">
                  <q-file 
                    v-model="wordListFile" 
                    label="Load pipeline list (.txt)" 
                    outlined 
                    dense 
                    class="col-grow"
                    accept=".txt"
                    @update:model-value="loadWordsForBatching"
                  >
                    <template v-slot:prepend><q-icon name="checklist" /></template>
                    <template v-slot:append v-if="wordListFile">
                      <q-icon name="close" @click.stop="clearWordList" class="cursor-pointer" />
                    </template>
                  </q-file>
                  
                  <div v-if="fullWordList.length > 0" class="row no-wrap items-center q-gutter-sm q-ml-sm">
                    <q-input 
                      v-model.number="batchSize" 
                      type="number" 
                      dense 
                      outlined 
                      class="bg-white"
                      style="width: 70px;" 
                      min="1"
                      tooltip="How many words to fetch at once"
                    />
                    <q-btn 
                      color="secondary" 
                      @click="fetchNextBatch" 
                      :loading="isLoading" 
                      icon="skip_next" 
                      :label="`Fetch Next ${batchSize}`"
                    />
                  </div>
                </div>

               <div v-if="fullWordList.length > 0" class="row items-center q-mt-sm q-mb-md bg-blue-grey-1 q-pa-sm rounded-borders">
                  <div class="text-caption text-bold text-primary q-mr-sm">List Progress:</div>
                  <q-linear-progress 
                    :value="completedWords.length / fullWordList.length" 
                    color="secondary" 
                    class="col-grow" 
                    size="10px" 
                    rounded 
                  />
                  
                  <div class="text-caption text-bold text-primary q-ml-sm q-mr-md">
                    {{ completedWords.length }} / {{ fullWordList.length }} words completed
                  </div>

                  <div class="row items-center no-wrap q-gutter-xs">
                    <q-input 
                      v-model.number="skipCount" 
                      type="number" 
                      dense 
                      outlined 
                      class="bg-white"
                      style="width: 70px;" 
                      placeholder="e.g. 20"
                      min="1"
                    />
                    <q-btn 
                      size="sm" 
                      color="warning" 
                      icon="fast_forward" 
                      @click="skipFirstNWords" 
                      tooltip="Mark the first X words as completed"
                    />
                  </div>
                </div>

                <q-separator v-if="fullWordList.length > 0" class="q-my-sm" />

                <div class="text-caption text-grey-6 q-mt-sm">Current batch (or manual input):</div>
                <div class="row q-gutter-sm q-mt-xs">
                  <q-input v-model="rawInput" type="textarea" outlined dense rows="2" class="col-grow" placeholder="Paste manual words here..." />
                  <q-btn label="Fetch Box" color="primary" @click="fetchData" :loading="isLoading" />
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
        <q-card class="q-mt-md" bordered flat>
  <q-card-section>
    <div class="text-h6 text-warning">
      <q-icon name="restore" /> Restore Processed Words
    </div>
    <div class="text-caption text-grey-7">
      Paste words here (separated by commas or new lines) to "unmark" them. This removes them from your completed memory so they will appear in your next batch again.
    </div>
  </q-card-section>

        <q-card-section>
          <q-input
            v-model="wordsToRestore"
            type="textarea"
            outlined
            dense
            placeholder="e.g. chien, chat, oiseau"
            rows="3"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            color="warning"
            icon="settings_backup_restore"
            label="Unmark Words"
            @click="unmarkProcessedWords"
            :disable="wordsToRestore.trim().length === 0"
          />
        </q-card-actions>
      </q-card>

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
                <template v-if="renaming[word] !== undefined">
                  <q-input v-model="renaming[word]" dense outlined class="q-mr-sm text-h5" bg-color="white" @keyup.enter="renameAndFetch(word)" autofocus />
                  <q-btn icon="search" color="primary" dense round @click="renameAndFetch(word)" tooltip="Fetch new word" />
                  <q-btn icon="close" color="negative" flat dense round @click="delete renaming[word]" class="q-ml-sm" />
                </template>
                
                <template v-else>
                  <div class="text-h4 text-capitalize text-weight-bold q-mr-md cursor-pointer" @click="renaming[word] = word">
                    {{ word }} <q-icon name="edit" size="sm" color="grey-5" />
                  </div>
                  <span v-if="data.article" class="text-h6 text-grey-4 q-ml-md">{{ data.article }}</span>
                </template>
              </div>
             <q-btn icon="close" flat round dense @click="selections[word].skipped = true; markWordProcessed(word)" tooltip="Minimize / Skip this word" />
            </q-card-section>

            <q-card-section class="bg-grey-1 border-bottom">
              <div class="row q-col-gutter-lg">
                <div class="col-12 col-md-5 border-right">
                  <div class="row items-center q-mb-sm">
                    <span class="text-subtitle2 text-primary q-mr-sm">Translations</span>
                  </div>
                  <div class="q-mb-sm row items-center">
                    <span class="text-h6 q-mr-sm" style="line-height: 1;">🇬🇧</span>
                    <span v-if="!data.translations?.en?.length" class="text-caption text-grey italic">N/A</span>
                    <div class="row q-gutter-x-sm inline">
                      <q-checkbox v-for="t in data.translations?.en" :key="'en-'+t" v-model="selections[word].selectedTranslations.en" :val="t" size="xs" dense color="blue-grey-6"><span class="text-body2">{{ t }}</span></q-checkbox>
                    </div>
                  </div>
                  <div class="row items-center">
                    <span class="text-h6 q-mr-sm" style="line-height: 1;">🇸🇪</span>
                    <span v-if="!data.translations?.sv?.length" class="text-caption text-grey italic">N/A</span>
                    <div class="row q-gutter-x-sm inline">
                      <q-checkbox v-for="t in data.translations?.sv" :key="'sv-'+t" v-model="selections[word].selectedTranslations.sv" :val="t" size="xs" dense color="blue-grey-6"><span class="text-body2">{{ t }}</span></q-checkbox>
                    </div>
                  </div>
                </div>

                <div class="col-12 col-md-7">
                  <div class="row items-center q-mb-sm">
                    <span class="text-subtitle2 text-primary q-mr-sm">Synonyms</span>
                  </div>
                  <div class="row q-gutter-x-md items-center inline">
                    <div v-if="!data.synonyms || data.synonyms.length === 0" class="text-caption text-grey italic">No synonyms found.</div>
                    <div v-for="syn in data.synonyms" :key="syn" class="row items-center no-wrap">
                      <q-checkbox v-model="selections[word].selectedSynonyms" :val="syn" size="xs" dense color="blue-grey-6"><span class="text-body2">{{ syn }}</span></q-checkbox>
                      <q-btn icon="add_circle" flat round dense size="xs" color="primary" class="q-ml-xs" @click="addFutureWord(syn)" tooltip="Add to Future Words" />
                    </div>
                  </div>
                </div>
              </div>
            </q-card-section>

            <div class="row q-col-gutter-md q-pa-md">
              <div class="col-12 col-md-6" v-for="source in ['rob_definitions', 'wik_definitions']" :key="source">
                <div class="text-overline text-h6 q-mb-sm" :class="source === 'rob_definitions' ? 'text-green-8' : 'text-blue-8'">
                  {{ source === 'rob_definitions' ? 'Le Robert' : 'Wiktionary' }}
                </div>
                
                <div v-for="(entry, idx) in data[source]" :key="idx" class="q-mb-xl">
                  <div class="row no-wrap items-start">
                    <q-checkbox v-model="selections[word].activeDefs" :val="entry.definition" :color="source === 'rob_definitions' ? 'green' : 'blue'" class="q-mr-sm" />
                    <div>
                      <div v-if="entry.tags && entry.tags.length > 0" class="q-mb-xs">
                        <q-badge v-for="tag in entry.tags" :key="tag" outline :color="source === 'rob_definitions' ? 'green' : 'blue'" class="q-mr-xs">{{ tag }}</q-badge>
                      </div>
                      <span class="text-body1" :class="selections[word].activeDefs.includes(entry.definition) ? 'text-weight-bold' : ''">{{ entry.definition }}</span>
                    </div>
                  </div>

                  <div v-if="selections[word].activeDefs.includes(entry.definition)" class="q-ml-xl q-pa-sm bg-blue-grey-1 rounded-borders q-mt-sm s">
                    
                    <div class="q-mb-md bg-white q-pa-sm rounded-borders s">
                      <div class="text-caption text-primary text-bold q-mb-xs">Select Thumbnail</div>
                      <div class="row q-gutter-sm no-wrap scroll q-pb-sm">
                        <q-img v-for="img in data.images" :key="img" :src="img" @click="selections[word].selectedImages[entry.definition] = img"
                          :style="selections[word].selectedImages[entry.definition] === img ? 'border: 4px solid #1976D2; opacity: 1;' : 'opacity: 0.5; cursor: pointer;'"
                          style="width: 200px; height: 150px; border-radius: 8px; flex-shrink: 0;" />
                      </div>
                      <div class="row q-mt-sm items-center no-wrap">
                        <q-input v-model="selections[word].customImageUrls[entry.definition]" dense outlined placeholder="Paste custom image URL..." class="col-grow text-caption bg-grey-2" />
                        <q-btn icon="check" color="primary" dense flat @click="applyCustomImage(word, entry.definition)" />
                      </div>
                    </div>

                    <div class="text-caption text-primary text-bold q-mb-xs">Select Examples</div>
                    <div v-for="ex in entry.examples" :key="ex">
                      <q-checkbox v-if="ex" v-model="selections[word].selectedExamples[entry.definition]" :val="ex" size="xs">
                        <span class="text-caption italic">{{ ex }}</span>
                      </q-checkbox>
                    </div>

                    <div class="q-mt-sm border-top q-pt-sm">
                      <q-btn size="sm" outline color="primary" icon="add" label="Add more examples" @click="selections[word].exampleAdder[entry.definition].show = !selections[word].exampleAdder[entry.definition].show" />
                      
                      <div v-if="selections[word].exampleAdder[entry.definition].show" class="q-mt-sm bg-white q-pa-sm rounded-borders s">
                        <div class="row q-gutter-md q-mb-md">
                          <q-radio v-model="selections[word].exampleAdder[entry.definition].tab" val="other" :label="source === 'rob_definitions' ? 'Wiktionary' : 'Le Robert'" dense size="sm" color="secondary" />
                          <q-radio v-model="selections[word].exampleAdder[entry.definition].tab" val="book" label="From Book" dense size="sm" color="secondary" />
                          <q-radio v-model="selections[word].exampleAdder[entry.definition].tab" val="own" label="Own Example" dense size="sm" color="secondary" />
                        </div>

                        <div v-if="selections[word].exampleAdder[entry.definition].tab === 'other'">
                           <div v-for="(otherDef, oIdx) in (source === 'rob_definitions' ? data.wik_definitions : data.rob_definitions)" :key="otherDef.definition" class="q-mb-md">
                              <div class="text-caption text-bold text-blue-grey-10">#{{ oIdx + 1 }} {{ otherDef.definition }}</div>
                              <div v-for="oEx in otherDef.examples" :key="oEx" class="q-pl-md q-mt-xs">
                                <q-checkbox v-model="selections[word].selectedExamples[entry.definition]" :val="oEx" size="xs"><span class="text-caption text-blue-grey-8">{{ oEx }}</span></q-checkbox>
                              </div>
                           </div>
                        </div>

                        <div v-if="selections[word].exampleAdder[entry.definition].tab === 'book'">
                          <q-btn size="xs" color="primary" label="Search Book Text" @click="getBookExamples(word, 0)" class="q-mb-sm" />
                          <div v-if="bookResults[word]">
                            <div v-if="bookResults[word].list.length === 0" class="text-caption text-grey">No matches found.</div>
                            <q-checkbox v-for="bEx in bookResults[word].list" :key="bEx" v-model="selections[word].selectedExamples[entry.definition]" :val="bEx" size="xs">
                               <span class="text-caption text-italic text-blue-grey-9">{{ bEx }}</span>
                            </q-checkbox>
                            <q-btn v-if="bookResults[word].hasMore" label="Load Next 5" flat size="sm" color="grey-7" class="full-width q-mt-xs" @click="getBookExamples(word, bookResults[word].offset + 5)" />
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

      </div>
    </div>

  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
// Add the variable to track the input box
const skipCount = ref(null)

// --- NEW: Fast-Forward Function ---
const skipFirstNWords = () => {
  if (skipCount.value > 0 && fullWordList.value.length > 0) {
    // Slice the first N words from the master list
    const wordsToSkip = fullWordList.value.slice(0, skipCount.value).map(w => w.toLowerCase());
    
    // Add them to the completed array if they aren't there already
    wordsToSkip.forEach(w => {
      if (!completedWords.value.includes(w)) {
        completedWords.value.push(w);
      }
    });
    
    // Save the newly populated array to your hard drive
    if (wordListFile.value && wordListFile.value.name) {
      localStorage.setItem(`flashcard_completed_${wordListFile.value.name}`, JSON.stringify(completedWords.value));
    }
    
    // Clear the input box
    skipCount.value = null;
  }
}
const renaming = ref({}) // Tracks which words are currently being edited
const listsToAggregate = ref([])
const isAggregating = ref(false)

const showSidebar = ref(true)
const deckName = ref('French words')
const bookFiles = ref([])
const indexing = ref(false)
const libraryStats = ref(null)
const rawInput = ref('')
const isLoading = ref(false)
const results = ref({})
const selections = ref({})
const bookResults = reactive({}) 
const wordListFile = ref(null)
const fullWordList = ref([])
const completedWords = ref([])
const batchSize = ref(10)

const futureWords = ref([])
const cardQueue = ref([])

// --- COMMAND+ENTER GLOBAL SHORTCUT ---
const handleKeydown = (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault()
    stageSelectedCards()
  }
}
onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
// Add this near your other refs
const wordsToRestore = ref('')

const unmarkProcessedWords = () => {
  // 1. Clean the pasted words
  const wordsToProcess = wordsToRestore.value
    .split(/[,\n]/)
    .map(w => w.trim().toLowerCase())
    .filter(w => w)

  if (wordsToProcess.length === 0) return

  const initialCount = completedWords.value.length

  // 2. Rescue the words by filtering them out of the completed array
  completedWords.value = completedWords.value.filter(
    completedWord => {
      const cleanMemoryWord = completedWord.trim().toLowerCase()
      return !wordsToProcess.includes(cleanMemoryWord)
    }
  )

  const newCount = completedWords.value.length
  const restoredCount = initialCount - newCount

  // 3. 🚨 THE CRITICAL FIX: Overwrite localStorage with the clean array! 🚨
  if (wordListFile.value && wordListFile.value.name) {
    localStorage.setItem(
      `flashcard_completed_${wordListFile.value.name}`, 
      JSON.stringify(completedWords.value)
    )
  }

  // 4. Clean up the UI
  wordsToRestore.value = ''
  
  if (restoredCount > 0) {
    alert(`✅ Successfully rescued ${restoredCount} words from Local Storage!`)
  } else {
    alert(`⚠️ None found! Double-check the spelling of the words you pasted.`)
  }
}
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
          selectedSynonyms: [],
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
  // Add this at the end of your fetchData function!
  // (If your variable is named something other than wordData, use that instead)
  return Object.keys(results.value);
}

// 1. Load the file and grab the array of completed words from memory
const loadWordsForBatching = (file) => {
  if (!file) {
    clearWordList()
    return
  }
  
  const reader = new FileReader()
  reader.onload = (e) => {
    const words = e.target.result.split(/[,\n]/).map(w => w.trim()).filter(w => w)
    fullWordList.value = words
    
    // Check memory for the array of completed words for THIS file
    const saved = localStorage.getItem(`flashcard_completed_${file.name}`)
    if (saved) {
      completedWords.value = JSON.parse(saved)
    } else {
      completedWords.value = []
    }
    
    rawInput.value = ''
  }
  reader.readAsText(file)
}

// 2. Clears the UI
const clearWordList = () => {
  wordListFile.value = null
  fullWordList.value = []
  completedWords.value = []
  rawInput.value = ''
}
// 3. mark word as done
const markWordProcessed = (word) => {
  const w = word.toLowerCase()
  // Only add it if it isn't already in the array
  if (!completedWords.value.includes(w)) {
    completedWords.value.push(w)
    
    // Instantly save the updated array to the browser's hard drive
    if (wordListFile.value && wordListFile.value.name) {
      localStorage.setItem(`flashcard_completed_${wordListFile.value.name}`, JSON.stringify(completedWords.value))
    }
  }
}
// 4. Dynamically fetch the next 10 untouched words
const fetchNextBatch = async () => {
  // Filter out words we already know are completed
  const remainingWords = fullWordList.value.filter(w => !completedWords.value.includes(w.toLowerCase()))
  
  if (remainingWords.length === 0) {
    alert("🎉 You've finished every word in this list!")
    return
  }

  // Slice out the dynamic amount using your batchSize variable
  const batch = remainingWords.slice(0, batchSize.value)
  rawInput.value = batch.join('\n')
  
  // Wait for the fetch and grab the "receipt" of successful words!
  const successfulWords = await fetchData()
  console.log(successfulWords)
  // THE NEW GHOST BUSTER
 
}

const countCardsForWord = (word) => {
  return cardQueue.value.filter(c => c.word === word).length
}

const addFutureWord = (word) => {
  if (!futureWords.value.includes(word)) futureWords.value.push(word)
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

// --- INLINE RENAME & FETCH FUNCTION ---
const renameAndFetch = async (oldWord) => {
  const newWord = renaming.value[oldWord]?.trim().toLowerCase()
  
  if (!newWord || newWord === oldWord) {
    delete renaming.value[oldWord]
    return
  }
  
  isLoading.value = true
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/fetch-words', { words: [newWord] })
    
    if (res.data[newWord]) {
      // Clean up the old word
      delete results.value[oldWord]
      delete selections.value[oldWord]
      delete renaming.value[oldWord]

      // Setup the new word
      results.value[newWord] = res.data[newWord]
      
      const robDefs = res.data[newWord].rob_definitions || []
      const wikDefs = res.data[newWord].wik_definitions || []
      const allDefs = [...robDefs, ...wikDefs]

      const newSelection = {
        activeDefs: [],
        selectedExamples: {},
        selectedImages: {},
        customImageUrls: {},
        exampleAdder: {},
        selectedSynonyms: [],
        selectedTranslations: { en: [], sv: [] },
        skipped: false
      }

      allDefs.forEach(d => {
        newSelection.selectedExamples[d.definition] = []
        newSelection.exampleAdder[d.definition] = { show: false, tab: 'other', text: '' }
      })

      selections.value[newWord] = newSelection
    }
  } catch (err) {
    console.error("Error fetching new word:", err)
    alert("Failed to fetch data for the new word.")
  }
  isLoading.value = false
}

// --- FILE DUPLICATE AGGREGATOR FUNCTION ---
const runAggregation = async () => {
  if (!listsToAggregate.value || listsToAggregate.value.length === 0) {
    alert("Please select at least one file to merge.")
    return
  }

  isAggregating.value = true
  const formData = new FormData()
  
  listsToAggregate.value.forEach(file => {
    formData.append('files', file)
  })

  try {
    const res = await axios.post('http://127.0.0.1:8000/api/aggregate-lists', formData)
    
    if (res.data.status === 'success') {
      alert(`✅ Successfully merged lists!\n\nSaved ${res.data.unique_count} unique words to:\nwordextractions/aggregations/${res.data.filename}`)
      listsToAggregate.value = [] 
    }
  } catch (err) {
    console.error("Aggregation failed:", err)
    alert("Failed to merge the lists. Check console for details.")
  } finally {
    isAggregating.value = false
  }
}

// -------------------------------------------------------------------
// BATCH STAGING & FORMATTING
// -------------------------------------------------------------------

const highlightWord = (text, word) => {
  if (!text || !word) return text
  const stemLength = Math.min(word.length, 5)
  const stem = word.substring(0, stemLength)
  const regex = new RegExp(`\\b(${stem}[a-zàâçéèêëîïôûùüÿñæœ]*)\\b`, 'gi')
  return text.replace(regex, '<span style="color: #2ecc71; font-weight: bold;">$1</span>')
}


// --- RICH TEXT EDITOR HANDLER (Bulletproof Toggle) ---
const applyGreenHighlight = () => {
  // 1. Tell the browser to use CSS (<span>)
  document.execCommand('styleWithCSS', false, true)
  
  // 2. Ask the browser what color the currently highlighted text is
  const currentColor = document.queryCommandValue('foreColor')
  
  // Normalize the string (removes spaces so rgb(46, 204, 113) becomes rgb(46,204,113))
  const normalizedColor = currentColor ? currentColor.replace(/\s/g, '') : ''
  const isGreen = normalizedColor === 'rgb(46,204,113)' || currentColor === '#2ecc71'

  if (isGreen) {
    // TOGGLE OFF: Strip the formatting back to normal text
    document.execCommand('removeFormat', false, null)
  } else {
    // TOGGLE ON: Apply the green color
    document.execCommand('foreColor', false, '#2ecc71')
    
    // Only apply bold if it isn't already bold
    if (!document.queryCommandState('bold')) {
      document.execCommand('bold', false, null)
    }
  }

  // 3. FORCE VUE TO UPDATE THE V-MODEL
  // Find the exact editor we are typing in and trigger an 'input' event so Vue saves the new HTML
  const selection = window.getSelection()
  if (selection && selection.rangeCount > 0) {
    let node = selection.focusNode
    if (node && node.nodeType === Node.TEXT_NODE) {
      node = node.parentNode
    }
    
    if (node && node.closest) {
      const editorContent = node.closest('.q-editor__content')
      if (editorContent) {
        editorContent.dispatchEvent(new Event('input', { bubbles: true }))
      }
    }
  }
}
const stageSelectedCards = () => {
  let stagedCount = 0
  for (const w in selections.value) {
    const sel = selections.value[w]
    if (sel.skipped) continue
    
    sel.activeDefs.forEach(defText => {
      if (sel.exampleAdder[defText]?.tab === 'own' && sel.exampleAdder[defText]?.text?.trim()) {
        addOwnExample(w, defText)
      }
      
      const wordData = results.value[w]
      stageCard(w, defText, wordData)
      stagedCount++
    })
    
    sel.activeDefs = []
  }
  
  if (stagedCount > 0) {
    alert(`Staged ${stagedCount} cards!`)
  }
}

const stageCard = (word, defText, wordData) => {
  const sel = selections.value[word]
  const examples = sel.selectedExamples[defText] || []
  
  let transEn = sel.selectedTranslations?.en || []
  let transSv = sel.selectedTranslations?.sv || []
  let syns = sel.selectedSynonyms || []

  // Pre-format the FRONT (Example)
  let rawExampleText = examples.join(' / ')
  let formattedExample = rawExampleText 
    ? highlightWord(rawExampleText, word) 
    : `<span style="color: #2ecc71; font-weight: bold;">${wordData.article ? wordData.article + ' ' : ''}${word}</span>`

  // Pre-format the BACK (Definition) with the "Word =" logic
  const wordDisplay = wordData.article ? `${wordData.article} ${word}` : word
  const formattedDefinition = `<span style="color: #2ecc71; font-weight: bold;">${wordDisplay} =</span> ${defText}`

  const newCard = {
    id: Date.now() + Math.random(),
    word: word,
    article: wordData.article || '',
    definition: formattedDefinition, // <-- Now Vue injects the formatting here!
    example: formattedExample, 
    imageUrl: sel.selectedImages[defText] || '',
    transEn: transEn.join(', '),
    transSv: transSv.join(', '),
    synonyms: syns.join(', ')
  }

  cardQueue.value.unshift(newCard) 

  markWordProcessed(word)
}

const exportQueue = async () => {
  if (cardQueue.value.length === 0) return
  
  try {
    const res = await axios.post('http://127.0.0.1:8000/api/export-anki', { 
      cards: cardQueue.value,
      deck_name: deckName.value
    })
    
    if (res.data.status === 'error') {
       alert(res.data.message)
       return
    }

    alert(`Successfully saved ${res.data.added_words.length} unique words to Anki!`)
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