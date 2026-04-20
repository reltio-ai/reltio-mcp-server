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
from src.util.api import extract_entity_id, extract_relation_id, extract_change_request_id
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
    options: str = Field(
        default="",
        description="Optional comma-separated list of options"
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
    options: str = Field(
        default="",
        description="Optional comma-separated list of options (e.g., sendHidden,updateAttributeUpdateDates,addRefAttrUriToCrosswalk)"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    always_create_dcr: bool = Field(
        default=True,
        description="If true, creates a DCR without updating the entity.(TO BE USED MOST OF THE TIME, SKIP IF Changes Seem minimal)"
    )
    change_request_id: Optional[str] = Field(
        default="",
        description="If provided, all changes will be added to the DCR with this ID instead of updating the entity directly."
    )
    overwrite_default_crosswalk_value: bool = Field(
        default=True,
        description="If true, overwrites the default crosswalk value.(TO BE USED MOST OF THE TIME, SKIP IF Changes Seem minimal)"
    )

    @field_validator('entity_id')
    @classmethod
    def extract_entity_id(cls, v):
        return extract_entity_id(v)
     
    @field_validator('change_request_id')
    @classmethod
    def extract_change_request_id(cls, v):
        return extract_change_request_id(v)  

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

# ============================================================================
# NEW MODELS ADDED FROM SOURCE REPOSITORY
# ============================================================================

import uuid

class CrosswalkModel(BaseModel):
    """Model for crosswalk objects in relations"""
    type: str = Field(
        default="configuration/sources/Reltio",
        description="Crosswalk type (defaults to 'configuration/sources/Reltio')"
    )
    sourceTable: str = Field(
        default="",
        description="Source table name (defaults to empty string)"
    )
    value: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Crosswalk value (defaults to a unique UUID4)"
    )

class RelationObjectModel(BaseModel):
    """Model for startObject and endObject in relations"""
    type: str = Field(
        ...,
        description="Entity type (e.g., 'configuration/entityTypes/Organization')"
    )
    objectURI: Optional[str] = Field(
        None,
        description="Object URI (e.g., 'entities/e1')"
    )
    crosswalks: Optional[List[CrosswalkModel]] = Field(
        None,
        description="List of crosswalks for the object"
    )
    
    @model_validator(mode='after')
    def validate_object_identification(self):
        """Validate that either objectURI or crosswalks is provided"""
        if not self.objectURI and not self.crosswalks:
            raise ValueError("Either objectURI or crosswalks must be provided")
        return self

class RelationModel(BaseModel):
    """Model for a single relation"""
    type: str = Field(
        ...,
        description="Relation type (e.g., 'configuration/relationTypes/OrganizationIndividual')"
    )
    crosswalks: Optional[List[CrosswalkModel]] = Field(
        None,
        description="List of crosswalks for the relation"
    )
    startObject: RelationObjectModel = Field(
        ...,
        description="Start object of the relation"
    )
    endObject: RelationObjectModel = Field(
        ...,
        description="End object of the relation"
    )

class CreateRelationsRequest(BaseModel):
    """Model for creating relations"""
    relations: List[RelationModel] = Field(
        ...,
        min_length=1,
        description="List of relations to create"
    )
    options: Optional[str] = Field(
        None,
        description="Comma-separated list of options (e.g., 'partialOverride', 'directMatchMode', etc.)"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )


class GetEntityRelationsRequest(BaseModel):
    """Model for get_entity_relations_tool request"""
    entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Entity ID to get connections for"
    )
    entity_types: List[str] = Field(
        ...,
        min_length=1,
        description="List of entity types that will be returned (mandatory)"
    )
    sort_by: Optional[str] = Field(
        default="",
        description="Specifies how to sort the results"
    )
    in_relations: Optional[List[Any]] = Field(
        default=None,
        description="List of relation types that have endEntity equal to current entity"
    )
    out_relations: Optional[List[Any]] = Field(
        default=None,
        description="List of relation types that have startEntity equal to current entity"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Specifies the first element in the request (default = 0)"
    )
    max: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Specifies the maximum numbers of elements (default = 10)"
    )
    show_relationship: Optional[str] = Field(
        default="",
        description="URI of relationship to show specific page of connections"
    )
    show_entity: Optional[str] = Field(
        default="",
        description="URI of connected entity to show specific page of connections"
    )
    next_entry: Optional[str] = Field(
        default="",
        description="Next connection specification if connection path does not equal one hop"
    )
    groups: Optional[List[str]] = Field(
        default=None,
        description="List of groups types that have entities as a member"
    )
    filter: Optional[str] = Field(
        default="",
        description="Enables filtering of entities using a condition"
    )
    relation_filter: Optional[str] = Field(
        default="",
        description="Enables filtering relations with searchRelationsWithFilter option"
    )
    return_objects: bool = Field(
        default=False,
        description="Whether the whole object data would be put into result (default = false)"
    )
    return_dates: bool = Field(
        default=False,
        description="Whether the activeness (startDate, endDate) attributes would be put into result (default = false)"
    )
    return_labels: bool = Field(
        default=True,
        description="Whether the entityLabel and relationLabel fields are contained in the response (default = true)"
    )
    id: Optional[str] = Field(
        default="",
        description="Identifier for this connections group"
    )
    suggested: Optional[List[str]] = Field(
        default=None,
        description="Other buckets from this connections request that must be mixed into this bucket"
    )
    limit_credits_consumption: bool = Field(
        default=False,
        description="Whether to limit credits consumption (query parameter)"
    )
    return_data_anyway: bool = Field(
        default=False,
        description="Whether to return data anyway (query parameter)"
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
            
    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max does not exceed 10000"""
        if self.offset + self.max > 10000:
            raise ValueError("The sum of offset and max must not exceed 10000")
        return self

class RelationSearchRequest(BaseModel):
    """Model for relation search requests"""
    filter: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_FILTER_LENGTH)]] = Field(
        default="",
        description="Enables relations filtering by a condition"
    )
    select: Optional[str] = Field(
        default="",
        description="Comma-separated list of properties from relation structure to return"
    )
    max: int = Field(
        default=10,
        ge=1,
        le=10000,
        description="Maximum number of relations to return (default=10, max=10000)"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Starting element in result set for pagination (default=0)"
    )
    sort: Optional[str] = Field(
        default="",
        description="Attribute or list of attributes for ordering"
    )
    order: Optional[str] = Field(
        default="asc",
        description="Sort order: 'asc' (ascending) or 'desc' (descending)"
    )
    options: Optional[str] = Field(
        default="",
        description="Comma-separated options"
    )
    activeness: Optional[str] = Field(
        default="active",
        description="Activeness filter: 'active' (default), 'all', or 'not_active'"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('filter')
    @classmethod
    def validate_filter(cls, v):
        if v:
            # Check for balanced parentheses
            if v.count('(') != v.count(')'):
                raise ValueError("Unbalanced parentheses in filter expression")
        return v

    @field_validator('order')
    @classmethod
    def validate_order(cls, v):
        if v and v.lower() not in ['asc', 'desc']:
            raise ValueError("Order must be 'asc' or 'desc'")
        return v.lower() if v else "asc"

    @field_validator('activeness')
    @classmethod
    def validate_activeness(cls, v):
        if v and v.lower() not in ['active', 'all', 'not_active']:
            raise ValueError("Activeness must be 'active', 'all', or 'not_active'")
        return v.lower() if v else "active"

    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max does not exceed 10000"""
        if self.offset + self.max > 10000:
            raise ValueError("The sum of offset and max must not exceed 10000")
        return self



class EntityInteractionsRequest(BaseModel):
    """Model for get_entity_interactions_tool request"""
    entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Entity ID to get interactions for"
    )
    max: int = Field(
        default=50,
        ge=1,
        le=MAX_RESULTS_LIMIT,
        description="Maximum number of interactions to return. Default is 50"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Starting index for paginated results. Default is 0"
    )
    order: Optional[str] = Field(
        default="asc",
        description="Sort order ('asc' or 'desc'). Default is asc"
    )
    sort: Optional[str] = Field(
        default="",
        description="Field to sort by. Default sorting is by timestamp"
    )
    filter: Optional[str] = Field(
        default="",
        description="Filter condition for interactions"
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
    
    @field_validator('order')
    @classmethod
    def validate_order(cls, v):
        if v and v.lower() not in ['asc', 'desc']:
            raise ValueError("Order must be 'asc' or 'desc'")
        return v.lower() if v else "asc"
    
    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max does not exceed 10000"""
        if self.offset + self.max > 10000:
            raise ValueError("The sum of offset and max must not exceed 10000")
        return self

class CreateInteractionRequest(BaseModel):
    """Model for creating interactions"""
    interactions: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of interaction objects to create. Each interaction must have a 'type' field."
    )
    source_system: Optional[str] = Field(
        default="configuration/sources/Reltio",
        description="Source system for the interactions"
    )
    crosswalk_value: Optional[str] = Field(
        default="",
        description="Identifier of an interaction object in the source system"
    )
    return_objects: bool = Field(
        default=True,
        description="Whether the response must include the created objects"
    )
    options: Optional[str] = Field(
        default="",
        description="Options for the request (e.g., 'sendHidden')"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('interactions')
    @classmethod
    def validate_interactions(cls, v):
        """Validate that each interaction has required fields"""
        if not v:
            raise ValueError("At least one interaction must be provided")
        
        for i, interaction in enumerate(v):
            if not isinstance(interaction, dict):
                raise ValueError(f"Interaction at index {i} must be a dictionary")
            
            if 'type' not in interaction:
                raise ValueError(f"Interaction at index {i} must have a 'type' field")
            
            if not interaction['type']:
                raise ValueError(f"Interaction at index {i} 'type' field cannot be empty")
        
        return v

class LookupListRequest(BaseModel):
    """Model for listing lookups by type"""
    lookup_type: str = Field(
        ...,
        description="RDM lookup type (e.g., 'rdm/lookupTypes/VistaVegetarianOrVegan')"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    max_results: Optional[int] = Field(
        default=10,
        ge=1,
        le=10,
        description="Maximum number of results to return per call (capped at 10). Use this for paging."
    )
    display_name_prefix: Optional[str] = Field(
        default="",
        description="Display name prefix to filter by"
    )
    
    @field_validator('lookup_type')
    @classmethod
    def validate_lookup_type(cls, v):
        """Validate lookup type format"""
        if not v:
            raise ValueError("lookup_type is required")
        # Basic validation to ensure it looks like a proper lookup type
        if not v.startswith('rdm/lookupTypes/'):
            raise ValueError("lookup_type must start with 'rdm/lookupTypes/'")
        return v

class GetPossibleAssigneesRequest(BaseModel):
    """Model for getting possible assignees for workflow tasks"""
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID for the Reltio environment",
        exclude=True  # Exclude from serialization as it's used in URL path
    )
    tasks: Optional[List[str]] = Field(
        default=None,
        description="List of task IDs to get possible assignees for. Cannot be used with task_filter or exclude."
    )
    task_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filter criteria for tasks. Cannot be used with tasks parameter.",
        serialization_alias="taskFilter"
    )
    exclude: Optional[List[str]] = Field(
        default=None,
        description="List of task IDs to exclude. Cannot be used with tasks parameter."
    )
    
    @model_validator(mode='after')
    def validate_parameter_combinations(self):
        """Validate that only one parameter approach is used at a time"""
        # Treat empty collections as "not provided"
        has_tasks = self.tasks is not None and len(self.tasks) > 0
        has_task_filter = self.task_filter is not None and len(self.task_filter) > 0
        has_exclude = self.exclude is not None and len(self.exclude) > 0
        
        if has_tasks and (has_task_filter or has_exclude):
            raise ValueError("Cannot use 'tasks' parameter with 'task_filter' or 'exclude' parameters")
        
        if not has_tasks and not has_task_filter and not has_exclude:
            raise ValueError("At least one parameter must be provided: 'tasks', 'task_filter', or 'exclude'")
        
        return self

class RetrieveTasksRequest(BaseModel):
    """Model for retrieve_tasks_tool request"""
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID for the Reltio environment",
        exclude=True  # Exclude from serialization as it's used in URL path
    )
    assignee: Optional[str] = Field(
        default=None,
        description="Task assignee. To retrieve unassigned tasks, use a value of 'none'"
    )
    process_instance_id: Optional[str] = Field(
        default=None,
        description="Process instance ID",
        serialization_alias="processInstanceId"
    )
    process_type: Optional[str] = Field(
        default=None,
        description="Process instance type. Use this field to filter on a single process type",
        serialization_alias="processType"
    )
    process_types: Optional[List[str]] = Field(
        default=None,
        description="Process instance types. Use this field to filter on multiple process types",
        serialization_alias="processTypes"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Start position for pagination"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=MAX_RESULTS_LIMIT,
        description="Number of records to be returned (capped at 100)",
        serialization_alias="max"
    )
    suspended: Optional[bool] = Field(
        default=None,
        description="Filter by suspended status (true or false)"
    )
    created_by: Optional[str] = Field(
        default=None,
        description="Task owner/creator",
        serialization_alias="createdBy"
    )
    priority_class: Optional[str] = Field(
        default=None,
        description="Task priority. Possible values: Urgent, High, Medium, Low",
        serialization_alias="priorityClass"
    )
    order_by: str = Field(
        default="createTime",
        description="Sort criteria. Possible values: createTime, assignee, dueDate, priority",
        serialization_alias="orderBy"
    )
    ascending: bool = Field(
        default=False,
        description="Sort order. True for ascending, False for descending"
    )
    task_type: Optional[str] = Field(
        default=None,
        description="Task type (e.g., 'dcrReview', 'dcrInternalReview')",
        serialization_alias="taskType"
    )
    created_after: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filter tasks created after this time (in milliseconds since epoch)",
        serialization_alias="createdAfter"
    )
    created_before: Optional[int] = Field(
        default=None,
        ge=0,
        description="Filter tasks created before this time (in milliseconds since epoch)",
        serialization_alias="createdBefore"
    )
    state: str = Field(
        default="valid",
        description="Validation state of tasks. Possible values: valid, invalid, all"
    )
    object_uris: Optional[List[str]] = Field(
        default=None,
        description="List of Reltio object URIs (entity/relation)",
        serialization_alias="objectURIs"
    )
    show_task_variables: bool = Field(
        default=False,
        description="Display task variables",
        serialization_alias="showTaskVariables"
    )
    show_task_local_variables: bool = Field(
        default=False,
        description="Display task local variables",
        serialization_alias="showTaskLocalVariables"
    )
    object_filter: Optional[str] = Field(
        default=None,
        description="Search filter expression for entities linked to workflow tasks",
        serialization_alias="objectFilter"
    )
    
    @field_validator('priority_class')
    @classmethod
    def validate_priority_class(cls, v):
        """Validate priority class"""
        if v is not None:
            valid_priorities = ['Urgent', 'High', 'Medium', 'Low']
            if v not in valid_priorities:
                raise ValueError(f"priority_class must be one of: {', '.join(valid_priorities)}")
        return v
    
    @field_validator('order_by')
    @classmethod
    def validate_order_by(cls, v):
        """Validate order by field"""
        valid_order_by = ['createTime', 'assignee', 'dueDate', 'priority']
        if v not in valid_order_by:
            raise ValueError(f"order_by must be one of: {', '.join(valid_order_by)}")
        return v
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        """Validate state field"""
        valid_states = ['valid', 'invalid', 'all']
        if v not in valid_states:
            raise ValueError(f"state must be one of: {', '.join(valid_states)}")
        return v
    
    @field_validator('created_after', 'created_before')
    @classmethod
    def validate_timestamps(cls, v, info):
        """Validate timestamp is positive if provided"""
        if v is not None and v < 0:
            raise ValueError(f"{info.field_name} must be a non-negative integer")
        return v
    
    @model_validator(mode='after')
    def validate_timestamp_ranges(self):
        """Validate that before timestamps are greater than after timestamps"""
        if self.created_before is not None and self.created_after is not None:
            if self.created_before <= self.created_after:
                raise ValueError("created_before must be greater than created_after")
        
        return self
    
    
    
    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max_results does not exceed 10000"""
        if self.offset + self.max_results > 10000:
            raise ValueError("The sum of offset and max_results must not exceed 10000")
        return self

class GetTaskDetailsRequest(BaseModel):
    """Model for get_task_details_tool request"""
    task_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The ID of the task to retrieve details for"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID for the Reltio environment"
    )
    show_task_variables: bool = Field(
        default=False,
        description="Display task variables"
    )
    show_task_local_variables: bool = Field(
        default=False,
        description="Display task local variables"
    )
    
    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v):
        """Validate task ID is not empty and contains only valid characters"""
        if not v or not v.strip():
            raise ValueError("Task ID cannot be empty")
        
        # Remove whitespace
        v = v.strip()
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9-_]+$', v):
            raise ValueError("Task ID can only contain alphanumeric characters, hyphens, and underscores")
        
        return v

