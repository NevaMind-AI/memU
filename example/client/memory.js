/**
 * Basic usage example for MemU JavaScript SDK
 * 
 * This example demonstrates how to:
 * 1. Initialize the MemU client
 * 2. Memorize a conversation
 * 3. Check task status
 * 4. Retrieve memories and categories
 */

import { MemuClient } from 'memu-js';

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForTaskCompletion(client, taskId) {
  // Poll task status until terminal state
  while (true) {
    const status = await client.getTaskStatus(taskId);
    console.log(`⏳ Task status: ${status.status}`);
    if (['SUCCESS', 'FAILURE', 'REVOKED'].includes(status.status)) {
      console.log(`✅ Task ${taskId} completed with status: ${status.status}`);
      break;
    }
    await sleep(2000);
  }
}

async function basicExample() {
  // Initialize client with environment variables or direct config
  const client = new MemuClient({
    baseUrl: process.env.MEMU_API_BASE_URL || 'https://api.memu.so',
    apiKey: process.env.MEMU_API_KEY || 'your-api-key-here',
    timeout: 30000, // 30 seconds
    maxRetries: 3
  });

  try {
    console.log('🚀 Starting MemU SDK example...\n');

    // Example 1: Memorize a text conversation
    console.log('📝 Memorizing text conversation...');
    const textResponse = await client.memorizeConversation(
      "User: I love hiking in the mountains.\nAssistant: That sounds wonderful! What's your favorite trail?",
      'user',
      'Johnson',
      'assistant',
      'Assistant',
      new Date().toISOString()
    );

    console.log(`✅ Task started: ${textResponse.taskId}`);
    console.log(`   Status: ${textResponse.status}`);
    console.log(`   Message: ${textResponse.message}`);
    
    sleep(2000);
    // Wait for task completion
    await waitForTaskCompletion(client, textResponse.taskId);
    console.log();

    // Example 2: Memorize a structured conversation
    console.log('💬 Memorizing structured conversation...');
    const structuredResponse = await client.memorizeConversation(
      [
        { role: 'user', content: 'What gear do I need for winter hiking?' },
        { role: 'assistant', content: 'For winter hiking, you\'ll need insulated boots, layered clothing, and safety equipment like crampons and a headlamp.' }
      ],
      'user',
      'Johnson',
      'assistant',
      'Assistant'
    );

    console.log(`✅ Task started: ${structuredResponse.taskId}`);
    console.log(`   Status: ${structuredResponse.status}`);
    
    // Wait for task completion
    await waitForTaskCompletion(client, structuredResponse.taskId);
    console.log();

    // Example 3: Check task status
    console.log('⏳ Checking task status...');
    const status = await client.getTaskStatus(textResponse.taskId);
    console.log(`📊 Task ${status.taskId}:`);
    console.log(`   Status: ${status.status}`);
    if (status.progress) {
      console.log(`   Progress: ${JSON.stringify(status.progress)}`);
    }
    if (status.error) {
      console.log(`   Error: ${status.error}`);
    }
    console.log();

    // Example 4: Retrieve default categories
    console.log('📂 Retrieving default categories...');
    const categories = await client.retrieveDefaultCategories({
      userId: 'user',
      agentId: 'assistant',
      includeInactive: false
    });

    console.log(`📋 Found ${categories.totalCategories} categories:`);
    categories.categories.forEach((category, index) => {
      console.log(`   ${index + 1}. ${category.categoryName} (${category.memoryCount} memories)`);
      console.log(`      Type: ${category.categoryType}`);
      console.log(`      Active: ${category.isActive ? '✅' : '❌'}`);
    });
    console.log();

    // Example 5: Search for related memories
    console.log('🔍 Searching for related memories...');
    const relatedMemories = await client.retrieveRelatedMemoryItems({
      userId: 'user',
      agentId: 'assistant',
      query: 'hiking equipment',
      topK: 5,
      minSimilarity: 0.3
    });

    console.log(`🎯 Found ${relatedMemories.totalFound} related memories:`);
    relatedMemories.relatedMemories.forEach((memory, index) => {
      console.log(`   ${index + 1}. Score: ${memory.similarityScore.toFixed(3)}`);
      console.log(`      Category: ${memory.memory.category}`);
      console.log(`      Content: ${memory.memory.content.substring(0, 100)}...`);
      console.log(`      Date: ${memory.memory.happenedAt}`);
    });
    console.log();

    // Example 6: Search for clustered categories
    console.log('🗂️ Searching for clustered categories...');
    const clusteredCategories = await client.retrieveRelatedClusteredCategories({
      userId: 'user',
      agentId: 'assistant',
      categoryQuery: 'outdoor activities',
      topK: 3,
      minSimilarity: 0.4
    });

    console.log(`📚 Found ${clusteredCategories.totalCategoriesFound} clustered categories:`);
    clusteredCategories.clusteredCategories.forEach((cluster, index) => {
      console.log(`   ${index + 1}. ${cluster.categoryName} (Score: ${cluster.similarityScore.toFixed(3)})`);
      console.log(`      Memories: ${cluster.memoryCount}`);
      cluster.memories.slice(0, 2).forEach(memory => {
        console.log(`        - ${memory.content.substring(0, 80)}...`);
      });
    });

    // Example 7: Delete memories
    console.log('🗑️ Deleting memories examples...');
    
    // Delete memories for a specific user and agent
    console.log('Deleting memories for user and assistant...');
    const deleteResponse = await client.deleteMemories({
      userId: 'user',
      agentId: 'assistant'
    });
    console.log(`✅ Success: ${deleteResponse.success}`);
    console.log(`   Deleted ${deleteResponse.deletedCount} memories`);
    console.log();

    // Example: Delete all memories for a user (without specifying agent)
    console.log('Deleting all memories for user...');
    const deleteAllResponse = await client.deleteMemories({
      userId: 'user'
    });
    console.log(`✅ Success: ${deleteAllResponse.success}`);
    console.log(`   Deleted ${deleteAllResponse.deletedCount} memories`);
    console.log();

    console.log('\n✨ Example completed successfully!');

  } catch (error) {
    console.error('❌ Error occurred:', error.message);
    if (error.statusCode) {
      console.error(`   Status Code: ${error.statusCode}`);
    }
    if (error.responseData) {
      console.error(`   Response Data: ${JSON.stringify(error.responseData)}`);
    }
  }
}

// Export the function
export { basicExample };

// Run the example
basicExample().catch(console.error);
