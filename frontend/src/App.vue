<template>
  <div class="container">
    <h2>对话 Agent（SSE，LangGraph + 百炼）</h2>

    <div class="chat-window">
      <div v-for="(m, idx) in messages" :key="idx" class="msg" :class="m.role">
        <div class="role">{{ m.role === 'user' ? '你' : '助手' }}</div>
        <div class="content">{{ m.content }}</div>
      </div>
    </div>

    <form class="input-bar" @submit.prevent="onSend">
      <input
        v-model="input"
        type="text"
        placeholder="输入你的问题..."
        :disabled="loading"
      />
      <button type="submit" :disabled="loading || !input.trim()">发送</button>
      <button type="button" @click="onStop" :disabled="!loading">停止</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const messages = ref([])
const input = ref('')
const loading = ref(false)
let source = null

function startAssistantMessage() {
  messages.value.push({ role: 'assistant', content: '' })
}

function appendToAssistant(token) {
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    last.content += token
  }
}

function onStop() {
  if (source) {
    source.close()
    source = null
    loading.value = false
  }
}

function onSend() {
  const text = input.value.trim()
  if (!text) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  startAssistantMessage()
  loading.value = true

  const url = `/api/chat/stream?message=${encodeURIComponent(text)}`
  source = new EventSource(url)

  source.onmessage = (ev) => {
    if (!ev.data) return
    if (ev.data === '[DONE]') {
      onStop()
      return
    }
    try {
      const payload = JSON.parse(ev.data)
      if (payload.type === 'token') {
        appendToAssistant(payload.content)
      }
    } catch (e) {
      // ignore malformed line
    }
  }

  source.onerror = () => {
    onStop()
  }
}
</script>

<style>
:root {
  --bg: #0b1020;
  --card: #121731;
  --text: #e7eaf6;
  --muted: #9aa3b2;
  --accent: #6b8afd;
}

* { box-sizing: border-box; }
body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial; background: var(--bg); color: var(--text); }
.container { max-width: 900px; margin: 0 auto; padding: 24px; }

h2 { margin: 0 0 16px; font-weight: 600; }

.chat-window { background: var(--card); border-radius: 12px; padding: 16px; height: 60vh; overflow: auto; box-shadow: 0 8px 30px rgba(0,0,0,0.25); }
.msg { display: grid; grid-template-columns: 80px 1fr; gap: 8px 16px; padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.msg .role { color: var(--muted); font-size: 13px; }
.msg .content { white-space: pre-wrap; line-height: 1.6; }
.msg.user .content { color: #c5d1ff; }
.msg.assistant .content { color: #d6f1ff; }

.input-bar { display: flex; gap: 8px; margin-top: 16px; }
.input-bar input { flex: 1; padding: 12px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); background: #0e1430; color: var(--text); }
.input-bar button { padding: 10px 12px; border-radius: 10px; border: none; background: var(--accent); color: white; cursor: pointer; }
.input-bar button[disabled] { opacity: 0.6; cursor: not-allowed; }
</style>