class StartProcessInstanceRequest(BaseModel):
    """Model for starting a process instance"""
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    process_type: str = Field(
        ...,
        description="The type of process to start"
    )
    object_uris: List[str] = Field(
        ...,
        description="List of object URIs to associate with the process"
    )
    comment: Optional[str] = Field(
        None,
        description="Optional comment for the process instance"
    )
    variables: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional variables to pass to the process"
    )
    
    @field_validator('process_type')
    @classmethod
    def validate_process_type(cls, v):
        """Validate that process_type is not empty"""
        if not v or not v.strip():
            raise ValueError("Process type cannot be empty")
        return v.strip()
    
    @field_validator('object_uris')
    @classmethod
    def validate_object_uris(cls, v):
        """Validate that object_uris is not empty"""
        if not v or len(v) == 0:
            raise ValueError("Object URIs cannot be empty")
        return v

class ExecuteTaskActionRequest(BaseModel):
    """Model for executing an action on a workflow task"""
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    task_id: str = Field(
        ...,
        description="The ID of the task to execute action on"
    )
    action: str = Field(
        ...,
        description="The action to execute (e.g., 'Approve', 'Reject')"
    )
    process_instance_comment: Optional[str] = Field(
        None,
        description="Optional comment for the process instance"
    )
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        """Validate that action is not empty and is a valid string"""
        if not v or not v.strip():
            raise ValueError("Action cannot be empty")
        return v.strip()


