/**
 * Basic usage example for MemU JavaScript SDK
 *
 * This example demonstrates how to:
 * 1. Initialize the MemU client
 * 2. Memorize a conversation
 * 3. Check task status
 * 4. Retrieve memories and categories
 * 5. Chat with memory-enhanced conversation
 */

import { MemuClient } from 'memu-js'
import process from 'node:process'

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

const waitForTaskCompletion = async (client, taskId) => {
  // Poll task status until terminal state
  while (true) {
    const status = await client.getTaskStatus(taskId)
    console.log(`⏳ Task status: ${status.status}`)
    if (['FAILURE', 'REVOKED', 'SUCCESS'].includes(status.status)) {
      console.log(`✅ Task ${taskId} completed with status: ${status.status}`)
      break
    }
    await sleep(2000)
  }
}

export const basicExample = async () => {
  // Initialize client with environment variables or direct config
  const client = new MemuClient({
    apiKey: process.env.MEMU_API_KEY || 'your-api-key-here',
    baseUrl: process.env.MEMU_API_BASE_URL || 'https://api.memu.so',
    maxRetries: 3,
    timeout: 30000, // 30 seconds
  })

  try {
    console.log('🚀 Starting MemU SDK example...\n')

    // Example 1: Memorize a text conversation
    console.log('📝 Memorizing text conversation...')
    const textResponse = await client.memorizeConversation(
      'User: I love hiking in the mountains.\nAssistant: That sounds wonderful! What\'s your favorite trail?',
      'user',
      'Johnson',
      'assistant',
      'Assistant',
      new Date().toISOString(),
    )

    console.log(`✅ Task started: ${textResponse.taskId}`)
    console.log(`   Status: ${textResponse.status}`)
    console.log(`   Message: ${textResponse.message}`)

    // Wait for task completion
    await waitForTaskCompletion(client, textResponse.taskId)
    console.log()

    // Example 2: Memorize a structured conversation
    console.log('💬 Memorizing structured conversation...')
    const structuredResponse = await client.memorizeConversation(
      [
        { content: 'What gear do I need for winter hiking?', role: 'user' },
        { content: 'For winter hiking, you\'ll need insulated boots, layered clothing, and safety equipment like crampons and a headlamp.', role: 'assistant' },
      ],
      'user',
      'Johnson',
      'assistant',
      'Assistant',
    )

    console.log(`✅ Task started: ${structuredResponse.taskId}`)
    console.log(`   Status: ${structuredResponse.status}`)

    // Wait for task completion
    await waitForTaskCompletion(client, structuredResponse.taskId)
    console.log()

    // Example 3: Check task status
    console.log('⏳ Checking task status...')
    const status = await client.getTaskStatus(textResponse.taskId)
    console.log(`📊 Task ${status.taskId}:`)
    console.log(`   Status: ${status.status}`)
    if (status.progress) {
      console.log(`   Progress: ${JSON.stringify(status.progress)}`)
    }
    if (status.error) {
      console.log(`   Error: ${status.error}`)
    }
    console.log()

    // Example 4: Retrieve default categories
    console.log('📂 Retrieving default categories...')
    const categories = await client.retrieveDefaultCategories({
      agentId: 'assistant',
      includeInactive: false,
      userId: 'user',
    })

    console.log(`📋 Found ${categories.totalCategories} categories:`)
    categories.categories.forEach((category, index) => {
      console.log(`   ${index + 1}. ${category.categoryName} (${category.memoryCount} memories)`)
      console.log(`      Type: ${category.categoryType}`)
      console.log(`      Active: ${category.isActive ? '✅' : '❌'}`)
    })
    console.log()

    // Example 5: Search for related memories
    console.log('🔍 Searching for related memories...')
    const relatedMemories = await client.retrieveRelatedMemoryItems({
      agentId: 'assistant',
      minSimilarity: 0.3,
      query: 'hiking equipment',
      topK: 5,
      userId: 'user',
    })

    console.log(`🎯 Found ${relatedMemories.totalFound} related memories:`)
    relatedMemories.relatedMemories.forEach((memory, index) => {
      console.log(`   ${index + 1}. Score: ${memory.similarityScore.toFixed(3)}`)
      console.log(`      Category: ${memory.memory.category}`)
      console.log(`      Content: ${memory.memory.content.substring(0, 100)}...`)
      console.log(`      Date: ${memory.memory.happenedAt}`)
    })
    console.log()

    // Example 6: Search for clustered categories
    console.log('🗂️ Searching for clustered categories...')
    const clusteredCategories = await client.retrieveRelatedClusteredCategories({
      agentId: 'assistant',
      categoryQuery: 'outdoor activities',
      minSimilarity: 0.4,
      topK: 3,
      userId: 'user',
    })

    console.log(`📚 Found ${clusteredCategories.totalCategoriesFound} clustered categories:`)
    clusteredCategories.clusteredCategories.forEach((cluster, index) => {
      console.log(`   ${index + 1}. ${cluster.categoryName} (Score: ${cluster.similarityScore.toFixed(3)})`)
      console.log(`      Memories: ${cluster.memoryCount}`)
      cluster.memories.slice(0, 2).forEach((memory) => {
        console.log(`        - ${memory.content.substring(0, 80)}...`)
      })
    })

    console.log()

    // Example 7: Chat with memory-enhanced conversation
    console.log('💬 Starting memory-enhanced chat...')
    const chatResponse = await client.chat({
      agentId: 'assistant',
      agentName: 'Assistant',
      kwargs: {
        temperature: 0.7,
        maxTokens: 150,
      },
      message: 'What should I prepare for my next hiking trip?',
      model: 'gpt-4o-mini', // Specify the chat model
      system: 'You are a helpful hiking assistant with expertise in outdoor activities and safety.',
      userId: 'user',
      userName: 'Johnson',
    })

    console.log(`🤖 AI Response: ${chatResponse.message}`)
    console.log('📊 Token Usage:')
    console.log(`   Total Tokens: ${chatResponse.chatTokenUsage.totalTokens}`)
    console.log(`   Prompt Tokens: ${chatResponse.chatTokenUsage.promptTokens}`)
    console.log(`   Completion Tokens: ${chatResponse.chatTokenUsage.completionTokens}`)
    
    if (chatResponse.chatTokenUsage.promptTokensBreakdown) {
      const breakdown = chatResponse.chatTokenUsage.promptTokensBreakdown
      console.log('   Token Breakdown:')
      console.log(`     - Current Query: ${breakdown.currentQuery || 0}`)
      console.log(`     - Short Term Context: ${breakdown.shortTermContext || 0}`)
      console.log(`     - User Profile: ${breakdown.userProfile || 0}`)
      console.log(`     - Retrieved Memory: ${breakdown.retrievedMemory || 0}`)
    }

    console.log('\n✨ Example completed successfully!')
  }
  catch (error) {
    console.error('❌ Error occurred:', error.message)
    if (error.statusCode) {
      console.error(`   Status Code: ${error.statusCode}`)
    }
    if (error.responseData) {
      console.error(`   Response Data: ${JSON.stringify(error.responseData)}`)
    }
  }
}

// Run the example
if (import.meta.main)
  basicExample().catch(console.error)
