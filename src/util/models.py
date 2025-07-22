"""
Centralized definitions for Pydantic models used across the Reltio MCP Server.
This module contains all data validation models used by the various API endpoints
and tools.
"""
from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator
from typing_extensions import Annotated
from typing import List, Optional, Dict, Any
from src.constants import (
    ENTITY_ID_PATTERN, 
    TENANT_ID_PATTERN, 
    MAX_RESULTS_LIMIT, 
    MAX_ENTITY_TYPE_LENGTH, 
    MAX_FILTER_LENGTH, 
    MAX_QUERY_LENGTH,
    RELATION_ID_PATTERN
)
from src.env import RELTIO_TENANT
from src.util.api import extract_entity_id, extract_relation_id
import re

# Entity-related models
class EntityIdRequest(BaseModel):
    """Model for requests with entity ID"""
    entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Entity ID"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('entity_id')
    @classmethod
    def extract_entity_id(cls, v):
        """Extract the ID part from an entity URI if needed"""
        return extract_entity_id(v)

class UpdateEntityAttributesRequest(BaseModel):
    """Model for update entity attributes request"""
    entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Entity ID"
    )
    updates: List[Dict[str, Any]] = Field(
        ...,
        description="List of attribute update operations"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )

    @field_validator('entity_id')
    @classmethod
    def extract_entity_id(cls, v):
        return extract_entity_id(v)  

class MergeEntitiesRequest(BaseModel):
    """Model for merging two entities"""
    entity_ids: List[str] = Field(
        ...,
        description="List of two entity IDs to merge",
        min_items=2,
        max_items=2
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('entity_ids')
    @classmethod
    def validate_entity_ids(cls, v):
        """Validate and format entity IDs"""
        if len(v) != 2:
            raise ValueError("Exactly two entity IDs must be provided")
            
        # Format entity IDs to ensure they have the required prefix
        formatted_ids = []
        for entity_id in v:
            # Extract ID if it's in the format "entities/<entity_id>"
            if entity_id.startswith("entities/"):
                formatted_ids.append(entity_id)
            else:
                # Add prefix if it's just the ID
                formatted_ids.append(f"entities/{extract_entity_id(entity_id)}")
        
        return formatted_ids

class RejectMatchRequest(BaseModel):
    """Model for rejecting a match between two entities"""
    source_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Source entity ID"
    )
    target_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Target entity ID to reject as a match"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('source_id', 'target_id')
    @classmethod
    def extract_entity_id(cls, v):
        """Extract the ID part from an entity URI if needed"""
        return extract_entity_id(v)

# Search-related models
class EntitySearchRequest(BaseModel):
    """Model for entity search requests"""
    query: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_QUERY_LENGTH)]] = Field(
        default="",
        description="Simple text query"
    )
    filter: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_FILTER_LENGTH)]] = Field(
        default="",
        description="Advanced filter expression"
    )
    entity_type: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_ENTITY_TYPE_LENGTH)]] = Field(
        default="",
        description="Optional entity type to filter by"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=MAX_RESULTS_LIMIT,
        description="Maximum number of results to return per call (capped at 10 by the tool layer). Use this for paging."
    )
    sort: Optional[str] = Field(
        default="",
        description="Attribute name to sort by"
    )
    order: Optional[str] = Field(
        default="asc",
        description="Sort order ('asc' or 'desc')"
    )
    select: Optional[str] = Field(
        default="uri,label",
        description="Comma-separated list of fields to select in the response."
    )
    options: Optional[str] = Field(
        default="ovOnly",
        description="Options for the search query."
    )
    activeness: Optional[str] = Field(
        default="active",
        description="Activeness filter for entities."
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Starting index for paginated results. Use 0 for the first page. For subsequent pages, increment offset by the number of results returned in the previous call (e.g., if you got 3 results, next offset should be 3; if you got 10, next offset should be 10)."
    )
    
    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v):
        if v:
            # Remove any potentially dangerous characters
            v = re.sub(r'[<>\'";]', '', v)
        return v
    
    @field_validator('filter')
    @classmethod
    def validate_filter(cls, v):
        if v:
            # Check for balanced parentheses
            if v.count('(') != v.count(')'):
                raise ValueError("Unbalanced parentheses in filter expression")
            # Sanitize the filter expression
            v = re.sub(r'[<>\'";]', '', v)
        return v
    
    @field_validator('order')
    @classmethod
    def validate_order(cls, v):
        if v.lower() not in ['asc', 'desc']:
            raise ValueError("Order must be 'asc' or 'desc'")
        return v.lower()

    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max_results does not exceed 10000"""
        if self.offset + self.max_results > 10000:
            raise ValueError("The sum of offset and max_results must not exceed 10000")
        return self

# Match-related models
class MatchScoreRequest(BaseModel):
    """Model for match score range requests"""
    start_match_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Minimum match score (0-100)"
    )
    end_match_score: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Maximum match score (0-100)"
    )
    entity_type: Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_ENTITY_TYPE_LENGTH)] = Field(
        default="Individual",
        description="Entity type to filter by"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=10,
        description="Maximum number of results to return per call (capped at 10). Use this for paging."
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Starting index for paginated results. Use 0 for the first page. For subsequent pages, increment offset by the number of results returned in the previous call (e.g., if you got 3 results, next offset should be 3)."
    )
    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max_results does not exceed 10000"""
        if self.offset + self.max_results > 10000:
            raise ValueError("The sum of offset and max_results must not exceed 10000")
        return self
    
    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v):
        """Validate entity type"""
        if not v:
            return "Individual"
        return v
        
    @model_validator(mode='after')
    def validate_score_range(self):
        """Validate that start_match_score <= end_match_score"""
        if self.start_match_score > self.end_match_score:
            raise ValueError("start_match_score must be less than or equal to end_match_score")
        return self

