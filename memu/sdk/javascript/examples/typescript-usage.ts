/* eslint-disable @masknet/prefer-timer-id */
/**
 * TypeScript usage example for MemU JavaScript SDK
 *
 * This example demonstrates how to use the SDK with full TypeScript support
 */

import type {
  ChatResponse,
  DefaultCategoriesResponse,
  MemorizeResponse,
  MemorizeTaskStatusResponse,
  MemuClientConfig,
  RelatedClusteredCategoriesResponse,
  RelatedMemoryItemsResponse,
} from 'memu-js'

import {
  MemuAPIException,
  MemuAuthenticationException,
  MemuClient,
  MemuConnectionException,
  MemuValidationException,
} from 'memu-js'
import process from 'node:process'

interface ConversationMessage {
  content: string
  role: 'assistant' | 'user'
}

// Utility function to demonstrate type inference
export const memorySearchHelper = async (
  client: MemuClient,
  userId: string,
  query: string,
  options?: {
    agentId?: string
    minSimilarity?: number
    topK?: number
  },
): Promise<number> => {
  const response = await client.retrieveRelatedMemoryItems({
    agentId: options?.agentId,
    minSimilarity: options?.minSimilarity ?? 0.3,
    query,
    topK: options?.topK ?? 10,
    userId,
  })

  return response.totalFound
}

