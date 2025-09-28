/* eslint-disable no-console */
/**
 * MemU SDK HTTP Client
 *
 * Provides HTTP client for interacting with MemU API services.
 */

import type {
  ChatRequest,
  ChatResponse,
  DefaultCategoriesRequest,
  DefaultCategoriesResponse,
  DeleteMemoryRequest,
  DeleteMemoryResponse,
  MemorizeRequest,
  MemorizeResponse,
  MemorizeTaskStatusResponse,
  MemorizeTaskSummaryReadyRequest,
  MemorizeTaskSummaryReadyResponse,
  RelatedClusteredCategoriesRequest,
  RelatedClusteredCategoriesResponse,
  RelatedMemoryItemsRequest,
  RelatedMemoryItemsResponse,
} from './models'

import {
  MemuAPIException,
  MemuAuthenticationException,
  MemuConnectionException,
  MemuValidationException,
} from './exceptions'

/**
 * Configuration options for MemuClient
 */
export interface MemuClientConfig {
  /** API key for authentication */
  apiKey?: string
  /** Base URL for MemU API server */
  baseUrl?: string
  /** Maximum number of retries for failed requests */
  maxRetries?: number
  /** Request timeout in milliseconds */
  timeout?: number
}

/**
 * HTTP client for MemU API services
 */
export class MemuClient {
  private apiKey: string
  private baseUrl: string
  private maxRetries: number
  private timeout: number

  /**
   * Initialize MemU SDK client
   *
   * @param config Client configuration options
   */
  constructor(config: MemuClientConfig = {}) {
    // eslint-disable-next-line node/prefer-global/process
    this.baseUrl = config.baseUrl ?? globalThis.process?.env?.MEMU_API_BASE_URL ?? 'http://localhost:8000'
    // eslint-disable-next-line node/prefer-global/process
    this.apiKey = config.apiKey ?? globalThis.process?.env?.MEMU_API_KEY ?? ''
    this.timeout = config.timeout ?? 30000 // 30 seconds
    this.maxRetries = config.maxRetries ?? 3

    if (!this.baseUrl) {
      throw new Error(
        'baseUrl is required. Set MEMU_API_BASE_URL environment variable or pass baseUrl in config.',
      )
    }

    if (!this.apiKey) {
      throw new Error(
        'apiKey is required. Set MEMU_API_KEY environment variable or pass apiKey in config.',
      )
    }

    // Ensure base_url ends with /
    if (!this.baseUrl.endsWith('/'))
      this.baseUrl += '/'

    console.log(`MemU SDK client initialized with baseUrl: ${this.baseUrl}`)
  }

  /**
   * Delete memories for a given user. If agentId is provided, delete only that agent's memories;
   * otherwise delete all memories for the user within the project.
   *
   * @param options Request options
   * @returns Response with deletion status and count
   */
  async deleteMemories(options: {
    agentId?: string
    userId: string
  }): Promise<DeleteMemoryResponse> {
    try {
      // Create request data
      const requestData: DeleteMemoryRequest = {
        userId: options.userId,
        ...(options.agentId != null && { agentId: options.agentId }),
      }

      console.log(
        `Deleting memories for user ${options.userId}${
        // eslint-disable-next-line sonarjs/no-nested-template-literals
          options.agentId != null ? ` and agent ${options.agentId}` : ' (all agents)'}`,
      )

      // Convert to snake_case for API
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const apiRequestData = this.toSnakeCase(requestData as unknown as Record<string, unknown>)

      // Make API request
      const responseData = await this.makeRequest<unknown>('api/v2/memory/delete', {
        body: JSON.stringify(apiRequestData),
        method: 'POST',
      })

      // Convert response to camelCase
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const response = this.toCamelCase(responseData as Record<string, unknown>) as unknown as DeleteMemoryResponse
      console.log(
        `Successfully deleted memories: ${response.deletedCount} memories deleted`,
      )

      return response
    }
    catch (error) {
      if (error instanceof MemuValidationException
        || error instanceof MemuAPIException
        || error instanceof MemuConnectionException
        || error instanceof MemuAuthenticationException) {
        throw error
      }
      // eslint-disable-next-line ts/restrict-template-expressions
      throw new MemuValidationException(`Request validation failed: ${error}`)
    }
  }

