<template>
  <q-dialog v-model="isOpen" persistent>
    <q-card style="min-width: 400px; text-align: center; padding: 20px;">
      
      <q-card-section>
        <div class="text-h6 text-primary">Vocabulary Word Selector</div>
        <q-select 
          v-model="selectedBook" 
          :options="availableBooks" 
          label="Select a Book" 
          @update:model-value="fetchNextWord"
          filled
          class="q-mt-md"
        />
      </q-card-section>

      <q-card-section v-if="selectedBook">
        <div v-if="loading" class="q-pa-md">
          <q-spinner color="primary" size="3em" />
        </div>
        
        <div v-else-if="currentWord">
          <div class="text-caption text-grey q-mb-sm">
            Word {{ currentIndex + 1 }} of {{ totalWords }}
          </div>
          
          <div class="text-h3 text-weight-bold q-my-sm text-dark">
            {{ currentWord }}
          </div>

          <q-badge color="secondary" class="q-mb-lg text-subtitle1" v-if="currentFrequency !== 'Unknown'">
            Appears {{ currentFrequency }} times
          </q-badge>
          
          <div class="row justify-center q-gutter-lg q-mt-md">
            <q-btn 
              color="negative" 
              icon="close" 
              label="Skip (N)" 
              size="lg"
              @click="makeDecision('n')" 
            />
            <q-btn 
              color="positive" 
              icon="check" 
              label="Learn (Y)" 
              size="lg"
              @click="makeDecision('y')" 
            />
          </div>
          
          <div class="text-caption text-grey q-mt-md">
            Use the 'Y' and 'N' keys on your keyboard for speed!
          </div>
        </div>
        
        <div v-else class="text-h6 text-positive q-my-lg">
          🎉 You've finished all words for this book!
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Close" color="primary" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

const isOpen = ref(false)
const availableBooks = ref([])
const selectedBook = ref(null)
const currentWord = ref(null)
const currentFrequency = ref(null)
const currentIndex = ref(0)
const totalWords = ref(0)
const loading = ref(false)

// Matches the port used in your main.py
const API_BASE = 'http://localhost:8000/api'

const openDialog = async () => {
  isOpen.value = true
  await fetchBooks()
}

const fetchBooks = async () => {
  try {
    const res = await axios.get(`${API_BASE}/selector/books`)
    availableBooks.value = res.data
  } catch (error) {
    console.error("Could not fetch books", error)
  }
}

const fetchNextWord = async () => {
  if (!selectedBook.value) return
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/selector/next?book_name=${selectedBook.value}`)
    currentWord.value = res.data.word
    currentFrequency.value = res.data.frequency
    currentIndex.value = res.data.index
    totalWords.value = res.data.total
  } catch (error) {
    console.error("Error fetching word", error)
  } finally {
    loading.value = false
  }
}

const makeDecision = async (decision) => {
  if (!currentWord.value || loading.value) return
  
  loading.value = true
  try {
    await axios.post(`${API_BASE}/selector/decide`, {
      book_name: selectedBook.value,
      word: currentWord.value,
      decision: decision
    })
    await fetchNextWord()
  } catch (error) {
    console.error("Error saving decision", error)
    loading.value = false
  }
}

const handleKeydown = (e) => {
  if (!isOpen.value || !currentWord.value) return
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  
  if (e.key === 'y' || e.key === 'Y') makeDecision('y')
  if (e.key === 'n' || e.key === 'N') makeDecision('n')
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

defineExpose({ openDialog })
</script>