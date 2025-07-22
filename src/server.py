"""
Reltio MCP Server - Main

This file initializes the MCP server and registers all tools.
Tools are imported from separate modules for better organization.
"""
import logging
from typing import List, Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

# Import server name from defines
from src.env import RELTIO_SERVER_NAME, RELTIO_TENANT
# Import tools from separate modules
from src.tools.entity import (
    get_entity_details, 
    update_entity_attributes, 
    get_entity_matches, 
    get_entity_match_history, 
    merge_entities, 
    reject_entity_match, 
    export_merge_tree,
    unmerge_entity_by_contributor,
    unmerge_entity_tree_by_contributor
)
from src.tools.match import find_matches_by_match_score, find_matches_by_confidence, get_total_matches, get_total_matches_by_entity_type
from src.tools.relation import get_relation_details
from src.tools.search import search_entities
from src.tools.system import list_capabilities
from src.tools.tenant_config import (
    get_business_configuration,
    get_tenant_permissions_metadata,
    get_tenant_metadata,
    get_data_model_definition,
    get_entity_type_definition,
    get_change_request_type_definition,
    get_relation_type_definition,
    get_interaction_type_definition,
    get_graph_type_definition,
    get_grouping_type_definition
)
from src.tools.activity import get_merge_activities

# Configure logging
logger = logging.getLogger("mcp.server.reltio")

# Initialize MCP server
mcp = FastMCP(RELTIO_SERVER_NAME)

