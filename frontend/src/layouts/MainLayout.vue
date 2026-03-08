<template>
  <q-layout view="lHh Lpr lFf">
    
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn dense flat round icon="menu" @click="toggleLeftDrawer" />
        <q-toolbar-title>Flashcard Factory</q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered>
      <q-list>
        <q-item-label header>Tools</q-item-label>

        <q-item clickable v-ripple @click="openWordSelector" class="bg-grey-2">
          <q-item-section avatar>
            <q-icon name="checklist" color="primary" />
          </q-item-section>
          <q-item-section class="text-weight-bold text-primary">
            Open Word Selector
          </q-item-section>
        </q-item>

        <q-separator class="q-my-sm" />
        <q-item-label header>Book Progress</q-item-label>

        <div v-if="bookStats.length === 0" class="q-pa-md text-grey text-caption">
          No progress recorded yet.
        </div>

        <q-expansion-item
          v-for="stat in bookStats"
          :key="stat.book_name"
          :label="formatBookName(stat.book_name)"
          icon="📖"
          header-class="text-weight-medium"
        >
          <q-card class="bg-grey-1">
            <q-card-section class="q-pt-xs">
              
              <div class="row text-caption text-grey-8 text-weight-bold q-mt-sm">SELECTION PROGRESS</div>
              <div class="row items-center justify-between">
                <span>Sorted:</span>
                <span class="text-weight-bold">{{ stat.sel_idx }} / {{ stat.total_freq }}</span>
              </div>
              <q-linear-progress :value="stat.sel_idx / stat.total_freq" color="primary" class="q-my-xs" />
              <div class="row">
              <div class="col-8 text-caption text-grey-6 text-italic ">
                Latest selection: "{{ stat.last_sel_word }}"
              </div>
              <div class="col-1 q-ml-md q-mr-lg q-pl-md">
                {{ stat.total_learn }}✅  
              </div>
              <div class="col-1"> {{ stat.sel_idx - stat.total_learn }}❌
              </div>
            </div>
              <div class="text-caption text-grey-8 text-weight-bold q-mt-md">FLASHCARDS GENERATED</div>
              <div class="row items-center justify-between">
                <span>Created:</span>
                <span class="text-weight-bold">{{ stat.anki_idx }} / {{ stat.total_learn }}</span>
              </div>
              <q-linear-progress :value="stat.total_learn ? (stat.anki_idx / stat.total_learn) : 0" color="secondary" class="q-my-xs" />
              <div class="text-caption text-grey-6 text-italic">
                Latest export: "{{ stat.last_anki_word }}"
              </div>

            </q-card-section>
          </q-card>
        </q-expansion-item>

      </q-list>
    </q-drawer>

    <WordSelector ref="wordSelectorDialog" @hide="fetchStats" />
    
    <q-page-container>
      <router-view />
    </q-page-container>

  </q-layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import WordSelector from 'components/WordSelector.vue' // Ensure this path is correct

const leftDrawerOpen = ref(true)
const wordSelectorDialog = ref(null)
const bookStats = ref([])

const toggleLeftDrawer = () => {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

const openWordSelector = () => {
  if (wordSelectorDialog.value) {
    wordSelectorDialog.value.openDialog()
  }
}

// Beautifies "les_trois_mousquetaires" to "Les Trois Mousquetaires"
const formatBookName = (name) => {
  return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const fetchStats = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/selector/stats')
    bookStats.value = res.data
  } catch (error) {
    console.error("Error fetching stats:", error)
  }
}

// Load stats when the app opens
onMounted(() => {
  fetchStats()
})
</script>