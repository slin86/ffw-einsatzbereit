<script setup lang="ts">
import { ref } from "vue";

import { errorText, shareFile } from "../../api";
import { toast } from "../toast";
import BottomSheet from "./BottomSheet.vue";
import MIcon from "./MIcon.vue";

const props = defineProps<{ query: string; description: string }>();

const sheet = ref<InstanceType<typeof BottomSheet> | null>(null);
const busy = ref("");

const FORMATS = [
  { fmt: "pdf", label: "PDF", hint: "Zum Ausdrucken oder für die Wehrführung" },
  { fmt: "xlsx", label: "Excel", hint: "Zum Weiterrechnen" },
  { fmt: "csv", label: "CSV", hint: "Für andere Programme" },
] as const;

async function share(fmt: string): Promise<void> {
  busy.value = fmt;
  try {
    const done = await shareFile(`/api/exports/${fmt}${props.query ? `?${props.query}` : ""}`);
    if (done) sheet.value?.close();
  } catch (e) {
    toast(errorText(e), "error");
  } finally {
    busy.value = "";
  }
}

defineExpose({ open: () => sheet.value?.open() });
</script>

<template>
  <BottomSheet ref="sheet" title="Liste teilen" :subtitle="description">
    <ul class="group">
      <li v-for="f in FORMATS" :key="f.fmt">
        <button type="button" class="cell" :disabled="!!busy" @click="share(f.fmt)">
          <span class="cell-icon"><MIcon name="share" :size="20" /></span>
          <span class="cell-main">
            <strong>{{ f.label }}</strong>
            <span class="cell-sub">{{ busy === f.fmt ? "Wird erstellt …" : f.hint }}</span>
          </span>
        </button>
      </li>
    </ul>
  </BottomSheet>
</template>