export const typescriptExample = async (): Promise<void> => {
  // Initialize client with typed configuration
  const config: MemuClientConfig = {
    apiKey: process.env.MEMU_API_KEY ?? 'your-api-key-here',
    baseUrl: process.env.MEMU_API_BASE_URL ?? 'https://api.memu.ai',
    maxRetries: 3,
    timeout: 30000,
  }

  const client = new MemuClient(config)

  try {
    console.log('🚀 Starting TypeScript MemU SDK example...\n')

    // Example 1: Typed conversation messages
    const conversation: ConversationMessage[] = [
      { content: 'I want to learn about machine learning.', role: 'user' },
      { content: 'Great! Machine learning is a subset of AI that enables computers to learn and make decisions from data.', role: 'assistant' },
    ]

    console.log('🤖 Memorizing ML conversation...')
    const memorizeResponse: MemorizeResponse = await client.memorizeConversation(
      conversation,
      'student_456',
      'Bob Smith',
      'ml_tutor',
      'ML Tutor',
    )

    console.log(`✅ Task ID: ${memorizeResponse.taskId}`)
    console.log(`   Status: ${memorizeResponse.status}\n`)

    // Example 2: Polling task status with proper typing
    console.log('⏳ Polling task status...')
    let taskStatus: MemorizeTaskStatusResponse
    let attempts = 0
    const maxAttempts = 10

    do {
      await new Promise(resolve => setTimeout(resolve, 2000))
      taskStatus = await client.getTaskStatus(memorizeResponse.taskId)
      attempts++

      console.log(`   Attempt ${attempts}: ${taskStatus.status}`)

      if ('progress' in taskStatus) {
        console.log(`   Progress: ${JSON.stringify(taskStatus.progress)}`)
      }
    } while (
      taskStatus.status === 'PENDING'
      && attempts < maxAttempts
    )

    if (taskStatus.status === 'SUCCESS') {
      console.log('✅ Memorization completed successfully!')
      if ('detailInfo' in taskStatus) {
        console.log(`   Detail: ${taskStatus.detailInfo}`)
      }
    }
    else if (taskStatus.status === 'FAILURE') {
      console.log('❌ Memorization failed!')
      if ('detailInfo' in taskStatus) {
        console.log(`   Detail: ${taskStatus.detailInfo}`)
      }
    }
    console.log()

    // Example 3: Retrieve categories with full typing
    console.log('📂 Retrieving default categories...')
    const categoriesResponse: DefaultCategoriesResponse = await client.retrieveDefaultCategories({
      agentId: 'ml_tutor',
      userId: 'student_456',
    })

    console.log(`   Total categories: ${categoriesResponse.totalCategories}`)

    categoriesResponse.categories.forEach((category, index) => {
      console.log(`   ${index + 1}. ${category.name}`)
      console.log(`      Type: ${category.type}`)
      console.log(`      Description: ${category.description}`)
      console.log(`      Memories: ${category.memoryItems?.memoryCount}`)
      // missing / removed
      // console.log(`      Active: ${category.isActive}`)
    })
    console.log()

    // Example 4: Search memories with type safety
    console.log('🔍 Searching for ML-related memories...')
    const searchResponse: RelatedMemoryItemsResponse = await client.retrieveRelatedMemoryItems({
      agentId: 'ml_tutor',
      includeCategories: ['learning', 'technology'],
      minSimilarity: 0.3,
      query: 'machine learning algorithms',
      topK: 5,
      userId: 'student_456',
    })

    console.log(`🎯 Query: "${searchResponse.query}"`)
    console.log(`   Total found: ${searchResponse.totalFound}`)
    console.log(`   Search params: ${JSON.stringify(searchResponse.searchParams)}`)

    searchResponse.relatedMemories.forEach((relatedMemory, index) => {
      const { memory, similarityScore } = relatedMemory
      console.log(`   ${index + 1}. Score: ${similarityScore.toFixed(3)}`)
      console.log(`      ID: ${memory.memoryId}`)
      console.log(`      Category: ${memory.category}`)
      console.log(`      Content: ${memory.content.substring(0, 100)}...`)
      console.log(`      Created: ${memory.createdAt.toJSON()}`)
      console.log(`      Updated: ${memory.updatedAt.toJSON()}`)
    })
    console.log()

    // Example 5: Clustered categories search
    console.log('🗂\uFE0F Searching clustered categories...')
    const clustersResponse: RelatedClusteredCategoriesResponse
      = await client.retrieveRelatedClusteredCategories({
        agentId: 'ml_tutor',
        categoryQuery: 'artificial intelligence',
        minSimilarity: 0.4,
        topK: 3,
        userId: 'student_456',
      })

    console.log(`📚 Category query: "${clustersResponse.categoryQuery}"`)
    console.log(`   Categories found: ${clustersResponse.totalCategoriesFound}`)

    clustersResponse.clusteredCategories.forEach((cluster, index) => {
      console.log(`   ${index + 1}. ${cluster.name}`)
      console.log(`      Similarity: ${cluster.similarityScore.toFixed(3)}`)
      console.log(`      Memory count: ${cluster.memoryCount}`)

      // Show first few memories in the cluster
      cluster.memories?.slice(0, 2).forEach((memory, memIndex) => {
        console.log(`      Memory ${memIndex + 1}: ${memory.content.substring(0, 60)}...`)
      })
    })

    console.log()

    // Example 6: Memory-enhanced chat with full TypeScript support
    console.log('💬 Starting memory-enhanced chat...')
    const chatResponse: ChatResponse = await client.chat({
      agentId: 'ml_tutor',
      agentName: 'ML Tutor',
      kwargs: {
        maxTokens: 200,
        temperature: 0.8,
      },
      message: 'Can you explain more about supervised vs unsupervised learning?',
      model: 'gpt-5-nano', // Specify the chat model
      system: 'You are an expert machine learning tutor who explains concepts clearly with practical examples.',
      userId: 'student_456',
      userName: 'Bob Smith',
    })

    console.log(`🤖 AI Response: ${chatResponse.message}`)
    console.log('📊 Token Usage:')
    console.log(`   Total Tokens: ${chatResponse.chatTokenUsage.totalTokens}`)
    console.log(`   Prompt Tokens: ${chatResponse.chatTokenUsage.promptTokens}`)
    console.log(`   Completion Tokens: ${chatResponse.chatTokenUsage.completionTokens}`)
    
    // Type-safe access to token breakdown
    const breakdown = chatResponse.chatTokenUsage.promptTokensBreakdown
    if (breakdown) {
      console.log('   Token Breakdown:')
      if (breakdown.currentQuery !== undefined) {
        console.log(`     - Current Query: ${breakdown.currentQuery}`)
      }
      if (breakdown.shortTermContext !== undefined) {
        console.log(`     - Short Term Context: ${breakdown.shortTermContext}`)
      }
      if (breakdown.userProfile !== undefined) {
        console.log(`     - User Profile: ${breakdown.userProfile}`)
      }
      if (breakdown.retrievedMemory !== undefined) {
        console.log(`     - Retrieved Memory: ${breakdown.retrievedMemory}`)
      }
    }

    console.log('\n✨ TypeScript example completed successfully!')
  }
  catch (error) {
    console.error('❌ Error occurred:')

    // Type-safe error handling
    if (error instanceof MemuValidationException) {
      console.error(`   Validation Error: ${error.message}`)
      console.error(`   Status Code: ${error.statusCode}`)
      if (error.responseData) {
        console.error(`   Response Data: ${JSON.stringify(error.responseData, null, 2)}`)
      }
    }
    else if (error instanceof MemuAuthenticationException) {
      console.error(`   Authentication Error: ${error.message}`)
      console.error(`   Status Code: ${error.statusCode}`)
    }
    else if (error instanceof MemuConnectionException) {
      console.error(`   Connection Error: ${error.message}`)
    }
    else if (error instanceof MemuAPIException) {
      console.error(`   API Error: ${error.message}`)
      console.error(`   Status Code: ${error.statusCode}`)
      if (error.responseData) {
        console.error(`   Response Data: ${JSON.stringify(error.responseData, null, 2)}`)
      }
    }
    else {
      console.error(`   Unknown Error: ${error}`)
    }
  }
}

// Run if this file is executed directly
if (import.meta.main)
  typescriptExample().catch(console.error)