class ConfidenceLevelRequest(BaseModel):
    """Model for confidence level requests"""
    confidence_level: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        default="Low confidence",
        description="Confidence level for matches"
    )
    entity_type: Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_ENTITY_TYPE_LENGTH)] = Field(
        default="Individual",
        description="Entity type to filter by"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=10,
        description="Maximum number of results to return per call (capped at 10). Use this for paging."
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Starting index for paginated results. Use 0 for the first page. For subsequent pages, increment offset by the number of results returned in the previous call (e.g., if you got 3 results, next offset should be 3)."
    )
    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max_results does not exceed 10000"""
        if self.offset + self.max_results > 10000:
            raise ValueError("The sum of offset and max_results must not exceed 10000")
        return self
    
    @field_validator('confidence_level', 'entity_type')
    @classmethod
    def validate_string_fields(cls, v, info):
        """Validate string fields"""
        if not v:
            if info.field_name == 'confidence_level':
                return "Low confidence"
            elif info.field_name == 'entity_type':
                return "Individual"
        return v

class GetTotalMatchesRequest(BaseModel):
    """Model for getting total potential matches count"""
    min_matches: int = Field(
        default=0,
        ge=0,
        description="Minimum number of matches to filter by (greater than)"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('min_matches')
    @classmethod
    def validate_min_matches(cls, v):
        """Validate min_matches is a non-negative integer"""
        if v < 0:
            raise ValueError("min_matches must be a non-negative integer")
        return v

class GetMatchFacetsRequest(BaseModel):
    """Model for getting potential matches facets by entity type"""
    min_matches: int = Field(
        default=0,
        ge=0,
        description="Minimum number of matches to filter by (greater than)"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('min_matches')
    @classmethod
    def validate_min_matches(cls, v):
        """Validate min_matches is a non-negative integer"""
        if v < 0:
            raise ValueError("min_matches must be a non-negative integer")
        return v

# Relation-related models
class RelationIdRequest(BaseModel):
    """Model for requests with relation ID"""
    relation_id: Annotated[str, StringConstraints(pattern=RELATION_ID_PATTERN)] = Field(
        ...,
        description="Relation ID"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('relation_id')
    @classmethod
    def extract_relation_id(cls, v):
        """Extract the ID part from a relation URI if needed"""
        return extract_relation_id(v) 

# Activity-related models
class MergeActivitiesRequest(BaseModel):
    """Model for retrieving merge activities"""
    timestamp_gt: int = Field(
        ...,
        description="Filter events with timestamp greater than this value (in milliseconds since epoch)"
    )
    event_types: Optional[List[str]] = Field(
        None,
        description="List of merge event types to filter by"
    )
    timestamp_lt: Optional[int] = Field(
        None,
        description="Optional filter for events with timestamp less than this value (in milliseconds since epoch)"
    )
    entity_type: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_ENTITY_TYPE_LENGTH)]] = Field(
        None,
        description="Optional filter for specific entity type (e.g., 'Individual', 'Organization')"
    )
    user: Optional[str] = Field(
        None,
        description="Optional filter for merges performed by a specific user"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID for the Reltio environment"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )
    max_results: int = Field(
        default=100,
        ge=1,
        le=MAX_RESULTS_LIMIT,
        description="Maximum number of results to return"
    )
    
    @field_validator('timestamp_gt')
    @classmethod
    def validate_timestamp_gt(cls, v):
        """Validate timestamp_gt is a positive integer"""
        if v <= 0:
            raise ValueError("timestamp_gt must be a positive integer")
        return v
    
    @field_validator('timestamp_lt')
    @classmethod
    def validate_timestamp_lt(cls, v):
        """Validate timestamp_lt is a positive integer"""
        if v is not None and v <= 0:
            raise ValueError("timestamp_lt must be a positive integer")
        return v
        
    @model_validator(mode='after')
    def validate_timestamps(self):
        """Validate that timestamp_lt > timestamp_gt if both are provided"""
        if self.timestamp_lt is not None and self.timestamp_lt <= self.timestamp_gt:
            raise ValueError("timestamp_lt must be greater than timestamp_gt")
        return self 

class UnmergeEntityRequest(BaseModel):
    """Model for unmerge entity request"""
    origin_entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Origin entity ID (the merged entity)"
    )
    contributor_entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Contributor entity ID to unmerge from the origin entity"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('origin_entity_id', 'contributor_entity_id')
    @classmethod
    def extract_entity_id(cls, v):
        """Extract the ID part from an entity URI if needed"""
        return extract_entity_id(v) 