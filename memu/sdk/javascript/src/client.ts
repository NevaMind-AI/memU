/**
 * MemU SDK HTTP Client
 * 
 * Provides HTTP client for interacting with MemU API services.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import {
  MemuAPIException,
  MemuAuthenticationException,
  MemuConnectionException,
  MemuValidationException,
} from './exceptions';
import {
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
} from './models';

/**
 * Configuration options for MemuClient
 */
export interface MemuClientConfig {
  /** Base URL for MemU API server */
  baseUrl?: string;
  /** API key for authentication */
  apiKey?: string;
  /** Request timeout in milliseconds */
  timeout?: number;
  /** Maximum number of retries for failed requests */
  maxRetries?: number;
  /** Additional axios configuration */
  axiosConfig?: AxiosRequestConfig;
}

/**
 * HTTP client for MemU API services
 */
export class MemuClient {
  private baseUrl: string;
  private apiKey: string;
  private timeout: number;
  private maxRetries: number;
  private client: AxiosInstance;

  /**
   * Initialize MemU SDK client
   * 
   * @param config Client configuration options
   */
  constructor(config: MemuClientConfig = {}) {
    this.baseUrl = config.baseUrl || globalThis.process?.env?.MEMU_API_BASE_URL || 'http://localhost:8000';
    this.apiKey = config.apiKey || globalThis.process?.env?.MEMU_API_KEY || '';
    this.timeout = config.timeout || 30000; // 30 seconds
    this.maxRetries = config.maxRetries || 3;

    if (!this.baseUrl) {
      throw new Error(
        'baseUrl is required. Set MEMU_API_BASE_URL environment variable or pass baseUrl in config.'
      );
    }

    if (!this.apiKey) {
      throw new Error(
        'apiKey is required. Set MEMU_API_KEY environment variable or pass apiKey in config.'
      );
    }

    // Ensure base_url ends with /
    if (!this.baseUrl.endsWith('/')) {
      this.baseUrl += '/';
    }

    // Configure axios client
    const axiosConfig: AxiosRequestConfig = {
      baseURL: this.baseUrl,
      timeout: this.timeout,
      headers: {
        'User-Agent': 'MemU-JavaScript-SDK/0.1.3',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      ...config.axiosConfig,
    };

    this.client = axios.create(axiosConfig);

    console.log(`MemU SDK client initialized with baseUrl: ${this.baseUrl}`);
  }

  /**
   * Make HTTP request with error handling and retries
   * 
   * @param config Axios request configuration
   * @returns Response data
   */
  private async makeRequest<T = any>(config: AxiosRequestConfig): Promise<T> {
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        console.log(`Making ${config.method?.toUpperCase()} request to ${config.url} (attempt ${attempt + 1})`);

        const response: AxiosResponse<T> = await this.client.request(config);

        // Handle HTTP status codes
        if (response.status === 200) {
          return response.data;
        } else {
          throw new MemuAPIException(
            `API request failed with status ${response.status}`,
            response.status
          );
        }
      } catch (error) {
        if (axios.isAxiosError(error)) {
          const axiosError = error as AxiosError;

          // Handle specific HTTP status codes
          if (axiosError.response?.status === 422) {
            const errorData = axiosError.response.data;
            throw new MemuValidationException(
              `Validation error: ${JSON.stringify(errorData)}`,
              axiosError.response.status,
              errorData as Record<string, any>
            );
          } else if (axiosError.response?.status === 401) {
            throw new MemuAuthenticationException(
              'Authentication failed. Check your API key.',
              axiosError.response.status
            );
          } else if (axiosError.response?.status === 403) {
            throw new MemuAuthenticationException(
              'Access forbidden. Check your API key permissions.',
              axiosError.response.status
            );
          } else if (axiosError.response) {
            // Server responded with error status
            const errorMsg = `API request failed with status ${axiosError.response.status}`;
            const errorData = axiosError.response.data;
            throw new MemuAPIException(
              `${errorMsg}: ${JSON.stringify(errorData)}`,
              axiosError.response.status
            );
          } else if (axiosError.request) {
            // Request was made but no response received
            if (attempt === this.maxRetries) {
              throw new MemuConnectionException(
                `Connection error after ${this.maxRetries + 1} attempts: ${axiosError.message}`
              );
            } else {
              console.warn(`Request failed (attempt ${attempt + 1}), retrying: ${axiosError.message}`);
              continue;
            }
          } else {
            // Something else happened
            throw new MemuAPIException(`Request setup error: ${axiosError.message}`);
          }
        } else {
          // Non-Axios error (shouldn't happen in normal cases)
          if (attempt === this.maxRetries) {
            throw new MemuConnectionException(
              `Unexpected error after ${this.maxRetries + 1} attempts: ${error}`
            );
          } else {
            console.warn(`Unexpected error (attempt ${attempt + 1}), retrying: ${error}`);
            continue;
          }
        }
      }
    }

