<template>
  <div>
    <div class="header">
      <div class="brand">Hierarchical Agent Teams Demo</div>
      <div class="lang-switcher">
        <select v-model="lang" aria-label="language switcher">
          <option value="zh">中文</option>
          <option value="en">EN</option>
        </select>
      </div>
    </div>

    <div class="container">
      <div class="chat-window" ref="chatWindowEl">
        <div v-for="(m, idx) in messages" :key="idx" class="msg" :class="m.role">
          <div
            class="avatar"
            :class="m.role"
            role="img"
            :aria-label="m.role === 'assistant' ? texts.assistant : texts.me"
            :title="m.role === 'assistant' ? texts.assistant : texts.me"
          >{{ m.role === 'assistant' ? '🤖' : '🧑' }}</div>
          <div class="bubble">
            <div v-if="isThinking(idx, m)" class="think">
              <span class="think-text">{{ texts.thinking }}</span>
              <span class="dots"><span></span><span></span><span></span></span>
            </div>
            <div v-else>
              <div v-html="renderMarkdown(m.content)"></div>
            </div>
          </div>
        </div>
      </div>

      <form class="input-bar" @submit.prevent="onSend">
        <input
          v-model="input"
          type="text"
          :placeholder="texts.placeholder"
          :disabled="loading"
        />
        <button type="submit" :disabled="loading || !input.trim()">{{ texts.send }}</button>
        <button type="button" @click="onStop" :disabled="!loading">{{ texts.stop }}</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { marked } from 'marked'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const lang = ref('en')
let source = null

const texts = computed(() => {
  if (lang.value === 'en') {
    return {
      me: 'You',
      assistant: 'Assistant',
      placeholder: 'Type your question...',
      send: 'Send',
      stop: 'Stop',
      greeting: "Hello! I'm your assistant. Ask me anything.",
      thinking: 'Thinking',
      steps: 'Execution Steps',
      workflow: 'Workflow Path',
      supervisor: 'Supervisor',
      reason: 'Reason',
      research: 'Research',
      writing: 'Writing',
    }
  }
  return {
    me: '你',
    assistant: '助手',
    placeholder: '输入你的问题...',
    send: '发送',
    stop: '停止',
    greeting: '你好！我是你的助手，有什么可以帮你？',
    thinking: '正在思考',
    steps: '执行步骤',
    workflow: '工作流路径',
    supervisor: '路由器',
    reason: '原因',
    research: '研究',
    writing: '写作',
  }
})

const chatWindowEl = ref(null)

onMounted(() => {
  messages.value.push({ role: 'assistant', content: texts.value.greeting })
  nextTick(() => scrollToBottom())
})

marked.setOptions({ gfm: true, breaks: true })
function renderMarkdown(text) {
  return marked.parse(text || '')
}

function startAssistantMessage() {
  messages.value.push({ role: 'assistant', content: '' })
  scrollToBottom()
}

function appendToAssistant(token) {
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    last.content += token
  }
  scrollToBottom()
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
  scrollToBottom()

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

function isThinking(index, message) {
  return (
    message.role === 'assistant' &&
    loading.value === true &&
    index === messages.value.length - 1 &&
    (!message.content || message.content.length === 0)
  )
}

function scrollToBottom() {
  const el = chatWindowEl.value
  if (!el) return
  requestAnimationFrame(() => {
    el.scrollTop = el.scrollHeight
  })
}
</script>

<style>
:root {
  --bg: #000000;
  --card: #0d0d0d;
  --text: #eaeaea;
  --muted: #9aa3b2;
  --accent: #6b8afd;
}

* { box-sizing: border-box; }
body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial; background: var(--bg); color: var(--text); }
.container { margin: 0 auto; padding: 24px; }

