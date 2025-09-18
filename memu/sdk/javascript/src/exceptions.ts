/**
 * MemU SDK Exceptions
 *
 * Custom exception classes for MemU SDK operations.
 */

/**
 * Base exception for MemU SDK
 */
export class MemuSDKException extends Error {
  constructor(message: string) {
    super(message)

    this.name = 'MemuSDKException'

    // Maintains proper stack trace for where our error was thrown (only available on V8)
    if ('captureStackTrace' in Error)
      Error.captureStackTrace(this, MemuSDKException)
  }
}

/**
 * Exception for API-related errors
 */
export class MemuAPIException extends MemuSDKException {
  public responseData?: Record<string, unknown>
  public statusCode?: number

  constructor(message: string, statusCode?: number, responseData?: Record<string, unknown>) {
    super(message)

    this.name = 'MemuAPIException'

    if (statusCode !== undefined)
      this.statusCode = statusCode

    if (responseData !== undefined)
      this.responseData = responseData

    if ('captureStackTrace' in Error)
      Error.captureStackTrace(this, MemuAPIException)
  }
}

/**
 * Exception for authentication errors
 */
export class MemuAuthenticationException extends MemuAPIException {
  constructor(message: string, statusCode?: number, responseData?: Record<string, any>) {
    super(message, statusCode, responseData)

    this.name = 'MemuAuthenticationException'

    if ('captureStackTrace' in Error)
      Error.captureStackTrace(this, MemuAuthenticationException)
  }
}

/**
 * Exception for connection errors
 */
export class MemuConnectionException extends MemuSDKException {
  constructor(message: string) {
    super(message)

    this.name = 'MemuConnectionException'

    if ('captureStackTrace' in Error)
      Error.captureStackTrace(this, MemuConnectionException)
  }
}

/**
 * Exception for validation errors
 */
export class MemuValidationException extends MemuAPIException {
  constructor(message: string, statusCode?: number, responseData?: Record<string, any>) {
    super(message, statusCode, responseData)

    this.name = 'MemuValidationException'

    if ('captureStackTrace' in Error)
      Error.captureStackTrace(this, MemuValidationException)
  }
}