    // This should never be reached, but TypeScript requires it
    throw new MemuConnectionException('Maximum retries exceeded');
  }

  /**
   * Convert camelCase object keys to snake_case for API compatibility
   * 
   * @param obj Object to convert
   * @returns Object with snake_case keys
   */
  private toSnakeCase(obj: Record<string, any>): Record<string, any> {
    const result: Record<string, any> = {};
    
    for (const [key, value] of Object.entries(obj)) {
      const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
      result[snakeKey] = value;
    }
    
    return result;
  }

  /**
   * Convert snake_case object keys to camelCase for JavaScript compatibility
   * 
   * @param obj Object to convert
   * @returns Object with camelCase keys
   */
  private toCamelCase(obj: any): any {
    if (obj === null || typeof obj !== 'object') {
      return obj;
    }

    if (Array.isArray(obj)) {
      return obj.map(item => this.toCamelCase(item));
    }

    const result: Record<string, any> = {};
    
    for (const [key, value] of Object.entries(obj)) {
      const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      result[camelKey] = this.toCamelCase(value);
    }
    
    return result;
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
    conversation: string | Array<{ role: string; content: string }>,
    userId: string,
    userName: string,
    agentId: string,
    agentName: string,
    sessionDate?: string
  ): Promise<MemorizeResponse> {
    try {
      const conversationData: Partial<MemorizeRequest> = {};
      
      if (typeof conversation === 'string') {
        conversationData.conversationText = conversation;
      } else if (Array.isArray(conversation)) {
        conversationData.conversation = conversation;
      } else {
        throw new Error(
          'Conversation must be a string for flatten text, or an array of objects for structured messages'
        );
      }

      const currentDate = sessionDate || new Date().toISOString();

      // Create request data
      const requestData: MemorizeRequest = {
        ...conversationData,
        userId,
        userName,
        agentId,
        agentName,
        sessionDate: currentDate,
      };

      console.log(`Starting memorization for user ${userId} and agent ${agentId}`);

      // Convert to snake_case for API
      const apiRequestData = this.toSnakeCase(requestData as Record<string, any>);

      // Make API request
      const responseData = await this.makeRequest<any>({
        method: 'POST',
        url: 'api/v1/memory/memorize',
        data: apiRequestData,
      });

      // Convert response to camelCase
      const response = this.toCamelCase(responseData) as MemorizeResponse;
      console.log(`Memorization task started: ${response.taskId}`);

      return response;
    } catch (error) {
      if (error instanceof MemuValidationException || 
          error instanceof MemuAPIException || 
          error instanceof MemuConnectionException ||
          error instanceof MemuAuthenticationException) {
        throw error;
      }
      throw new MemuValidationException(`Request validation failed: ${error}`);
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
      console.log(`Getting status for task: ${taskId}`);

      // Make API request
      const responseData = await this.makeRequest<any>({
        method: 'GET',
        url: `api/v1/memory/memorize/status/${taskId}`,
      });

      // Convert response to camelCase
      const response = this.toCamelCase(responseData) as MemorizeTaskStatusResponse;
      console.log(`Task ${taskId} status: ${response.status}`);

      return response;
    } catch (error) {
      if (error instanceof MemuValidationException || 
          error instanceof MemuAPIException || 
          error instanceof MemuConnectionException ||
          error instanceof MemuAuthenticationException) {
        throw error;
      }
      throw new MemuValidationException(`Response validation failed: ${error}`);
    }
  }

  /**
   * Get the summary ready status of a memorization task
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
      };

      console.log(`Getting summary ready status for task: ${taskId}`);

      // Convert to snake_case for API
      const apiRequestData = this.toSnakeCase(requestData as Record<string, any>);

      // Make API request
      const responseData = await this.makeRequest<any>({
        method: 'POST',
        url: `api/v1/memory/memorize/status/${taskId}/summary`,
        data: apiRequestData,
      });

      // Convert response to camelCase
      const response = this.toCamelCase(responseData) as MemorizeTaskSummaryReadyResponse;
      console.log(`Task ${taskId} summary ready: ${response.allReady}`);

      return response;
    } catch (error) {
      if (error instanceof MemuValidationException || 
          error instanceof MemuAPIException || 
          error instanceof MemuConnectionException ||
          error instanceof MemuAuthenticationException) {
        throw error;
      }
      throw new MemuValidationException(`Response validation failed: ${error}`);
    }
  }

  /**
   * Retrieve default categories for a project
   * 
   * @param options Request options
   * @returns Default categories information
   */
  async retrieveDefaultCategories(options: {
    userId: string;
    agentId?: string;
    includeInactive?: boolean;
    wantSummary?: boolean;
  }): Promise<DefaultCategoriesResponse> {
    try {
      // Create request data
      const requestData: DefaultCategoriesRequest = {
        userId: options.userId,
        ...(options.agentId && { agentId: options.agentId }),
        includeInactive: options.includeInactive || false,
        wantSummary: options.wantSummary || true,
      };

      // Convert to snake_case for API
      const apiRequestData = this.toSnakeCase(requestData as Record<string, any>);

      // Make API request
      const responseData = await this.makeRequest<any>({
        method: 'POST',
        url: 'api/v1/memory/retrieve/default-categories',
        data: apiRequestData,
      });

      // Convert response to camelCase
      const response = this.toCamelCase(responseData) as DefaultCategoriesResponse;
      console.log(`Retrieved ${response.totalCategories} categories`);

      return response;
    } catch (error) {
      if (error instanceof MemuValidationException || 
          error instanceof MemuAPIException || 
          error instanceof MemuConnectionException ||
          error instanceof MemuAuthenticationException) {
        throw error;
      }
      throw new MemuValidationException(`Request validation failed: ${error}`);
    }
  }

  /**
   * Retrieve related memory items for a user query
   * 
   * @param options Request options
   * @returns Related memory items
   */
  async retrieveRelatedMemoryItems(options: {
    userId: string;
    agentId?: string;
    query: string;
    topK?: number;
    minSimilarity?: number;
    includeCategories?: string[];
  }): Promise<RelatedMemoryItemsResponse> {
    try {
      // Create request data
      const requestData: RelatedMemoryItemsRequest = {
        userId: options.userId,
        ...(options.agentId && { agentId: options.agentId }),
        query: options.query,
        topK: options.topK || 10,
        minSimilarity: options.minSimilarity || 0.3,
        ...(options.includeCategories && { includeCategories: options.includeCategories }),
      };

      console.log(`Retrieving related memories for user ${options.userId}, query: '${options.query}'`);

      // Convert to snake_case for API
      const apiRequestData = this.toSnakeCase(requestData as Record<string, any>);

      // Make API request
      const responseData = await this.makeRequest<any>({
        method: 'POST',
        url: 'api/v1/memory/retrieve/related-memory-items',
        data: apiRequestData,
      });

      // Convert response to camelCase
      const response = this.toCamelCase(responseData) as RelatedMemoryItemsResponse;
      console.log(`Retrieved ${response.totalFound} related memories`);

      return response;
    } catch (error) {
      if (error instanceof MemuValidationException || 
          error instanceof MemuAPIException || 
          error instanceof MemuConnectionException ||
          error instanceof MemuAuthenticationException) {
        throw error;
      }
      throw new MemuValidationException(`Request validation failed: ${error}`);
    }
  }

  /**
   * Retrieve related clustered categories for a user
   * 
   * @param options Request options
   * @returns Related clustered categories
   */
  async retrieveRelatedClusteredCategories(options: {
    userId: string;
    agentId?: string;
    categoryQuery: string;
    topK?: number;
    minSimilarity?: number;
  }): Promise<RelatedClusteredCategoriesResponse> {
    try {
      // Create request data
      const requestData: RelatedClusteredCategoriesRequest = {
        userId: options.userId,
        ...(options.agentId && { agentId: options.agentId }),
        categoryQuery: options.categoryQuery,
        topK: options.topK || 5,
        minSimilarity: options.minSimilarity || 0.3,
      };

      console.log(
        `Retrieving clustered categories for user ${options.userId}, query: '${options.categoryQuery}'`
      );

      // Convert to snake_case for API
      const apiRequestData = this.toSnakeCase(requestData as Record<string, any>);

      // Make API request
      const responseData = await this.makeRequest<any>({
        method: 'POST',
        url: 'api/v1/memory/retrieve/related-clustered-categories',
        data: apiRequestData,
      });

      // Convert response to camelCase
      const response = this.toCamelCase(responseData) as RelatedClusteredCategoriesResponse;
      console.log(`Retrieved ${response.totalCategoriesFound} clustered categories`);

      return response;
    } catch (error) {
      if (error instanceof MemuValidationException || 
          error instanceof MemuAPIException || 
          error instanceof MemuConnectionException ||
          error instanceof MemuAuthenticationException) {
        throw error;
      }
      throw new MemuValidationException(`Request validation failed: ${error}`);
    }
  }

  /**
   * Delete memories for a given user. If agentId is provided, delete only that agent's memories; 
   * otherwise delete all memories for the user within the project.
   * 
   * @param options Request options
   * @returns Response with deletion status and count
   */
  async deleteMemories(options: {
    userId: string;
    agentId?: string;
  }): Promise<DeleteMemoryResponse> {
    try {
      // Create request data
      const requestData: DeleteMemoryRequest = {
        userId: options.userId,
        ...(options.agentId && { agentId: options.agentId }),
      };

      console.log(
        `Deleting memories for user ${options.userId}` +
        (options.agentId ? ` and agent ${options.agentId}` : ' (all agents)')
      );

      // Convert to snake_case for API
      const apiRequestData = this.toSnakeCase(requestData as Record<string, any>);

      // Make API request
      const responseData = await this.makeRequest<any>({
        method: 'POST',
        url: 'api/v1/memory/delete',
        data: apiRequestData,
      });

      // Convert response to camelCase
      const response = this.toCamelCase(responseData) as DeleteMemoryResponse;
      console.log(
        `Successfully deleted memories: ${response.deletedCount} memories deleted`
      );

      return response;
    } catch (error) {
      if (error instanceof MemuValidationException || 
          error instanceof MemuAPIException || 
          error instanceof MemuConnectionException ||
          error instanceof MemuAuthenticationException) {
        throw error;
      }
      throw new MemuValidationException(`Request validation failed: ${error}`);
    }
  }
}