  /**
   * Get the status of a memorization task
   *
   * @param taskId Task identifier returned from memorizeConversation
   * @returns Task status, progress, and results
   */
  async getTaskStatus(taskId: string): Promise<MemorizeTaskStatusResponse> {
    try {
      console.log(`Getting status for task: ${taskId}`)

      // Make API request
      const responseData = await this.makeRequest<unknown>(`api/v2/memory/memorize/status/${taskId}`, {
        method: 'GET',
      })

      // Convert response to camelCase
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const response = this.toCamelCase(responseData as Record<string, unknown>) as unknown as MemorizeTaskStatusResponse
      console.log(`Task ${taskId} status: ${response.status}`)

      return response
    }
    catch (error) {
      if (error instanceof MemuValidationException
        || error instanceof MemuAPIException
        || error instanceof MemuConnectionException
        || error instanceof MemuAuthenticationException) {
        throw error
      }
      // eslint-disable-next-line ts/restrict-template-expressions
      throw new MemuValidationException(`Response validation failed: ${error}`)
    }
  }

  /**
   * Get the summary ready status of a memorization task
   *
   * @deprecated From 0.1.10, summary is always ready when memorization task's status is SUCCESS.
   *
   * @param taskId Task identifier returned from memorizeConversation
   * @param group Category group to query (default: 'basic')
   * @returns Summary ready status for the task
   */
  async getTaskSummaryReady(taskId: string, group: string = 'basic'): Promise<MemorizeTaskSummaryReadyResponse> {
    try {
      // Create request data
      const requestData: MemorizeTaskSummaryReadyRequest = {
        group,
      }

      console.log(`Getting summary ready status for task: ${taskId}`)

      // Convert to snake_case for API
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const apiRequestData = this.toSnakeCase(requestData as unknown as Record<string, unknown>)

      // Make API request
      const responseData = await this.makeRequest<unknown>(`api/v1/memory/memorize/status/${taskId}/summary`, {
        body: JSON.stringify(apiRequestData),
        method: 'POST',
      })

      // Convert response to camelCase
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const response = this.toCamelCase(responseData as Record<string, unknown>) as unknown as MemorizeTaskSummaryReadyResponse
      console.log(`Task ${taskId} summary ready: ${response.allReady}`)

      return response
    }
    catch (error) {
      if (error instanceof MemuValidationException
        || error instanceof MemuAPIException
        || error instanceof MemuConnectionException
        || error instanceof MemuAuthenticationException) {
        throw error
      }
      // eslint-disable-next-line ts/restrict-template-expressions
      throw new MemuValidationException(`Response validation failed: ${error}`)
    }
  }

  /**
   * Start a Celery task to memorize conversation text with agent processing
   *
   * @param conversation Conversation content to memorize, either as a string or a list of objects
   * @param userId User identifier
   * @param userName User display name
   * @param agentId Agent identifier
   * @param agentName Agent display name
   * @param sessionDate Session date in ISO 8601 format (optional)
   * @returns Task ID and status for tracking the memorization process
   */
  async memorizeConversation(
    conversation: Array<{ content: string, role: string }> | string,
    userId: string,
    userName: string,
    agentId: string,
    agentName: string,
    sessionDate?: string,
  ): Promise<MemorizeResponse> {
    try {
      const conversationData: Partial<MemorizeRequest> = {}

      if (typeof conversation === 'string') {
        conversationData.conversationText = conversation
      }
      else if (Array.isArray(conversation)) {
        conversationData.conversation = conversation
      }
      else {
        throw new TypeError(
          'Conversation must be a string for flatten text, or an array of objects for structured messages',
        )
      }

      const currentDate = sessionDate ?? new Date().toISOString()

      // Create request data
      const requestData: MemorizeRequest = {
        ...conversationData,
        agentId,
        agentName,
        sessionDate: currentDate,
        userId,
        userName,
      }

      console.log(`Starting memorization for user ${userId} and agent ${agentId}`)

      // Convert to snake_case for API
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const apiRequestData = this.toSnakeCase(requestData as unknown as Record<string, unknown>)

      // Make API request
      const responseData = await this.makeRequest<unknown>('api/v2/memory/memorize', {
        body: JSON.stringify(apiRequestData),
        method: 'POST',
      })

      // Convert response to camelCase
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const response = this.toCamelCase(responseData as Record<string, unknown>) as unknown as MemorizeResponse
      console.log(`Memorization task started: ${response.taskId}`)

      return response
    }
    catch (error) {
      if (error instanceof MemuValidationException
        || error instanceof MemuAPIException
        || error instanceof MemuConnectionException
        || error instanceof MemuAuthenticationException) {
        throw error
      }
      // eslint-disable-next-line ts/restrict-template-expressions
      throw new MemuValidationException(`Request validation failed: ${error}`)
    }
  }

