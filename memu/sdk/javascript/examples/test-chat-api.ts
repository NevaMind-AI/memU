/*
 * Test script for chat API (TypeScript version)
 *
 * This script tests the chat API endpoint:
 * - POST /api/v2/chat - Send a chat message and get response
 *
 * Usage:
 *   MEMU_API_KEY=your_api_key node --import tsx examples/test-chat-api.ts
 */

import * as readline from 'node:readline/promises'

type JsonValue = Record<string, any>

class ChatAPITester {
  private baseUrl: string
  private apiPrefix: string
  private bearerToken: string

  private testUserId: string
  private testAgentId: string

  constructor(baseUrl: string = 'https://memu-dev.tail13fa45.ts.net/u/wu/be') {
    this.baseUrl = baseUrl
    this.apiPrefix = '/api/v2'
    // Prefer env var; fallback to placeholder
    this.bearerToken = process.env.MEMU_API_KEY ?? 'your-api-key-here'

    this.testUserId = 'test_user_chat_0926'
    this.testAgentId = 'test_agent_chat_0926'
  }

  async testChatEndpoint(payload?: JsonValue): Promise<JsonValue> {
    const finalPayload = payload ?? {
      user_id: this.testUserId,
      agent_id: this.testAgentId,
      message: 'Hi, is everything going well?',
      // max_context_tokens: 1000,
      // kwargs: { temperature: 0.7 },
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (this.bearerToken)
      headers.Authorization = `Bearer ${this.bearerToken}`

    try {
      const url = `${this.baseUrl}${this.apiPrefix}/chat`
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(finalPayload),
      })

      if (res.ok) {
        const result = (await res.json()) as JsonValue
        this.printChatResponse(result)
        return result
      } else {
        const text = await res.text()
        console.error(`❌ Request failed (${res.status}): ${text}`)
        return { error: text, status_code: res.status }
      }
    }
    catch (e) {
      console.error(`❌ Exception occurred: ${e}`)
      return { error: String(e) }
    }
  }

  private printChatResponse(result: JsonValue): void {
    if ('response' in result)
      console.log(`🤖 ${result.response}`)
    else if ('message' in result)
      console.log(`💬 ${result.message}`)
    else
      console.log(`📋 ${JSON.stringify(result, null, 2)}`)
  }

  async testWithCustomPayload(customPayload: JsonValue): Promise<JsonValue> {
    return this.testChatEndpoint(customPayload)
  }

  async testServerHealth(): Promise<boolean> {
    try {
      const healthUrl = `${this.baseUrl}/health/web`
      const res = await fetch(healthUrl, { method: 'GET', signal: AbortSignal.timeout(10000) })
      return res.status === 200
    }
    catch {
      return false
    }
  }

  async runBasicTest(): Promise<void> {
    await this.testChatEndpoint()
  }

  async runInteractiveTest(): Promise<void> {
    console.log('💬 Interactive chat mode (type "exit" to quit)')

    const rl = readline.createInterface({ input: process.stdin, output: process.stdout })
    try {
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const message = (await rl.question('\n> ')).trim()
        if (!message)
          continue
        if (['exit', 'quit', 'q'].includes(message.toLowerCase()))
          break

        const payload: JsonValue = {
          user_id: this.testUserId,
          agent_id: this.testAgentId,
          message,
        }
        await this.testChatEndpoint(payload)
      }
    }
    catch (e) {
      console.error(`❌ Error: ${e}`)
    }
    finally {
      rl.close()
    }
  }
}

async function main(): Promise<void> {
  const tester = new ChatAPITester()
  // await tester.runBasicTest()
  await tester.runInteractiveTest()
}

main().catch(err => {
  console.error(err)
  process.exitCode = 1
})


