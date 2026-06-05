from __future__ import annotations

from typing import Any

from memu._version import __version__
from memu.server.constants import SUPPORTED_MEMORIZE_MODALITIES, SUPPORTED_MEMORY_TYPES


def openapi_schema() -> dict[str, Any]:
    """Return the built-in server OpenAPI contract."""

    error_response = {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                },
            }
        },
    }
    where_schema = {
        "type": "object",
        "additionalProperties": True,
        "description": "Optional scope filters validated by the configured UserConfig.model.",
    }
    health_response = {
        "type": "object",
        "required": ["ok", "service", "version", "storage", "providers", "auth", "limits"],
        "properties": {
            "ok": {"type": "boolean"},
            "service": {"type": "string", "const": "memu-server"},
            "version": {"type": "string"},
            "storage": {"type": ["string", "null"]},
            "providers": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "llm_profiles": {"type": "array", "items": {"type": "string"}},
                    "storage": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "metadata_store": {"type": ["string", "null"]},
                            "vector_index": {"type": ["string", "null"]},
                        },
                    },
                },
            },
            "auth": {
                "type": "object",
                "required": ["enabled"],
                "properties": {"enabled": {"type": "boolean"}},
            },
            "limits": {
                "type": "object",
                "required": ["max_request_bytes"],
                "properties": {"max_request_bytes": {"type": "integer", "minimum": 1}},
            },
        },
    }
    memory_type_schema = {
        "type": "string",
        "enum": list(SUPPORTED_MEMORY_TYPES),
    }
    modality_schema = {
        "type": "string",
        "enum": list(SUPPORTED_MEMORIZE_MODALITIES),
    }
    memory_categories_schema = {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "description": "Category names to link to the item. An empty list is allowed.",
    }
    query_schema = {
        "oneOf": [
            {
                "type": "string",
                "description": "Convenience shorthand for a user message.",
                "minLength": 1,
                "examples": ["What should this agent remember?"],
            },
            {
                "type": "object",
                "required": ["role", "content"],
                "properties": {
                    "role": {"type": "string", "minLength": 1, "examples": ["user"]},
                    "content": {
                        "oneOf": [
                            {"type": "string", "minLength": 1},
                            {
                                "type": "object",
                                "required": ["text"],
                                "properties": {"text": {"type": "string", "minLength": 1}},
                            },
                        ]
                    },
                },
            },
        ]
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "memU Self-Hosted API",
            "version": __version__,
            "description": "Built-in JSON API wrapper around MemoryService.",
        },
        "servers": [{"url": "http://127.0.0.1:8765"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Enabled when MEMU_SERVER_API_KEY or --api-key is configured.",
                }
            },
            "schemas": {
                "ErrorResponse": error_response,
                "Where": where_schema,
                "Query": query_schema,
                "MemoryType": memory_type_schema,
                "Modality": modality_schema,
                "MemoryCategories": memory_categories_schema,
                "HealthResponse": health_response,
            },
        },
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "Server health",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/HealthResponse"}}
                            },
                        }
                    },
                },
                "head": {
                    "summary": "Health check metadata",
                    "responses": {"200": {"description": "Server health headers"}},
                },
            },
            "/api/v3/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "Server health",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/HealthResponse"}}
                            },
                        }
                    },
                },
                "head": {
                    "summary": "Health check metadata",
                    "responses": {"200": {"description": "Server health headers"}},
                },
            },
            "/openapi.json": {
                "get": {
                    "summary": "OpenAPI contract",
                    "responses": {
                        "200": {
                            "description": "OpenAPI schema",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                },
                "head": {
                    "summary": "OpenAPI contract metadata",
                    "responses": {"200": {"description": "OpenAPI contract headers"}},
                },
            },
            "/api/v3/openapi.json": {
                "get": {
                    "summary": "OpenAPI contract",
                    "responses": {
                        "200": {
                            "description": "OpenAPI schema",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                },
                "head": {
                    "summary": "OpenAPI contract metadata",
                    "responses": {"200": {"description": "OpenAPI contract headers"}},
                },
            },
            "/api/v3/memory/memorize": {
                "post": {
                    "summary": "Memorize a resource",
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["resource_url", "modality"],
                                    "properties": {
                                        "resource_url": {"type": "string"},
                                        "modality": {"$ref": "#/components/schemas/Modality"},
                                        "user": {"$ref": "#/components/schemas/Where"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory/retrieve": {
                "post": {
                    "summary": "Retrieve relevant memory",
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "anyOf": [
                                        {"required": ["query"]},
                                        {"required": ["queries"]},
                                    ],
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "minLength": 1,
                                            "description": "Convenience shorthand for a single user query.",
                                        },
                                        "queries": {
                                            "type": "array",
                                            "minItems": 1,
                                            "description": (
                                                "Conversation messages. String items are normalized as user messages."
                                            ),
                                            "items": {"$ref": "#/components/schemas/Query"},
                                        },
                                        "where": {"$ref": "#/components/schemas/Where"},
                                        "method": {
                                            "type": "string",
                                            "enum": ["rag", "llm"],
                                            "description": (
                                                "Optional per-request retrieval method override. "
                                                "Defaults to the service retrieve_config.method."
                                            ),
                                        },
                                        "ranking": {
                                            "type": "string",
                                            "enum": ["similarity", "salience"],
                                            "description": (
                                                "Optional per-request item ranking override for RAG item recall. "
                                                "Defaults to retrieve_config.item.ranking."
                                            ),
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory/categories": {
                "post": {
                    "summary": "List memory categories",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _where_request_body(),
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory/items": {
                "post": {
                    "summary": "List memory items",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _where_request_body(),
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory/items/create": {
                "post": {
                    "summary": "Create a source-less memory item",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _create_item_request_body(),
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory/items/update": {
                "post": {
                    "summary": "Update a memory item",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _update_item_request_body(),
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory/items/delete": {
                "post": {
                    "summary": "Delete a memory item",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _delete_item_request_body(),
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory/clear": {
                "post": {
                    "summary": "Clear memory for an optional scope",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _where_request_body(),
                    "responses": _json_responses(error_response),
                }
            },
            "/api/v3/memory": {
                "delete": {
                    "summary": "Clear memory for an optional scope",
                    "security": [{"bearerAuth": []}],
                    "requestBody": _where_request_body(required=False),
                    "responses": _json_responses(error_response),
                }
            },
        },
    }


def _create_item_request_body() -> dict[str, Any]:
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["memory_type", "memory_content", "memory_categories"],
                    "properties": {
                        "memory_type": {"$ref": "#/components/schemas/MemoryType"},
                        "memory_content": {"type": "string", "minLength": 1},
                        "memory_categories": {"$ref": "#/components/schemas/MemoryCategories"},
                        "user": {"$ref": "#/components/schemas/Where"},
                        "propagate": {"type": "boolean", "default": True},
                    },
                }
            }
        },
    }


def _update_item_request_body() -> dict[str, Any]:
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["memory_id"],
                    "anyOf": [
                        {"required": ["memory_type"]},
                        {"required": ["memory_content"]},
                        {"required": ["memory_categories"]},
                    ],
                    "properties": {
                        "memory_id": {"type": "string", "minLength": 1},
                        "memory_type": {"$ref": "#/components/schemas/MemoryType"},
                        "memory_content": {"type": "string", "minLength": 1},
                        "memory_categories": {"$ref": "#/components/schemas/MemoryCategories"},
                        "user": {"$ref": "#/components/schemas/Where"},
                        "propagate": {"type": "boolean", "default": True},
                    },
                }
            }
        },
    }


def _delete_item_request_body() -> dict[str, Any]:
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["memory_id"],
                    "properties": {
                        "memory_id": {"type": "string", "minLength": 1},
                        "user": {"$ref": "#/components/schemas/Where"},
                        "propagate": {"type": "boolean", "default": True},
                    },
                }
            }
        },
    }


def _where_request_body(*, required: bool = True) -> dict[str, Any]:
    return {
        "required": required,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"where": {"$ref": "#/components/schemas/Where"}},
                }
            }
        },
    }


def _json_responses(error_response: dict[str, Any]) -> dict[str, Any]:
    return {
        "200": {
            "description": "Successful response",
            "content": {"application/json": {"schema": {"type": "object"}}},
        },
        "400": {
            "description": "Invalid request",
            "content": {"application/json": {"schema": error_response}},
        },
        "401": {
            "description": "Missing or invalid bearer token",
            "content": {"application/json": {"schema": error_response}},
        },
        "405": {
            "description": "Method not allowed",
            "content": {"application/json": {"schema": error_response}},
        },
        "413": {
            "description": "JSON body is too large",
            "content": {"application/json": {"schema": error_response}},
        },
        "500": {
            "description": "Unexpected server error",
            "content": {"application/json": {"schema": error_response}},
        },
    }


__all__ = ["openapi_schema"]