# Register tools with the MCP server
@mcp.tool()
async def search_entities_tool(filter: str, entity_type: str, 
                          tenant_id: str = RELTIO_TENANT, max_results: int = 10, sort: str = "", order: str = "asc", select: str = "uri,label", options: str = "ovOnly", activeness: str = "active", offset: int = 0, trace: bool = False) -> dict:
    """Search for entities matching the filter criteria
         
        Args:
            filter (str): Enables entity filtering using supported Reltio filter condition types.
                          Format for filter query parameter: filter=({Condition Type}[AND/OR {Condition Type}]*).
                    If multiple filters are provided, they should be combined with 'and'/'or' like given in the Examples.
                  You can combine multiple filters using AND / OR.
                  Supported filter conditions include:
                  
                  - equals(property, value)
                  - equalsCaseSensitive(property, value)
                  - containsWordStartingWith(property, value)
                  - startsWith(property, value)
                  - fullText(property, value)
                  - equalsAnalyzed(property, value)
                  - fuzzy(property, value)
                  - missing(property)
                  - exists(property)
                  - inSameAttributeValue(...)
                  - listEquals(property, value OR file-url)
                  - listEqualsCaseSensitive(property, value OR file-url)
                  - in(property, comma-separated-values)
                  - lte(property, value)
                  - gte(property, value)
                  - lt(property, value)
                  - gt(property, value)
                  - range(property, start, end)
                  - not(condition)
                  - contains(property, '*value' or '?value') — supports wildcards
                  - regexp(property, pattern) — regular expression matching
                  - insideCategoryTree(category, categoryURI)
                  - changes(attribute) — used with DELTAS or SNAPSHOT_WITH_DELTA stream payloads
                  - defaultCombining with AND / OR
                  
                  Examples:
                      - equals(attributes.LastName, 'Smith')
                      - containsWordStartingWith(attributes.FirstName, 'Jo')
                      - exists(attributes.Email)
                      - missing(attributes.Phone)
                      - in(attributes.State, 'CA,NY,TX')
                      - fuzzy(attributes.CompanyName, 'Relto')
                      - range(attributes.Age, 18, 25)
                      - not(equals(attributes.Status, 'Inactive'))
                      - equals(attributes.Country, 'US') AND startsWith(attributes.City, 'San')
            entity_type (str): Entity type to filter by. The entity type should follow PascalCase format.
                Examples: HCO, HCP, GPO, Contact, Product, Ingredient, Customer, Prospect, Location, Household, Supplier, Material, FinancialProfessional, FinancialAccount, Payer, InsurancePlan, ProductCategory, BrokerAgent, Claim, Contract, InsuredAsset, Structure, ClinicalStudy, Drug, IDN, MedicalDevice, MedicalManufacturedItem, PackagedMedicinalProduct, Person, PharmaceuticalProduct, ProductGroup, StudySite, Substance, Individual, Organization
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            max_results (int): Maximum number of results to return. Defaults to 10, and is capped at 10 per call.
            sort (str): Attribute name to sort by.
            order (str): Sort order ('asc' or 'desc'). Defaults to 'asc'.
            select (str): Comma-separated list of fields to select in the response.
            options (str): Comma-separated list of different options. Available options:
                - sendHidden: disabled by default; entity's JSON will contain hidden attributes if this option is enabled.
                - searchByOv: disabled by default, to search by all attributes with Operational Value (OV) only. You can use the searchByOv and sortByOv options in case of STATIC index OV strategy. If you use searchByOv option, sorting by OV works automatically. In case of NONE strategy, the sortByOv option is ignored. If you want to sort by OV, you should switch indexOvStrategy to STATIC.
                - ovOnly: return only attribute values that have the ov=true flag.
                - nonOvOnly: return only attribute values that have the ov=false flag. If you have a nested or reference attribute value, where ov=true, but sub-attributes, where ov=false, then these sub-attributes do not appear in the response.
                - cleanEntity: Set this option to true to get entities without certain properties.
            activeness (str): Activeness filter for entities. The following options are available:
                - active: Search only active entities. (default)
                - all: Search for both active and expired entities.
                - expired: Search for only expired entities.
                Example: activeness="all"
            offset (int): Starting index for paginated results. Use 0 for the first page. For subsequent pages, increment offset by the number of results returned in the previous call (e.g., if you got 3 results, next offset should be 3).
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the search results
        
        Examples:
            # Find all John with entity type 'Individual'
            search_entities_tool(filter="containsWordStartingWith(attributes,'John')", entity_type="Individual")

            # Find all entities with the name 'John' and living in 'TX' with entity type 'Individual' 
            search_entities_tool(filter="containsWordStartingWith(attributes,'John') and equals(attributes.Address.State,'TX'))", entity_type="Individual")

            #Find all Healthcare Organizations (HCO) based in Chicago that are not active in the system. Bring 5 results only after the first 10. For each HCO, bring the uri, label, name, identifier type and identifier ID
            search_entities_tool(select="uri,label,attributes.Name,attributes.Identifiers.Type,attributes.Identifiers.ID", activeness="expired", max_results=5, offset=10, filter="equals(attributes.Address.City,'Chicago'))", entity_type="HCO")

            # Find organizations with CompanyName fuzzy match to 'Relto'
            search_entities_tool(filter="fuzzy(attributes.CompanyName,'Relto')", entity_type="Organization")

            # Find entities that do NOT have Email
            search_entities_tool(filter="missing(attributes.Email)", entity_type="Individual")

            # Find entities where Address exists
            search_entities_tool(filter="exists(attributes.Address)", entity_type="Individual")

            # Find entities where State is either CA, NY, or TX
            search_entities_tool(filter="in(attributes.State,'CA,NY,TX')", entity_type="Individual")

            # Find entities with Age in range 18 to 25
            search_entities_tool(filter="range(attributes.Age,18,25)", entity_type="Individual")
        """
    if filter and entity_type:
            filter = f"{filter} and equals(type,'configuration/entityTypes/{entity_type}')"
    elif entity_type:
        filter = f"equals(type,'configuration/entityTypes/{entity_type}')"
    if not select or select.strip() == "":
        select = "uri,label"
    if "uri" not in select:
        select = f"uri,{select}"
    return await search_entities(filter, entity_type, tenant_id, min(max_results, 10), sort, order, select, options, activeness, offset)
    