.header { position: sticky; top: 0; z-index: 10; backdrop-filter: blur(8px); background: rgba(0,0,0,0.6); border-bottom: 1px solid rgba(255,255,255,0.06); }
.header { display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; }
.brand { font-weight: 700; letter-spacing: 0.3px; color: #ffffff; }
.lang-switcher select { background: var(--card); color: var(--text); border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 6px 10px; }

h2 { margin: 0 0 16px; font-weight: 600; }

.chat-window { background: var(--card); border-radius: 12px; padding: 16px; height: 80vh; overflow: auto; box-shadow: 0 8px 30px rgba(0,0,0,0.5); }
.msg { display: flex; padding: 8px 0; align-items: flex-start; gap: 10px; }
.msg.assistant { justify-content: flex-start; }
.msg.user { flex-direction: row-reverse; }
.avatar { width: 32px; height: 32px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 18px; line-height: 1; user-select: none; }
.avatar.assistant { background: #1a1a1a; color: #eaeaea; border: 1px solid rgba(255,255,255,0.08); }
.avatar.user { background: var(--accent); color: #ffffff; }
.bubble { max-width: 80%; padding: 10px 12px; border-radius: 12px; line-height: 1.6; word-break: break-word; }
.msg.assistant .bubble { background: #111111; color: var(--text); border: 1px solid rgba(255,255,255,0.08); }
.msg.user .bubble { background: var(--accent); color: #ffffff; }
.bubble p { margin: 0; }
.bubble p + p { margin-top: 0.6em; }
.bubble code { background: rgba(255,255,255,0.12); padding: 0.1em 0.3em; border-radius: 6px; }
.bubble pre { background: rgba(255,255,255,0.08); padding: 10px; border-radius: 8px; overflow: auto; }

/* thinking loading */
.think { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); }
.dots { display: inline-flex; gap: 4px; }
.dots span { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.25; animation: blink 1.2s infinite ease-in-out; }
.dots span:nth-child(1) { animation-delay: 0s; }
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 100% { opacity: 0.25; transform: translateY(0); } 50% { opacity: 1; transform: translateY(-1px); } }

.input-bar { display: flex; gap: 8px; margin-top: 16px; }
.input-bar input { flex: 1; padding: 12px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); background: var(--card); color: var(--text); }
.input-bar button { padding: 10px 12px; border-radius: 10px; border: none; background: var(--accent); color: white; cursor: pointer; }
.input-bar button[disabled] { opacity: 0.6; cursor: not-allowed; }

/* steps */
.steps { margin-top: 12px; padding-top: 8px; border-top: 1px dashed rgba(255,255,255,0.12); }
.steps-title { font-size: 12px; color: var(--muted); margin-bottom: 6px; }

/* workflow overview */
.workflow-overview {
  background: linear-gradient(135deg, rgba(107,138,253,0.06), rgba(52,199,89,0.04));
  border: 1px solid rgba(107,138,253,0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.workflow-title {
  font-size: 11px;
  color: var(--accent);
  font-weight: 600;
  margin-bottom: 10px;
  text-align: center;
}

.workflow-path {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workflow-node {
  background: rgba(255,255,255,0.08);
  color: var(--muted);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.workflow-node.active {
  background: linear-gradient(135deg, rgba(107,138,253,0.3), rgba(107,138,253,0.5));
  color: #ffffff;
  border-color: rgba(107,138,253,0.4);
  box-shadow: 0 2px 8px rgba(107,138,253,0.2);
}

.workflow-node.completed {
  background: linear-gradient(135deg, rgba(52,199,89,0.3), rgba(52,199,89,0.5));
  color: #ffffff;
  border-color: rgba(52,199,89,0.4);
  box-shadow: 0 2px 8px rgba(52,199,89,0.2);
}

.workflow-connector {
  color: var(--accent);
  font-size: 14px;
  font-weight: bold;
}

.step-item { margin-bottom: 10px; }
.step-item.route { 
  background: linear-gradient(135deg, rgba(107,138,253,0.08), rgba(52,199,89,0.06)); 
  border: 1px solid rgba(107,138,253,0.2); 
  padding: 12px; 
  border-radius: 12px;
  backdrop-filter: blur(8px);
}

.step-head { display: inline-flex; gap: 6px; align-items: center; margin-bottom: 6px; }
.step-head.route-step { flex-direction: column; align-items: stretch; gap: 8px; }

.route-badges { 
  display: flex; 
  align-items: center; 
  gap: 8px; 
  justify-content: center;
}

.route-arrow { 
  color: var(--accent); 
  font-size: 16px; 
  font-weight: bold;
  text-shadow: 0 0 8px rgba(107,138,253,0.3);
}

.route-description {
  font-size: 11px;
  color: var(--muted);
  text-align: center;
  background: rgba(255,255,255,0.04);
  padding: 4px 8px;
  border-radius: 6px;
  font-style: italic;
}

.route-reason {
  font-size: 10px;
  color: var(--muted);
  text-align: center;
  margin-top: 4px;
}

.reason-label {
  font-weight: 600;
  color: var(--accent);
}

.workflow-status {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 6px;
  font-size: 10px;
}

.status-item {
  color: var(--muted);
  transition: color 0.2s;
}

.status-item.completed {
  color: #34c759;
}

.badge { font-size: 11px; background: rgba(255,255,255,0.12); color: var(--text); border-radius: 6px; padding: 2px 6px; }
.badge.node { background: rgba(107,138,253,0.35); }
.badge.team { background: rgba(255,149,0,0.35); color: #ffffff; }
.badge.sup { background: rgba(255,255,255,0.18); font-weight: 600; }
.badge.dest { 
  background: linear-gradient(135deg, rgba(52,199,89,0.4), rgba(52,199,89,0.6)); 
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(52,199,89,0.2);
}
.step-body { font-size: 14px; }
</style>