  /**
   * Retrieve default categories for a project
   *
   * @param options Request options
   * @returns Default categories information
   */
  async retrieveDefaultCategories(options: {
    agentId?: string
    userId: string
    wantMemoryItems?: boolean
  }): Promise<DefaultCategoriesResponse> {
    try {
      // Create request data
      const requestData: DefaultCategoriesRequest = {
        userId: options.userId,
        ...(options.agentId != null && { agentId: options.agentId }),
        wantMemoryItems: options.wantMemoryItems || false,
      }

      // Convert to snake_case for API
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const apiRequestData = this.toSnakeCase(requestData as unknown as Record<string, unknown>)

      // Make API request
      const responseData = await this.makeRequest<unknown>('api/v2/memory/retrieve/default-categories', {
        body: JSON.stringify(apiRequestData),
        method: 'POST',
      })

      // Convert response to camelCase
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const response = this.toCamelCase(responseData as Record<string, unknown>) as unknown as DefaultCategoriesResponse
      console.log(`Retrieved ${response.totalCategories} categories`)

      return response
    }
    catch (error) {
      if (error instanceof MemuValidationException
        || error instanceof MemuAPIException
        || error instanceof MemuConnectionException
        || error instanceof MemuAuthenticationException) {
        throw error
      }
      // eslint-disable-next-line ts/restrict-template-expressions
      throw new MemuValidationException(`Request validation failed: ${error}`)
    }
  }

  /**
   * Retrieve related memory items for a user query
   *
   * @param options Request options
   * @returns Related memory items
   */
  async retrieveRelatedMemoryItems(options: {
    agentId?: string
    includeCategories?: string[]
    minSimilarity?: number
    query: string
    topK?: number
    userId: string
  }): Promise<RelatedMemoryItemsResponse> {
    try {
      // Create request data
      const requestData: RelatedMemoryItemsRequest = {
        userId: options.userId,
        ...(options.agentId != null && { agentId: options.agentId }),
        minSimilarity: options.minSimilarity ?? 0.3,
        query: options.query,
        topK: options.topK ?? 10,
        ...(options.includeCategories && { includeCategories: options.includeCategories }),
      }

      console.log(`Retrieving related memories for user ${options.userId}, query: '${options.query}'`)

      // Convert to snake_case for API
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const apiRequestData = this.toSnakeCase(requestData as unknown as Record<string, unknown>)

      // Make API request
      const responseData = await this.makeRequest<unknown>('api/v2/memory/retrieve/related-memory-items', {
        body: JSON.stringify(apiRequestData),
        method: 'POST',
      })

      // Convert response to camelCase
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const response = this.toCamelCase(responseData as Record<string, unknown>) as unknown as RelatedMemoryItemsResponse
      console.log(`Retrieved ${response.totalFound} related memories`)

      return response
    }
    catch (error) {
      if (error instanceof MemuValidationException
        || error instanceof MemuAPIException
        || error instanceof MemuConnectionException
        || error instanceof MemuAuthenticationException) {
        throw error
      }
      // eslint-disable-next-line ts/restrict-template-expressions
      throw new MemuValidationException(`Request validation failed: ${error}`)
    }
  }

  /**
   * Send a chat message to the agent with memory-enhanced conversation
   *
   * @param options Request options
   * @returns AI response with token usage information
   */
  async chat(options: {
    agentId: string
    agentName?: string
    kwargs?: Record<string, any>
    message: string
    model?: string
    system?: string
    userId: string
    userName?: string
  }): Promise<ChatResponse> {
    try {
      // Create request data
      const requestData: ChatRequest = {
        userId: options.userId,
        ...(options.userName != null && { userName: options.userName }),
        agentId: options.agentId,
        ...(options.agentName != null && { agentName: options.agentName }),
        message: options.message,
        ...(options.system != null && { system: options.system }),
        ...(options.model != null && { model: options.model }),
        kwargs: options.kwargs ?? {},
      }

      console.log(`Sending chat message for user ${options.userId} and agent ${options.agentId}`)

      // Convert to snake_case for API
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const apiRequestData = this.toSnakeCase(requestData as unknown as Record<string, unknown>)

      // Make API request
      const responseData = await this.makeRequest<unknown>('api/v2/chat', {
        body: JSON.stringify(apiRequestData),
        method: 'POST',
      })

      // Convert response to camelCase
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type
      const response = this.toCamelCase(responseData as Record<string, unknown>) as unknown as ChatResponse
      console.log(`Chat response received: ${response.message.length} characters`)

      return response
    }
    catch (error) {
      if (error instanceof MemuValidationException
        || error instanceof MemuAPIException
        || error instanceof MemuConnectionException
        || error instanceof MemuAuthenticationException) {
        throw error
      }
      // eslint-disable-next-line ts/restrict-template-expressions
      throw new MemuValidationException(`Request validation failed: ${error}`)
    }
  }