class EntityWithMatchesRequest(BaseModel):
    """Model for get_entity_with_matches request"""
    entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Entity ID to retrieve with matches"
    )
    attributes: List[str] = Field(
        default_factory=list,
        description="Specific attributes to return for source entity. Empty list returns all attributes"
    )
    include_match_attributes: bool = Field(
        default=True,
        description="Whether to include full attribute details for matching entities"
    )
    match_attributes: List[str] = Field(
        default_factory=list,
        description="Specific attributes to return for matching entities (only used if include_match_attributes=True). Empty list returns all attributes"
    )
    match_limit: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Maximum number of potential matches to return (1-5)"
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


class CreateEntitiesRequest(BaseModel):
    """Model for create entities request"""
    entities: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of entity objects to create. Each entity must have a 'type' field."
    )
    return_objects: bool = Field(
        default=False,
        description="Whether the response contains created entities: true (default) or false"
    )
    execute_lca: bool = Field(
        default=True,
        description="Whether to trigger all Lifecycle Actions during this request: true (default) or false"
    )
    tenant_id: Annotated[str, StringConstraints(pattern=TENANT_ID_PATTERN)] = Field(
        default=RELTIO_TENANT,
        description="Tenant ID"
    )
    
    @field_validator('entities')
    @classmethod
    def validate_entities(cls, v):
        """Validate that each entity has required fields"""
        if not v:
            raise ValueError("At least one entity must be provided")
        
        for i, entity in enumerate(v):
            if not isinstance(entity, dict):
                raise ValueError(f"Entity at index {i} must be a dictionary")
            
            if 'type' not in entity:
                raise ValueError(f"Entity at index {i} must have a 'type' field")
            
            if not entity['type']:
                raise ValueError(f"Entity at index {i} 'type' field cannot be empty")
        
        return v


