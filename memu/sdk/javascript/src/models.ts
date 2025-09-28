/**
 * MemU SDK Data Models
 *
 * Defines request and response models for MemU API interactions.
 */

/**
 * Category memory items model
 */
export interface CategoryMemoryItems {
  /** Memory items */
  memories: MemoryItem[]
  /** Number of memory items */
  memoryCount: number
}

/**
 * Category response model
 */
export interface CategoryResponse {
  /** Agent ID */
  agentId?: string
  /** Category description */
  description?: string
  /** Memory items in this category */
  memoryItems?: CategoryMemoryItems | null
  /** Category name */
  name: string
  /** Memory summarization for this category */
  summary?: null | string
  /** Category type */
  type: string
  /** User ID */
  userId?: string
}

/**
 * Clustered category with memories
 */
export interface ClusteredCategory {
  /** Agent identifier */
  agentId?: string
  /** Memories in this category */
  memories?: MemoryItem[] | null
  /** Number of memories in category */
  memoryCount?: null | number
  /** Category name */
  name: string
  /** Similarity score */
  similarityScore: number
  /** Memory summarization for this category */
  summary?: null | string
  /** User identifier */
  userId?: string
}

/**
 * Request model for default categories API
 */
export interface DefaultCategoriesRequest {
  /** Agent ID */
  agentId?: string
  /** User ID */
  userId: string
  /** Request also raw memory items */
  wantMemoryItems?: boolean
}

/**
 * Response model for default categories API
 */
export interface DefaultCategoriesResponse {
  /** List of category objects */
  categories: CategoryResponse[]
  /** Total number of categories */
  totalCategories: number
}

// ========== New Retrieve API Models ==========

/**
 * Request model for delete memory API
 */
export interface DeleteMemoryRequest {
  /** Agent identifier (optional, delete all user memories if not provided) */
  agentId?: string
  /** User identifier */
  userId: string
}

/**
 * Response model for delete memory API
 */
export interface DeleteMemoryResponse {
  /** Number of memories deleted */
  deletedCount?: number
  /** Operation success status */
  success: boolean
}

/**
 * Error detail model for validation errors
 */
export interface ErrorDetail {
  /** Error location */
  loc: any[]
  /** Error message */
  msg: string
  /** Error type */
  type: string
}

/**
 * Request model for memorize conversation API
 * Either conversationText or conversation must be provided
 */
export interface MemorizeRequest {
  /** Agent identifier */
  agentId: string
  /** Agent display name */
  agentName: string
  /** Conversation to memorize in role-content format */
  conversation?: Array<{ content: string, role: string, time?: string }>
  /** Conversation to memorize in plain text format */
  conversationText?: string
  /** Session date in ISO 8601 format */
  sessionDate?: string
  /** User identifier */
  userId: string
  /** User display name */
  userName: string
}

/**
 * Response model for memorize conversation API
 */
export interface MemorizeResponse {
  /** Response message */
  message: string
  /** Task status */
  status: string
  /** Celery task ID for tracking */
  taskId: string
}

/**
 * Response model for memorize task status API
 */
export interface MemorizeTaskStatusResponse {
  /** Detail information */
  detailInfo?: string
  /** Task status (e.g., PENDING, SUCCESS, FAILURE) */
  status: string
  /** Celery task ID */
  taskId: string
}

/**
 * Request model for memorize task summary ready API
 */
export interface MemorizeTaskSummaryReadyRequest {
  /** Category group to query */
  group?: string
}

/**
 * Response model for memorize task summary ready API
 */
export interface MemorizeTaskSummaryReadyResponse {
  /** Whether all summaries are ready */
  allReady: boolean
  /** Whether each category is ready */
  categoryReady: Record<string, boolean>
}

/**
 * Memory item model
 */
export interface MemoryItem {
  /** Memory category */
  category: string
  /** Memory content */
  content: string
  /** When the memory was created */
  createdAt: Date
  /** When the memory happened */
  happenedAt: Date
  /** Memory identifier */
  memoryId: string
  /** When the memory was last updated */
  updatedAt: Date
}

/**
 * Request model for related clustered categories API
 */
export interface RelatedClusteredCategoriesRequest {
  /** Agent identifier */
  agentId?: string
  /** Category search query */
  categoryQuery: string
  /** Minimum similarity threshold */
  minSimilarity?: number
  /** Number of top categories to return */
  topK?: number
  /** User identifier */
  userId: string
  /** Request summary instead of raw memory items */
  wantSummary?: boolean
}

/**
 * Response model for related clustered categories API
 */
export interface RelatedClusteredCategoriesResponse {
  /** Original category query */
  categoryQuery: string
  /** List of clustered categories */
  clusteredCategories: ClusteredCategory[]
  /** Search parameters used */
  searchParams: Record<string, any>
  /** Total categories found */
  totalCategoriesFound: number
}

// ========== Delete Memory API Models ==========

/**
 * Related memory with similarity score
 */
export interface RelatedMemory {
  /** Agent identifier */
  agentId?: string
  /** Memory item */
  memory: MemoryItem
  /** Similarity score */
  similarityScore: number
  /** User identifier */
  userId?: string
}

/**
 * Request model for related memory items API
 */
export interface RelatedMemoryItemsRequest {
  /** Agent identifier */
  agentId?: string
  /** Categories to include in search */
  includeCategories?: string[]
  /** Minimum similarity threshold */
  minSimilarity?: number
  /** Search query */
  query: string
  /** Number of top results to return */
  topK?: number
  /** User identifier */
  userId: string
}

// ========== Task Summary Ready API Models ==========

/**
 * Response model for related memory items API
 */
export interface RelatedMemoryItemsResponse {
  /** Original search query */
  query: string
  /** List of related memories */
  relatedMemories: RelatedMemory[]
  /** Search parameters used */
  searchParams: Record<string, any>
  /** Total number of memories found */
  totalFound: number
}

/**
 * Validation error response model
 */
export interface ValidationError {
  /** List of validation errors */
  detail: ErrorDetail[]
}

// ========== Chat API Models ==========

/**
 * Request model for chat API
 */
export interface ChatRequest {
  /** User identifier */
  userId: string
  /** User display name */
  userName?: string
  /** Agent identifier */
  agentId: string
  /** Agent display name */
  agentName?: string
  /** User message content */
  message: string
  /** System message content */
  system?: string
  /** Chat LLM model */
  model?: string
  // Now configure the maximum context token in the web platform.
  // /** Maximum tokens for final chat prompt (current query + short term context + long term memory), correspond to ChatTokenUsage.promptTokens */
  // maxContextTokens?: number
  /** Additional parameters for LLM */
  kwargs?: Record<string, any>
}

/**
 * Token usage breakdown for chat response
 */
export interface ChatTokenUsageBreakdown {
  /** Tokens used for current query */
  currentQuery?: number
  /** Tokens used for short term context */
  shortTermContext?: number
  /** Tokens used for user profile */
  userProfile?: number
  /** Tokens used for retrieved memory */
  retrievedMemory?: number
}

/**
 * Token usage information for chat response
 */
export interface ChatTokenUsage {
  /** Total prompt tokens */
  promptTokens: number
  /** Breakdown of prompt tokens */
  promptTokensBreakdown?: ChatTokenUsageBreakdown
  /** Completion tokens */
  completionTokens: number
  /** Total tokens */
  totalTokens: number
}

/**
 * Response model for chat API
 */
export interface ChatResponse {
  /** AI response message */
  message: string
  /** Token usage information */
  chatTokenUsage: ChatTokenUsage
}