  /**
   * Make HTTP request with error handling and retries
   *
   * @param path url path
   * @param config request init
   * @returns Response data
   */
  // eslint-disable-next-line sonarjs/cognitive-complexity
  private async makeRequest<T = unknown>(path: string, config: RequestInit): Promise<T> {
    const url = new URL(path, this.baseUrl)

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        console.log(`Making ${config.method?.toUpperCase()} request to ${url} (attempt ${attempt + 1})`)

        const response = await fetch(url, {
          ...config,
          headers: {
            'Accept': 'application/json',
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
            'User-Agent': 'MemU-JavaScript-SDK/0.2.1',
            ...config.headers,
          },
          signal: this.timeout
            // eslint-disable-next-line sonarjs/no-nested-conditional
            ? config.signal
              ? AbortSignal.any([config.signal, AbortSignal.timeout(this.timeout)])
              : AbortSignal.timeout(this.timeout)
            : undefined,
        })

        // Handle HTTP status codes
        if (response.ok) {
          // eslint-disable-next-line @masknet/type-prefer-return-type-annotation
          return response.json() as T
        }
        else {
          let errorData: Record<string, unknown> | undefined

          try {
            errorData = await response.json() as Record<string, unknown>
          }
          catch {}

          // Handle specific HTTP status codes
          switch (response.status) {
            case 422:
              throw new MemuValidationException(
                `Validation error: ${JSON.stringify(errorData)}`,
                response.status,
                errorData,
              )
            case 401:
              throw new MemuAuthenticationException(
                'Authentication failed. Check your API key.',
                response.status,
              )
            case 403:
              throw new MemuAuthenticationException(
                'Access forbidden. Check your API key permissions.',
                response.status,
              )
            default:
              throw new MemuAPIException(
                `API request failed with status ${response.status}: ${JSON.stringify(errorData)}`,
                response.status,
              )
          }
        }
      }
      catch (error) {
        if (error instanceof TypeError) {
          // Request was made but no response received
          if (attempt === this.maxRetries) {
            throw new MemuConnectionException(
              `Connection error after ${this.maxRetries + 1} attempts: ${error.message}`,
            )
          }
          else {
            console.warn(`Request failed (attempt ${attempt + 1}), retrying: ${error.message}`)
            continue
          }
        }
        else {
          // Non-Fetch error (shouldn't happen in normal cases)
          if (attempt === this.maxRetries) {
            throw new MemuConnectionException(
              // eslint-disable-next-line ts/restrict-template-expressions
              `Unexpected error after ${this.maxRetries + 1} attempts: ${error}`,
            )
          }
          else {
            // eslint-disable-next-line ts/restrict-template-expressions
            console.warn(`Unexpected error (attempt ${attempt + 1}), retrying: ${error}`)
            continue
          }
        }
      }
    }

    // This should never be reached, but TypeScript requires it
    throw new MemuConnectionException('Maximum retries exceeded')
  }

  /**
   * Convert snake_case object keys to camelCase for JavaScript compatibility
   *
   * @param obj Object to convert
   * @returns Object with camelCase keys
   */
  private toCamelCase(obj: Record<string, unknown>): Record<string, unknown> {
    if (obj == null || typeof obj !== 'object')
      return obj

    if (Array.isArray(obj))
      // eslint-disable-next-line @masknet/type-no-force-cast-via-top-type, @masknet/type-prefer-return-type-annotation
      return obj.map(item => this.toCamelCase(item as Record<string, unknown>)) as unknown as Record<string, unknown>

    return Object.fromEntries(
      Object.entries(obj)
        .map(([key, value]) => [key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase()), value]),
    )
  }

  /**
   * Convert camelCase object keys to snake_case for API compatibility
   *
   * @param obj Object to convert
   * @returns Object with snake_case keys
   */
  private toSnakeCase(obj: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(
      Object.entries(obj)
        .map(([key, value]) => [key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`), value]),
    )
  }
}
