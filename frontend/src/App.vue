<script setup>
import { ref } from 'vue'

// 状态定义 (类似于 React 的 useState)
const inputMsg = ref('')
const messages = ref([
  { role: 'assistant', content: '你好！我是你的 AI 导购，想买点什么？' }
])
const isLoading = ref(false)

// 发送消息的处理函数
const sendMessage = async () => {
  if (!inputMsg.value.trim()) return

  // 1. 把用户的消息加到列表
  messages.value.push({ role: 'user', content: inputMsg.value })
  const userQuery = inputMsg.value
  inputMsg.value = '' // 清空输入框
  isLoading.value = true

  try {
    // 2. 调用后端 API (我们马上就要去写这个 Python API)
    // 注意：这里假设后端开在 8000 端口
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: userQuery })
    })

    const data = await response.json()
    
    // 3. 把 AI 的回复加到列表
    messages.value.push({ role: 'assistant', content: data.reply })
  } catch (error) {
    messages.value.push({ role: 'assistant', content: '连接服务器失败，请检查后端是否启动。' })
    console.error(error)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-100 flex items-center justify-center p-4">
    <div class="w-full max-w-2xl bg-white rounded-xl shadow-lg overflow-hidden flex flex-col h-[600px]">
      
      <!-- 标题栏 -->
      <div class="bg-blue-600 p-4 text-white font-bold text-lg">
        🛍️ SmartShopper Agent
      </div>

      <!-- 聊天记录区域 -->
      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <div 
          v-for="(msg, index) in messages" 
          :key="index"
          :class="`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`"
        >
          <div 
            :class="`max-w-[80%] rounded-lg p-3 ${
              msg.role === 'user' 
                ? 'bg-blue-500 text-white' 
                : 'bg-gray-100 text-gray-800'
            }`"
          >
            {{ msg.content }}
          </div>
        </div>
        
        <!-- Loading 状态 -->
        <div v-if="isLoading" class="flex justify-start">
          <div class="bg-gray-100 text-gray-500 rounded-lg p-3 animate-pulse">
            思考中...
          </div>
        </div>
      </div>

      <!-- 输入框区域 -->
      <div class="p-4 border-t border-gray-200 flex gap-2">
        <input 
          v-model="inputMsg" 
          @keyup.enter="sendMessage"
          type="text" 
          placeholder="我想买一件蓝色的衬衫..." 
          class="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button 
          @click="sendMessage"
          :disabled="isLoading"
          class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition"
        >
          发送
        </button>
      </div>

    </div>
  </div>
</template>