class GetEntityParentsRequest(BaseModel):
    """Model for get_entity_parents request"""
    entity_id: Annotated[str, StringConstraints(pattern=ENTITY_ID_PATTERN)] = Field(
        ...,
        description="Entity ID to get parents for"
    )
    graph_type_uris: str = Field(
        ...,
        description="Comma-separated list of graph type URIs to traverse (required)"
    )
    select: Optional[str] = Field(
        default="",
        description="Comma-separated list of properties to include in the response"
    )
    options: Optional[str] = Field(
        default="",
        description="Comma-separated list of options affecting the response content (sendHidden, ovOnly, nonOvOnly)"
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
    
    @field_validator('graph_type_uris')
    @classmethod
    def validate_graph_type_uris(cls, v):
        """Validate that graph_type_uris is not empty"""
        if not v or not v.strip():
            raise ValueError("graph_type_uris is required and cannot be empty")
        return v.strip()


class UnifiedMatchRequest(BaseModel):
    """Model for unified match requests supporting score, confidence, and match rule filtering"""
    search_type: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        default="match_rule",
        description="Type of search: 'match_rule', 'score', or 'confidence'"
    )
    filter: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        ...,
        description="Filter value: match_rule_id for match_rule, 'start,end' for score, confidence_level for confidence"
    )
    entity_type: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = Field(
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
        description="Starting index for paginated results. Use 0 for the first page."
    )
    search_filters: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        default="",
        description="Additional search filters to apply (e.g., 'equals(attributes.FirstName,John)')"
    )
    
    @model_validator(mode='after')
    def validate_offset_max_combination(self):
        """Validate that offset + max does not exceed 10000"""
        if self.offset + self.max_results > 10000:
            raise ValueError("The sum of offset and max must not exceed 10000")
        return self
    
    @field_validator('search_type')
    @classmethod
    def validate_search_type(cls, v):
        """Validate search type"""
        valid_types = ['match_rule', 'score', 'confidence']
        if v not in valid_types:
            raise ValueError(f"search_type must be one of: {', '.join(valid_types)}")
        return v
    
    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v):
        """Validate entity type is not empty"""
        if not v or not v.strip():
            raise ValueError("entity_type cannot be empty")
        return v.strip()

    @model_validator(mode='after')
    def validate_filter_for_search_type(self):
        """Validate filter format based on search_type"""
        if self.search_type == "score":
            # For score, filter should be "start,end" format
            try:
                parts = self.filter.split(',')
                if len(parts) != 2:
                    raise ValueError("For score search_type, filter must be in format 'start,end' (e.g., '50,100')")
                start_score = int(parts[0].strip())
                end_score = int(parts[1].strip())
                if start_score < 0 or start_score > 100 or end_score < 0 or end_score > 100:
                    raise ValueError("Score values must be between 0 and 100")
                if start_score > end_score:
                    raise ValueError("Start score must be less than or equal to end score")
            except ValueError as e:
                if "invalid literal for int()" in str(e):
                    raise ValueError("For score search_type, filter must contain numeric values (e.g., '50,100')")
                raise e
        
        elif self.search_type == "match_rule":
            # For match_rule, filter should be a non-empty string (match rule ID)
            if not self.filter.strip():
                raise ValueError("For match_rule search_type, filter must be a non-empty match rule ID")
        
        return self

class GetPotentialMatchApisRequest(BaseModel):
    """Model for getting potential match APIs"""
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