@mcp.tool()
async def get_entity_tool(entity_id: str, filter_field: Dict[str, List[str]] = None, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get detailed information about a Reltio entity by ID
    entityType is determined by calling the same tool "get_entity_tool" with filter_field={"type": []}.
    
    Args:
        entity_id (str): The ID of the entity to retrieve
        filter_field (Dict[str, Any]): Optional list of fields to filter in the response. If not provided, all fields are returned.
            The valid Reltio API fields are: uri, type, createdBy, createdTime, updatedBy, updatedTime, attributes, isFavorite, crosswalks, analyticsAttributes, label, secondaryLabel
            * attributes: Based on the provided filter values create filter_field.
                If Individual entity type is used, the attributes field will contain at least the following fields: Name, FirstName, MiddleName, MiddleInitial, LastName, NameSuffix, Phone, Email, Address, Identifiers, DoB
                    So filter_field can be like:
                        filter_field = {"attributes": ["Name", "FirstName", "MiddleName", "MiddleInitial", "LastName", "NameSuffix", "Phone", "Email", "Address", "Identifiers", "DoB"]}
                    Other attributes can be included as well if specified in the input.
                If Organization entity type is used, the attributes field will contain at least the following fields: Name, WebsiteURL, DoingBusinessAsName, Phone, Email, Address, DUNSNumber, Identifiers
                    So filter_field can be like:
                        filter_field = {"attributes": ["Name", "WebsiteURL", "DoingBusinessAsName", "TradestyleNames", "Phone", "Email", "Address", "DUNSNumber", "Identifiers"]}
                    Other attributes can be included as well if specified in the input.
                For other entity types, the input should specify which attributes to retrieve. For example, an HCO may have a TaxIdentifier. So the input would be like this:
                    filter_field = {"attributes": ["TaxIdentifier]}
                Finally, in order to get all attributes, the list can be sent empty.
                    filter_field = {"attributes": []}
                So that all attributes will be returned.
            If any fields are provided, only those fields will be included in the response.
            Map the field names to their corresponding Reltio API field names.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.

    Returns:
        A dictionary containing the entity details
    
    Raises:
        Exception: If there's an error getting the entity details
    
    Examples:
        # Get full entity details by ID
        filter_field = None
        get_entity_details("entity_id", filter_field, "tenant_id")

        # Get all attributes of an entity by ID
        filter_field = {"attributes": []}
        get_entity_details("entity_id", filter_field, "tenant_id")

        # Get specific attributes of an entity by ID
        filter_field = {"attributes": ["Name", "FirstName", "LastName"]}
        get_entity_details("entity_id", filter_field, "tenant_id")

        # Get crosswalks and analyticsAttributes of an entity by ID
        filter_field = {"crosswalks": [], "analyticsAttributes": []}
        get_entity_details("entity_id", filter_field, "tenant_id")

        # Get specific fields of an entity by ID
        filter_field = {"uri": [], "type": [], "createdBy": [], "createdTime": [], "updatedBy": [], "updatedTime": [], "attributes": ["Name", "FirstName", "LastName"], "isFavorite": [], "crosswalks": [], "analyticsAttributes": [], "label": [], "secondaryLabel": []}
        get_entity_details("entity_id", filter_field, "tenant_id")
    """
    return await get_entity_details(entity_id, filter_field, tenant_id)

@mcp.tool()
async def update_entity_attributes_tool(entity_id: str, updates: List[Dict[str, Any]], tenant_id: str = RELTIO_TENANT) -> dict:
    """Update specific attributes of an entity in Reltio.
    Before using this tool, ensure that the entity ID, attribute URIs and crosswalk are correct.
    
    Args:
        entity_id (str): Entity ID to update
        updates (List[Dict[str, Any]]): List of update operations as per Reltio API spec
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the API response
    
    Raises:
        Exception: If there's an error during the update
    
    Examples:
        # Update FirstName and LastName attributes in entity with ID 47uMxdm
        entity_id="47uMxdm",
        updates=[
            {
                "type": "UPDATE_ATTRIBUTE",
                "uri": "entities/47uMxdm/attributes/FirstName/3Z3Tq6BBE",
                "newValue": [{"value": "Willy"}],
                "crosswalk": {"type": "configuration/sources/LNKD", "value": "LNKD.47uMxdm"}
            },
            {
                "type": "UPDATE_ATTRIBUTE",
                "uri": "entities/47uMxdm/attributes/LastName/3Z3Tq6FRU",
                "newValue": [{"value": "Haarley"}],
                "crosswalk": {"type": "configuration/sources/LNKD", "value": "LNKD.47uMxdm"}
            }
        ]
        update_entity_attributes(entity_id, updates, "tenant_id")
    """
    return await update_entity_attributes(entity_id, updates, tenant_id)

@mcp.tool()
async def get_entity_matches_tool(entity_id: str, tenant_id: str = RELTIO_TENANT, max_results: int = 25) -> dict:
    """Find potential matches for a specific entity with detailed comparisons
    
    Args:
        entity_id (str): Entity ID to find matches for
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        max_results (int): Maximum number of results to return. Default to 25
    
    Returns:
        A dictionary containing the source entity and potential matches
    
    Raises:
        Exception: If there's an error getting the potential matches for an entity
    
    Examples:
        # Find potential matches for an entity
        get_entity_matches("entity_id", "tenant_id", 10)
    """
    return await get_entity_matches(entity_id, tenant_id, max_results)

@mcp.tool()
async def get_entity_match_history_tool(entity_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Find the match history for a specific entity
    
    Args:
        entity_id (str): Entity ID to find matches for
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the source entity and match history for that entity
    
    Raises:
        Exception: If there's an error getting the match history for an entity
    
    Examples:
        # Find match history for an entity
        get_entity_match_history("entity_id", "tenant_id")
    """
    return await get_entity_match_history(entity_id, tenant_id)

@mcp.tool()
async def get_relation_tool(relation_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get detailed information about a Reltio relation by ID
    
    Args:
        relation_id (str): The ID of the relation to retrieve
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the relation details
    
    Raises:
        Exception: If there's an error getting the relation details
    
    Examples:
        # Get relation details by ID
        get_relation_details("relation_id", "tenant_id")
    """
    return await get_relation_details(relation_id, tenant_id)

@mcp.tool()
async def find_entities_by_match_score_tool(start_match_score: int = 0, end_match_score: int = 100, entity_type: str = "Individual", 
                                           tenant_id: str = RELTIO_TENANT, max_results: int = 10, offset: int = 0) -> dict:
    """Find all entities by match score range
    
    Args:
        start_match_score (int): Minimum match score to filter matches. Default to 0.
        end_match_score (int): Maximum match score to filter matches. Default to 100.
        entity_type (str): Entity type to filter by. Default to 'Individual'.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        max_results (int): Maximum number of results to return. Default to 10, and is capped at 10.
        offset (int): Starting index for paginated results. Use 0 for the first page. For subsequent pages, increment offset by the number of results returned in the previous call (e.g., if you got 3 results, next offset should be 3).
    
    Returns:
        A dictionary containing the search results
    
    Raises:
        Exception: If there's an error getting the matches
    
    Examples:
        # Find matches with a specific match score range
        find_matches_by_match_score(0, 100, "Individual", "tenant_id", 10)

        # Find matches with a different match score range
        find_matches_by_match_score(50, 80, "Organization", "tenant_id", 5)
    """
    return await find_matches_by_match_score(start_match_score, end_match_score, entity_type, tenant_id, min(max_results, 10), offset)

@mcp.tool()
async def find_entities_by_confidence_tool(confidence_level: str = "Low confidence", entity_type: str = "Individual",
                                            tenant_id: str = RELTIO_TENANT, max_results: int = 10, offset: int = 0) -> dict:
    """Find all potential matches by confidence level
    
    Args:
        confidence_level (str): Confidence level for matches (e.g., 'Strong matches', 'Medium confidence', 'Low confidence', 'High confidence', 'Super strong matches'). Default to 'Low confidence'.
        entity_type (str): Entity type to filter by. Default to 'Individual'.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        max_results (int): Maximum number of results to return. Default to 10, and is capped at 10.
        offset (int): Starting index for paginated results. Use 0 for the first page. For subsequent pages, increment offset by the number of results returned in the previous call (e.g., if you got 3 results, next offset should be 3).
    
    Returns:
        A dictionary containing the search results

    Raises:
        Exception: If there's an error getting the matches
    
    Examples:
        # Find matches with a specific confidence level
        find_matches_by_confidence("Low confidence", "Individual", "tenant_id", 10)

        # Find matches with a different confidence level
        find_matches_by_confidence("High confidence", "Organization", "tenant_id", 5)
    """
    return await find_matches_by_confidence(confidence_level, entity_type, tenant_id, min(max_results, 10), offset)

@mcp.tool()
async def get_total_matches_tool(min_matches: int = 0, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the total count of potential matches in the tenant
    
    Args:
        min_matches (int): Minimum number of matches to filter by. Returns total count of entities with greater than this many matches. Default to 0.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the total count of potential matches
    
    Raises:
        Exception: If there's an error getting the total matches count
    
    Examples:
        # Get total count of all entities with potential matches
        get_total_matches(0, "tenant_id")
        
        # Get total count of entities with more than 5 potential matches
        get_total_matches(5, "tenant_id")
    """
    return await get_total_matches(min_matches, tenant_id)

@mcp.tool()
async def get_total_matches_by_entity_type_tool(min_matches: int = 0, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the facet counts of potential matches by entity type
    
    Args:
        min_matches (int): Minimum number of matches to filter by. Returns facet counts of entities with greater than this many matches. Default to 0.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the facet counts of potential matches by entity type
    
    Raises:
        Exception: If there's an error getting the match facets
    
    Examples:
        # Get facet counts of all entities with potential matches by entity type
        get_total_matches_by_entity_type(0, "tenant_id")
        
        # Get facet counts of entities with more than 5 potential matches by entity type
        get_total_matches_by_entity_type(5, "tenant_id")
    """
    return await get_total_matches_by_entity_type(min_matches, tenant_id)

@mcp.tool()
async def merge_entities_tool(entity_ids: List[str], tenant_id: str = RELTIO_TENANT) -> dict:
    """Merge two entities in Reltio
    
    Args:
        entity_ids (List[str]): List of two entity IDs to merge (format: ["entities/<id1>", "entities/<id2>"] or just the IDs)
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result or error information
    
    Raises:
        Exception: If there's an error merging the entities
    
    Examples:
        # Merge two entities by their IDs
        merge_entities_tool(["entities/123abc", "entities/456def"], "tenant_id")
        
        # Alternatively, you can pass just the IDs without the "entities/" prefix
        merge_entities_tool(["123abc", "456def"], "tenant_id")
    """
    return await merge_entities(entity_ids, tenant_id)

@mcp.tool()
async def reject_entity_match_tool(source_id: str, target_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Mark an entity as not a match (reject the potential duplicate)
    
    Args:
        source_id (str): The entity ID that originated the search for matches
        target_id (str): The entity ID to be marked as not a match
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result or error information
    
    Raises:
        Exception: If there's an error rejecting the match
    
    Examples:
        # Reject a match between two entities
        reject_match("source_entity_id", "target_entity_id", "tenant_id")
    """
    return await reject_entity_match(source_id, target_id, tenant_id)

@mcp.tool()
async def export_merge_tree_tool(email_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Export the merge tree for all entities in a specific tenant.
    This tool allows you to export the merge tree data for all entities in a tenant. This is an asynchronous request that returns the IDs of tasks, which export data. Using these IDs you can track the status of these tasks. After completion of the tasks, a link to the result files is sent to the specified email address.
    The file with the exported data is a multi-line text file and every line has a separate JSON object that stands for one entity merge tree:
    
    Args:
        email_id (str): This parameter indicates the valid email address to which the notification is sent after the export is completed.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the scheduled export job ID and status
    
    Raises:
        Exception: If there's an error exporting the merge tree
    
    Examples:
        # Export merge tree for all entities in a tenant
        export_merge_tree("email_id", "tenant_id")
    """
    return await export_merge_tree(email_id, tenant_id)

@mcp.tool()
async def get_business_configuration_tool(tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the business configuration for a specific tenant
    
    Args:
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the business configuration
    
    Raises:
        Exception: If there's an error getting the business configuration
    
    Examples:
        # Get business configuration for a tenant
        get_business_configuration("tenant_id")
    """
    return await get_business_configuration(tenant_id)

@mcp.tool()
async def get_tenant_permissions_metadata_tool(tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the permissions and security metadata for a specific tenant
    
    Args:
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the tenant permissions metadata
    
    Raises:
        Exception: If there's an error getting the tenant permissions metadata
    
    Examples:
        # Get tenant permissions metadata for a tenant
        get_tenant_permissions_metadata("tenant_id")
    """
    return await get_tenant_permissions_metadata(tenant_id)

@mcp.tool()
async def get_tenant_metadata_tool(tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the tenant metadata details from the business configuration for a specific tenant
        Tenant metadata details includes: uri, description, schemaVersion, number_of_sources, label, createdTime, updatedTime, createdBy, updatedBy, number_of_entity_types, 
        number_of_change_request_types, number_of_relation_types, number_of_interaction_types, number_of_graph_types, number_of_survivorship_strategies, number_of_grouping_types.
        
        Args:
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the tenant metadata details
        
        Raises:
            Exception: If there's an error getting the tenant metadata details
        
        Examples:
            # Get tenant metadata details for a tenant enabling trace
            get_tenant_metadata_tool("tenant_id")
    """
    return await get_tenant_metadata(tenant_id)

@mcp.tool()
async def get_data_model_definition_tool(object_type: list, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get complete details about the data model definition from the business configuration for a specific tenant
        This data model definition is a collection of all the entity types, change request types, relation types, interaction types, graph types, survivorship strategies, and grouping types in the tenant.
        This tool should return only one of the object types at a time. If you want to get all the object types, you should explicitly pass all the object types in the list.

        Args:
            object_type (list[str]): The type of object to get the definition for. Can be any one of the following: ["entityTypes", "changeRequestTypes", "relationTypes", "interactionTypes", "graphTypes", "survivorshipStrategies", "groupingTypes"].
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the data model definition details
        
        Raises:
            Exception: If there's an error getting the data model definition details
        
        Examples:
            # Get entity type definition details for a tenant enabling trace
            get_data_model_definition_tool(["entityTypes"], "tenant_id")

            # Get change request type definition details for a tenant enabling trace
            get_data_model_definition_tool(["changeRequestTypes"], "tenant_id")

            # Get relation type definition details for a tenant enabling trace
            get_data_model_definition_tool(["relationTypes"], "tenant_id")

            # Get interaction type definition details for a tenant enabling trace
            get_data_model_definition_tool(["interactionTypes"], "tenant_id")

            # Get graph type definition details for a tenant enabling trace
            get_data_model_definition_tool(["graphTypes"], "tenant_id")

            # Get survivorship strategy definition details for a tenant enabling trace
            get_data_model_definition_tool(["survivorshipStrategies"], "tenant_id")

            # Get grouping type definition details for a tenant enabling trace
            get_data_model_definition_tool(["groupingTypes"], "tenant_id")

            # Get all data model definition details for a tenant enabling trace, this is not recommended as it will return a lot of data and may cause performance issues. 
            # So, use this only if you need to get all the data model definition details when user explicitly asks for it.
            get_data_model_definition_tool(["entityTypes", "changeRequestTypes", "relationTypes", "interactionTypes", "graphTypes", "survivorshipStrategies", "groupingTypes"], "tenant_id")
        
        Output:
            # Example output for entityTypes
            [
                {
                    "label": "Price Specification",
                    "description": "Overview of price specifications for products or services. It includes key details such as base price, discounts, effective dates, and additional pricing conditions. This information is essential for pricing strategies, sales analysis, and inventory management.",
                    "attributes": [
                        {
                            "label": "Preference Hierarchy",
                            "name": "PreferenceHierarchy",
                            "description": "Property name",
                            "type": "String",
                            "required": False,
                            "searchable": True
                        }
                    ]
                }
            ]
    """
    return await get_data_model_definition(object_type, tenant_id)

@mcp.tool()
async def get_entity_type_definition_tool(entity_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the entity type definition for a specified entity type from the business configuration of a specific tenant
        The specified entity type should be in the format of "configuration/entityTypes/<entity_type>".
        These are some examples of entity types: ["HCO", "HCP", "GPO", "Contact", "Product", "Ingredient", "Customer", "Prospect", "Location", "Household", "Supplier", "Material", "FinancialProfessional", "FinancialAccount", "Payer", "InsurancePlan", "ProductCategory", "BrokerAgent", "Claim", "Contract", "InsuredAsset", "Structure", "ClinicalStudy", "Drug", "IDN", "MedicalDevice", "MedicalManufacturedItem", "PackagedMedicinalProduct", "Person", "PharmaceuticalProduct", "ProductGroup", "StudySite", "Substance", "Individual", "Organization", "IndividualPerson", "Property", "PriceSpecification", "FinalFinishedGoods", "LegalEntity", "LegalOwner", "Policy"].
        
        Args:
            entity_type (str): The type of entity to get the definition for.
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the entity type definition
        
        Raises:
            Exception: If there's an error getting the entity type definition
        
        Examples:
            # Get entity type definition for Organization entity type
            get_entity_type_definition_tool("configuration/entityTypes/Organization", "tenant_id")

            # Get entity type definition for Individual entity type
            get_entity_type_definition_tool("configuration/entityTypes/Individual", "tenant_id")
    """
    return await get_entity_type_definition(entity_type, tenant_id)

@mcp.tool()
async def get_change_request_type_definition_tool(change_request_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the change request type definition for a specified change request type from the business configuration of a specific tenant
        The specified change request type should be in the format of "configuration/changeRequestTypes/<change_request_type>".
        
        Args:
            change_request_type (str): The type of change request to get the definition for.
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the change request type definition
        
        Raises:
            Exception: If there's an error getting the change request type definition
        
        Examples:
            # Get change request type definition for default type
            get_change_request_type_definition_tool("configuration/changeRequestTypes/default", "tenant_id")
    """
    return await get_change_request_type_definition(change_request_type, tenant_id)

@mcp.tool()
async def get_relation_type_definition_tool(relation_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the relation type definition for a specified relation type from the business configuration of a specific tenant
        The specified relation type should be in the format of "configuration/relationTypes/<relation_type>".
        These are some examples of relation types: ["OrganizationIndividual", "OrganizationAffiliation", "ReportsTo", "IndividualHasAddress", "OrganizationHasAddress", "Location", "PropertyHasAddress", "Price2FFG", "DnBHierarchy", "HHMember", "LegalEntityOwner", "IndividualEmployer", "ZoomInfoHierarchy"].
        
        Args:
            relation_type (str): The type of relation to get the definition for.
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the relation type definition
        
        Raises:
            Exception: If there's an error getting the relation type definition
        
        Examples:
            # Get relation type definition for OrganizationIndividual relation type
            get_relation_type_definition_tool("configuration/relationTypes/OrganizationIndividual", "tenant_id")

            # Get relation type definition for OrganizationAffiliation relation type
            get_relation_type_definition_tool("configuration/relationTypes/OrganizationAffiliation", "tenant_id")

            # Get relation type definition for ReportsTo relation type
            get_relation_type_definition_tool("configuration/relationTypes/ReportsTo", "tenant_id")
    """
    return await get_relation_type_definition(relation_type, tenant_id)

@mcp.tool()
async def get_interaction_type_definition_tool(interaction_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the interaction type definition for a specified interaction type from the business configuration of a specific tenant
        The specified interaction type should be in the format of "configuration/interactionTypes/<interaction_type>".
        These are some examples of interaction types: ["PurchaseOrder", "Email", "Orders", "WebEvents", "ServiceRequest", "Unclassified"].
        
        Args:
            interaction_type (str): The type of interaction to get the definition for.
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the interaction type definition
        
        Raises:
            Exception: If there's an error getting the interaction type definition
        
        Examples:
            # Get interaction type definition for PurchaseOrder interaction type
            get_interaction_type_definition_tool("configuration/interactionTypes/PurchaseOrder", "tenant_id")

            # Get interaction type definition for Email interaction type
            get_interaction_type_definition_tool("configuration/interactionTypes/Email", "tenant_id")
    """
    return await get_interaction_type_definition(interaction_type, tenant_id)

@mcp.tool()
async def get_graph_type_definition_tool(graph_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the graph type definition for a specified graph type from the business configuration of a specific tenant
        The specified graph type should be in the format of "configuration/graphTypes/<graph_type>".
        These are some examples of graph types: ["Hierarchy", "OrganizationHierarchy", "ZoomInfoHierarchy"].
        
        Args:
            graph_type (str): The type of graph to get the definition for.
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the graph type definition
        
        Raises:
            Exception: If there's an error getting the graph type definition
        
        Examples:
            # Get graph type definition for Hierarchy graph type
            get_graph_type_definition_tool("configuration/graphTypes/Hierarchy", "tenant_id")

            # Get graph type definition for OrganizationHierarchy graph type
            get_graph_type_definition_tool("configuration/graphTypes/OrganizationHierarchy", "tenant_id")

            # Get graph type definition for ZoomInfoHierarchy graph type
            get_graph_type_definition_tool("configuration/graphTypes/ZoomInfoHierarchy", "tenant_id")
    """
    return await get_graph_type_definition(graph_type, tenant_id)

@mcp.tool()
async def get_grouping_type_definition_tool(grouping_type: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the grouping type definition for a specified grouping type from the business configuration of a specific tenant
        The specified grouping type should be in the format of "configuration/groupingTypes/<grouping_type>".
        These are some examples of grouping types: ["Household"].
        
        Args:
            grouping_type (str): The type of grouping to get the definition for.
            tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
            trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        
        Returns:
            A dictionary containing the grouping type definition
        
        Raises:
            Exception: If there's an error getting the grouping type definition
        
        Examples:
            # Get grouping type definition for Household grouping type
            get_grouping_type_definition_tool("configuration/groupingTypes/Household", "tenant_id")
    """
    return await get_grouping_type_definition(grouping_type, tenant_id)

@mcp.tool()
async def get_merge_activities_tool(timestamp_gt: int, event_types: Optional[List[str]] = None, 
                                    timestamp_lt: Optional[int] = None, entity_type: Optional[str] = None, 
                                    user: Optional[str] = None, tenant_id: str = RELTIO_TENANT, 
                                    offset: int = 0, max_results: int = 100) -> dict:
    """Retrieve activity events related to entity merges with flexible filtering options
    
    Args:
        timestamp_gt (int): Filter events with timestamp greater than this value (in milliseconds since epoch)
        event_types (Optional[List[str]]): List of merge event types to filter by. Defaults to 
                                         ['ENTITIES_MERGED_MANUALLY', 'ENTITIES_MERGED', 'ENTITIES_MERGED_ON_THE_FLY']
        timestamp_lt (Optional[int]): Optional filter for events with timestamp less than this value (in milliseconds since epoch)
        entity_type (Optional[str]): Optional filter for specific entity type (e.g., 'Individual', 'Organization')
        user (Optional[str]): Optional filter for merges performed by a specific user
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        offset (int): Pagination offset. Defaults to 0.
        max_results (int): Maximum number of results to return. Defaults to 100.
    
    Returns:
        A dictionary containing the activity events matching the specified filters
    
    Raises:
        Exception: If there's an error retrieving the activity events
    
    Examples:
        # Get all merge activities since timestamp 1744191663000
        get_merge_activities_tool(1744191663000)
        
        # Get merge activities within a specific time range
        get_merge_activities_tool(1744191663000, timestamp_lt=1744291663000)
        
        # Get only manual merge activities for a specific entity type
        get_merge_activities_tool(1744191663000, event_types=['ENTITIES_MERGED_MANUALLY'], entity_type='Individual')
        
        # Get merge activities performed by a specific user
        get_merge_activities_tool(1744191663000, user='john.doe@example.com')
        
        # Combine multiple filters
        get_merge_activities_tool(
            1744191663000,
            event_types=['ENTITIES_MERGED_MANUALLY', 'ENTITIES_MERGED'],
            entity_type='Organization',
            user='john.doe@example.com',
            max_results=50
        )
    """
    return await get_merge_activities(
        timestamp_gt=timestamp_gt,
        event_types=event_types,
        timestamp_lt=timestamp_lt,
        entity_type=entity_type,
        user=user,
        tenant_id=tenant_id,
        offset=offset,
        max_results=max_results
    )

@mcp.tool()
async def capabilities_tool() -> dict:
    """List all capabilities (resources, tools, and prompts) available in this server
    
    Returns:
        A dictionary containing information about available server capabilities
    
    Raises:
        Exception: If there's an error getting the server capabilities
    """
    try:
        return await list_capabilities()
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def unmerge_entity_by_contributor_tool(origin_entity_id: str, contributor_entity_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Unmerge a contributor entity from a merged entity, keeping any profiles merged beneath it intact.
    
    Args:
        origin_entity_id (str): The ID of the origin entity (the merged entity)
        contributor_entity_id (str): The ID of the contributor entity to unmerge from the origin entity
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result of the unmerge operation with 'a' (modified origin) and 'b' (spawn) entities
    
    Raises:
        Exception: If there's an error during the unmerge operation
    
    Examples:
        # Unmerge a contributor entity from a merged entity
        unmerge_entity_by_contributor_tool("entity1", "entity2", "tenant_id")
        
        # Unmerge using entity prefixes
        unmerge_entity_by_contributor_tool("entities/entity1", "entities/entity2", "tenant_id")
    """
    return await unmerge_entity_by_contributor(origin_entity_id, contributor_entity_id, tenant_id)

@mcp.tool()
async def unmerge_entity_tree_by_contributor_tool(origin_entity_id: str, contributor_entity_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Unmerge a contributor entity and all profiles merged beneath it from a merged entity.
    
    Args:
        origin_entity_id (str): The ID of the origin entity (the merged entity)
        contributor_entity_id (str): The ID of the contributor entity to unmerge from the origin entity
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result of the unmerge operation with 'a' (modified origin) and 'b' (spawn) entities
    
    Raises:
        Exception: If there's an error during the unmerge operation
    
    Examples:
        # Unmerge a contributor entity and all profiles beneath it from a merged entity
        unmerge_entity_tree_by_contributor_tool("entity1", "entity2", "tenant_id")
        
        # Unmerge using entity prefixes
        unmerge_entity_tree_by_contributor_tool("entities/entity1", "entities/entity2", "tenant_id")
    """
    return await unmerge_entity_tree_by_contributor(origin_entity_id, contributor_entity_id, tenant_id)  

