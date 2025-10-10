/**
 * Example usage of MemU SDK with streaming support (JavaScript)
 */

import { MemuClient } from '../dist/index.js'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Initialize the client
const client = new MemuClient({
  apiKey: 'your-api-key-here',
  baseUrl: 'https://api.memu.so',
})

async function nonStreamingExample() {
  console.log('=== Non-streaming Chat Example ===')
  
  try {
    const request = {
      userId: 'user123',
      userName: 'John Doe',
      agentId: 'agent456',
      agentName: 'AI Assistant',
      message: 'Hello, how are you today?',
      system: 'You are a helpful assistant.',
      model: 'gpt-4.1',
      stream: false, // Explicit non-streaming
    }

    const response = await client.chat(request)
    console.log('Response:', response.message)
    console.log('Token usage:', response.chatTokenUsage)
  } catch (error) {
    console.error('Error:', error)
  }
}

async function streamingExample() {
  console.log('\n=== Streaming Chat Example ===')
  
  try {
    const request = {
      userId: 'user123',
      userName: 'John Doe',
      agentId: 'agent456',
      agentName: 'AI Assistant',
      message: 'Tell me a story about a brave knight.',
      system: 'You are a creative storyteller.',
      model: 'gpt-4.1',
      stream: true, // Enable streaming
    }

    const streamResponse = await client.chat(request)
    
    let fullMessage = ''
    
    // Cast to AsyncGenerator for streaming response
    for await (const chunk of streamResponse) {
      if (chunk.error) {
        console.error('Stream error:', chunk.error)
        break
      }
      
      if (chunk.message) {
        process.stdout.write(chunk.message)
        fullMessage += chunk.message
      }
      
      if (chunk.streamEnded) {
        console.log('\n\nStream ended.')
        if (chunk.chatTokenUsage) {
          console.log('Final token usage:', chunk.chatTokenUsage)
        }
        break
      }
    }
    
    console.log(`\nFull message received: ${fullMessage.length} characters`)
  } catch (error) {
    console.error('Stream error:', error)
  }
}

async function main() {
  // Run non-streaming example
  await nonStreamingExample()
  
  // Wait a bit
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Run streaming example
  await streamingExample()
}

// Run the examples if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error)
}

export { nonStreamingExample, streamingExample }
