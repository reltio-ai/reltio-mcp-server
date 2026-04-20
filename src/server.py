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
    unmerge_entity_tree_by_contributor,
    get_entity_with_matches,
    create_entities,
    get_entity_hops,
    get_entity_parents
)
from src.tools.match import (
    find_matches_by_match_score, 
    find_matches_by_confidence, 
    get_total_matches, 
    get_total_matches_by_entity_type,
    find_potential_matches,
    get_potential_match_apis
)
from src.tools.relation import get_relation_details, create_relationships, delete_relation, get_entity_relations, search_relations
from src.tools.search import search_entities
from src.tools.system import list_capabilities, health_check
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
from src.tools.activity import get_merge_activities, check_user_activity
from src.tools.interaction import get_entity_interactions, create_interactions
from src.tools.lookup import rdm_lookups_list
from src.tools.user import get_users_by_role_and_tenant, get_users_by_group
from src.tools.workflow import (
    get_user_workflow_tasks,
    reassign_workflow_task,
    get_possible_assignees,
    retrieve_tasks,
    get_task_details,
    start_process_instance,
    execute_task_action
)


# Configure logging
logger = logging.getLogger("mcp.server.reltio")

# Initialize MCP server
mcp = FastMCP(RELTIO_SERVER_NAME)

# Register tools with the MCP server
@mcp.tool()
async def search_entities_tool(filter: str, entity_type: str, 
                          tenant_id: str = RELTIO_TENANT, max_results: int = 10, sort: str = "", order: str = "asc", select: str = "uri,label", options: str = "ovOnly", activeness: str = "active", offset: int = 0) -> dict:
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
            filter = f"({filter}) and equals(type,'configuration/entityTypes/{entity_type}')"
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
async def update_entity_attributes_tool(entity_id: str, updates: List[Dict[str, Any]],options: str = "",always_create_dcr:bool = False,change_request_id:str = None, overwrite_default_crosswalk_value:bool = True,tenant_id: str = RELTIO_TENANT) -> dict:
    """Update specific attributes of an entity in Reltio.
    Before using this tool, ensure that the entity ID, attribute URIs and crosswalk are correct.
    
    Args:
        entity_id (str): Entity ID to update
        updates (List[Dict[str, Any]]): List of update operations as per Reltio API spec
        options (str): Optional comma-separated list of options. Available options:
        - sendHidden: Include hidden attributes in the response
        - updateAttributeUpdateDates: Update the updateDate and singleAttributeUpdateDates timestamps
        - addRefAttrUriToCrosswalk: Add reference attribute URIs to crosswalks during updates
        Example: options="sendHidden,updateAttributeUpdateDates,addRefAttrUriToCrosswalk"
        always_create_dcr (bool): If true, creates a DCR without updating the entity but default is false.
        change_request_id (str): If provided, all changes will be added to the DCR with this ID instead of updating the entity directly or create a new DCR.
        overwrite_default_crosswalk_value (bool): If true, overwrites the default crosswalk value.(TO BE USED MOST OF THE TIME, SKIP IF Changes Seem minimal)
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        Changed entity or data change request (if changeRequestId is defined or if you don't have access to update the object, but you do have permission to initiate a data change request).
        A dictionary containing the API response
    Raises:
        Exception: If there's an error during the update
    
    Instructions:
        # The following types of changes can be performed for an entity:
        #   - INSERT_ATTRIBUTE
        #   - UPDATE_ATTRIBUTE
        #   - DELETE_ATTRIBUTE
        #   - PIN_ATTRIBUTE
        #   - IGNORE_ATTRIBUTE
        #   - UPDATE_TAGS
        #   - UPDATE_ROLES
        #   - UPDATE_START_DATE
        #   - UPDATE_END_DATE
        #
        # Requirements for change objects:
        #   - All changes except DELETE_ATTRIBUTE must include a 'newValue' property,
        #     which specifies the new value for attributes, tags, or roles.
        #   - The following change types must include a 'uri' property (the URI of the attribute):
        #       INSERT_ATTRIBUTE, UPDATE_ATTRIBUTE, DELETE_ATTRIBUTE, PIN_ATTRIBUTE, IGNORE_ATTRIBUTE
        #   - The following change types must include a 'crosswalk' property (the crosswalk to update):
        #       INSERT_ATTRIBUTE, UPDATE_ATTRIBUTE, DELETE_ATTRIBUTE
    Examples:
        # Update FirstName and LastName attributes in entity with ID 000005KL
        [
            {
                "type": "INSERT_ATTRIBUTE",
                "uri": "entities/000005KL/attributes/FirstName",
                "newValue": [
                    {"value": "John"},
                    {"value": "Jonny"}
                ],
                "crosswalk": {
                    "type": "configuration/sources/HMS",       
                    "value": "000005KL",
                    "sourceTable": "testTable" #this is optional
                }
            },
            {
                "type": "INSERT_ATTRIBUTE",
                "uri": "entities/000005KL/attributes/Identifiers",
                "newValue": [
                    {
                        "value": {
                            "Type": [{"value": "Test"}],
                            "ID": [{"value": "1111"}]
                        }
                    }
                ],
                "crosswalk": {
                    "type": "configuration/sources/Reltio",
                    "value": "000005KL",
                    "sourceTable": "testTable" #this is optional
                }
            },
            {
                "type": "UPDATE_ATTRIBUTE",
                "uri": "entities/000005KL/attributes/LastName/ohg4GDs3",
                "newValue": {"value": "Smith"},
                "crosswalk": {
                    "type": "configuration/sources/HMS",
                    "value": "000005KL`",
                    "sourceTable": "testTable" #this is optional
                }
            },
            {
                "type": "DELETE_ATTRIBUTE",
                "uri": "entities/000005KL/attributes/MiddleName/Jk07LJ3d",
                "crosswalk": {
                    "type": "configuration/sources/HMS",
                    "value": "000005KL",
                    "sourceTable": "testTable" #this is optional
                }
            },
            {
                "type": "PIN_ATTRIBUTE",
                "uri": "entities/000005KL/attributes/ProductMetrics/IL98KH3f",
                "newValue": {"value": "true"}
            },
            {
                "type": "IGNORE_ATTRIBUTE",
                "uri": "entities/000005KL/attributes/ProductMetrics/IL98KH3f/Name/ohgGk4wd",
                "newValue": {"value": "false"}
            },
            {
                "type": "UPDATE_TAGS",
                "newValue": ["tag1", "tag2"]
            },
            {
                "type": "UPDATE_ROLES",
                "newValue": []
            },
            {
                "type": "UPDATE_START_DATE",
                "newValue": "1455702524000"
            },
            {
                "type": "UPDATE_END_DATE",
                "newValue": "1455702524000"
            }
        ]         
        # Update FirstName and LastName attributes in entity with ID 47uMxdm enabling trace
        entity_id="47uMxdm",
        updates=[
            {
                "type": "UPDATE_ATTRIBUTE",
                "uri": "entities/47uMxdm/attributes/FirstName/3Z3Tq6BBE",
                "newValue": [{"value": "Willy"}],
                "crosswalk": {"type": "configuration/sources/LNKD", "value": "47uMxdm"}
            },
            {
                "type": "UPDATE_ATTRIBUTE",
                "uri": "entities/47uMxdm/attributes/LastName/3Z3Tq6FRU",
                "newValue": [{"value": "Haarley"}],
                "crosswalk": {"type": "configuration/sources/LNKD", "value": "47uMxdm"}
            }
        ]
        update_entity_attributes_tool(entity_id, updates, "tenant_id")
    """
    
    result = await update_entity_attributes(entity_id, updates,options,always_create_dcr,change_request_id,overwrite_default_crosswalk_value,tenant_id)
    return result


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
async def get_relation_details_tool(relation_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
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
async def find_potential_matches_tool(search_type: str = "match_rule", filter: str = "", entity_type: str = "Individual",
                                     tenant_id: str = RELTIO_TENANT, max_results: int = 10, offset: int = 0,
                                     search_filters: str = "") -> dict:
    """Unified tool to find all potential matches by match rule, score range, or confidence level
    
    It provides a unified interface for finding potential matches using different search criteria.
    
    Args:
        search_type (str): Type of search - 'match_rule' (default), 'score', or 'confidence'
        filter (str): Filter value based on search_type:
            - For 'match_rule': match rule ID (e.g., 'BaseRule05')
            - For 'score': comma-separated start,end range (e.g., '50,100')
            - For 'confidence': confidence level (e.g., 'High confidence', 'Medium confidence', 'Low confidence', 
              'Strong matches', 'Super strong matches')
        entity_type (str): Entity type to filter by. Default to 'Individual'.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        max_results (int): Maximum number of results to return. Default to 10, and is capped at 10.
        offset (int): Starting index for paginated results. Use 0 for the first page.
        search_filters (str): Additional search filters to apply (e.g., 'equals(attributes.FirstName,John)')
    
    Returns:
        A dictionary containing the search results with matching entities
    
    Raises:
        Exception: If there's an error getting the matches
    
    Examples:
        # Find entities by match rule
        find_potential_matches_tool("match_rule", "BaseRule05", "Individual", "tenant_id", 10, 0, "")
        
        # Find entities by score range 
        find_potential_matches_tool("score", "50,100", "Individual", "tenant_id", 10, 0, "")
        
        # Find entities by confidence level with additional filters
        find_potential_matches_tool("confidence", "High confidence", "Individual", "tenant_id", 10, 0, "equals(attributes.FirstName,John)")
    """
    return await find_potential_matches(search_type, filter, entity_type, tenant_id, max_results, offset, search_filters)


@mcp.tool()
async def get_potential_matches_stats_tool(min_matches: int = 0, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get the total, entity-level, and match-rule-level counts of potential matches in the tenant
        
    Args:
        min_matches (int): Minimum number of matches to filter by. Returns total count of entities with greater 
                          than this many matches. Default to 0.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing:
        - total_matches: Total count of entities with matches above threshold
        - type: Breakdown of entities by entity type
        - matchRules: Breakdown of entities by match rule
    
    Raises:
        Exception: If there's an error getting the potential matches counts
    
    Examples:
        # Get total, entity-level, and match-rule-level counts of all entities with potential matches
        get_potential_matches_stats_tool(0, "tenant_id")
        
        # Get counts of entities with more than 5 potential matches
        get_potential_matches_stats_tool(5, "tenant_id")
    """
    return await get_potential_match_apis(min_matches, tenant_id)


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
async def get_entity_with_matches_tool(entity_id: str, attributes: List[str] = None, include_match_attributes: bool = True,
                                       match_attributes: List[str] = None, match_limit: int = 5, 
                                       tenant_id: str = RELTIO_TENANT) -> dict:
    """Get detailed information about a Reltio entity along with its potential matches.
    This tool unifies entity retrieval and match discovery in a single call.
    
    Args:
        entity_id (str): The ID of the entity to retrieve
        attributes (List[str]): Specific attributes to return for source entity. Empty/None returns all attributes.
            Examples: ["FirstName", "LastName", "Email"] or [] for all attributes
        include_match_attributes (bool): Whether to include full attribute details for matching entities. 
            Defaults to True.
        match_attributes (List[str]): Specific attributes to return for matching entities (only used if include_match_attributes=True). 
            Empty/None returns all attributes. Examples: ["FirstName", "LastName"] or [] for all attributes
        match_limit (int): Maximum number of potential matches to return (1-5). Defaults to 5.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A YAML formatted dictionary containing:
        - source_entity: Complete entity details including attributes and crosswalks
        - matches: Dictionary of matching entities with metadata (matchRules, matchScore, relevance, createdTime)
                    and optional full attributes based on include_match_attributes flag
        - total_matches: Total count of potential matches for this entity
    
    Examples:
        # Get entity with matches, including all attributes for both source and matches
        get_entity_with_matches_tool("entity_id", [], True, [], 5)
        
        # Get entity with matches, specific attributes for source, no match attributes
        get_entity_with_matches_tool("entity_id", ["FirstName", "LastName"], False, [], 3)
        
        # Get entity with matches, all source attributes, specific match attributes
        get_entity_with_matches_tool("entity_id", [], True, ["FirstName", "LastName", "Email"], 5)
    """
    return await get_entity_with_matches(entity_id, attributes, include_match_attributes, match_attributes, match_limit, tenant_id)


@mcp.tool()
async def create_entity_tool(entities: List[Dict[str, Any]], return_objects: bool = False, execute_lca: bool = True, 
                               tenant_id: str = RELTIO_TENANT) -> dict:
    """Create one or more entities in a Reltio tenant using the Entities API.
    
    This tool allows you to create one or more entities in your Reltio tenant. Each entity describes a data object 
    such as a person, organization, product, or location.Entities are comprised of properties such as URIs, type, 
    labels, roles, tags, attributes, crosswalks, and timestamps.

    IMPORTANT: To effectively use this tool with specific attributes, you should be familiar with the tenant's 
    data model to understand what attributes are available for each entity type. Consider using tenant configuration 
    tools to explore the data model first.
    
    Args:
        entities (List[Dict[str, Any]]): List of entity objects to create. Each entity must include:
            - type (str): Entity type (mandatory) - e.g., 'configuration/entityTypes/Individual'
            - attributes (dict): Optional attributes for the entity
            - crosswalks (list): Optional list of crosswalks for entity identification

            Example entity structures:
            
            Individual entity:
            {
                "type": "configuration/entityTypes/Individual",
                "attributes": {
                    "Name": [{"value": "Alex Sabel"}],
                    "NamePrefix": [{"value": "Mr."}],
                    "FirstName": [{"value": "Alex"}],
                    "LastName": [{"value": "Sabel"}],
                    "Address": [{
                        "value": {
                            "AddressLine1": [{"value": "123 Main Street"}],
                            "City": [{"value": "New York"}],
                            "State": [{"value": "NY"}],
                            "PostalCode": [{"value": {"PostalCode": [{"value": "10001"}]}}],
                            "Country": [{"value": "US"}],
                            "Active": [{"value": "true"}]
                        },
                        "label": "245 Highland Dr, Buffalo, NY, 14221-6856, United States",
                        "refRelation": {
                            "type": "configuration/sources/Reltio",
                            "objectURI": "relations/uri$$vTAtCJoHKhRXzI241757483548070"
                        },
                        "refEntity": {
                            "objectURI": "entities/0OkXAzQ",
                            "type": "configuration/entityTypes/Location"
                        }
                    }],
                    "Phone": [{
                        "value": {
                            "Number": [{"value": "(401) 854-2519"}]
                        }
                    }],
                    "Email": [{
                        "value": {
                            "Email": [{"value": "alex@gmail.com"}]
                        }
                    }],
                    "DoB": [{"value": "1999-07-15"}],
                    "YoB": [{"value": "1999"}]
                },
                "crosswalks": [
                    {
                        "type": "configuration/sources/CRM",
                        "value": "CRM123456"
                    }
                ]
            }
            
            Organization entity:
            {
                "type": "configuration/entityTypes/Organization",
                "attributes": {
                    "Name": [{"value": "Luke Corporation"}],
                    "Address": [{
                        "value": {
                            "Registered": [{"value": "true"}],
                            "Primary": [{"value": "true"}],
                            "Active": [{"value": "true"}]
                        },
                        "label": "2001 W 86th St Ste 100, Indianapolis, IN, 46260-1902, United States",
                        "refRelation": {
                            "type": "configuration/sources/Reltio",
                            "objectURI": "relations/uri$$3GXqISCewcGou8EL1757485592323"
                        },
                        "refEntity": {
                            "objectURI": "entities/0Ol7TRg",
                            "type": "configuration/entityTypes/Location"
                        }
                    }],
                    "Phone": [{
                        "value": {
                            "Number": [{"value": "(248) 299-0030"}],
                            "Active": [{"value": "true"}]
                        }
                    }],
                    "Email": [{
                        "value": {
                            "Email": [{"value": "sample@Luke.org"}],
                            "Active": [{"value": "true"}]
                        }
                    }],
                    "FoundedYear": [{"value": "2012"}]
                },
                "crosswalks": [
                    {
                        "type": "configuration/sources/ERP",
                        "value": "ORG789012"
                    }
                ]
            }
            
            Location entity:
            {
                "type": "configuration/entityTypes/Location",
                "attributes": {
                    "AddressLine1": [{"value": "811 New York Ave Ste 802"}],
                    "City": [{"value": "Brooklyn"}],
                    "ISO3166-2": [{"value": "US"}],
                    "ISO3166-3": [{"value": "USA"}],
                    "ISO3166-N": [{"value": "840"}],
                    "PostalCode": [{
                        "value": {
                            "PostalCode": [{"value": "11203-2720"}],
                            "Zip5": [{"value": "11203"}],
                            "Zip4": [{"value": "2720"}]
                        }
                    }],
                    "AdministrativeArea": [{"value": "NY"}],
                    "SubAdministrativeArea": [{"value": "Kings"}],
                    "SubBuilding": [{"value": "Ste 802"}],
                    "Locality": [{"value": "Brooklyn"}],
                    "Premise": [{"value": "811"}],
                    "County": [{"value": "United States"}],
                    "GeoLocation": [{
                        "value": {
                            "Latitude": [{"value": "40.654090"}],
                            "Longitude": [{"value": "-73.946750"}],
                            "GeoAccuracy": [{"value": "P4"}]
                        }
                    }],
                    "Street": [{"value": "New York Ave"}]
                },
                "crosswalks": [
                    {
                        "type": "configuration/sources/GIS",
                        "value": "LOC456789"
                    }
                ]
            }
            
        return_objects (bool): Whether the response contains created entities: true or false(default).
        execute_lca (bool): Whether to trigger all Lifecycle Actions during this request: true (default) or false.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A list containing the creation results for each entity with success/failure status
    
    Examples:
        # Create a single Individual entity
        create_entity_tool([{
            "type": "configuration/entityTypes/Individual",
            "attributes": {
                "FirstName": [{"value": "John"}],
                "LastName": [{"value": "Smith"}],
                "Email": [{"value": "john.smith@example.com"}]
            }
        }])
        
        # Create multiple entities at once
        create_entity_tool([
            {
                "type": "configuration/entityTypes/Individual",
                "attributes": {"FirstName": [{"value": "James"}], "LastName": [{"value": "Potter"}]}
            },
            {
                "type": "configuration/entityTypes/Individual",
                "attributes": {"FirstName": [{"value": "Harry"}], "LastName": [{"value": "Cameron"}]}
            }
        ])
    """
    return await create_entities(entities, return_objects, execute_lca, tenant_id)


@mcp.tool()
async def get_entity_graph_tool(entity_id: str, select: str = "label", graph_type_uris: str = "",
                                relation_type_uris: str = "", entity_type_uris: str = "", deep: int = 1,
                                max_results: int = 100, activeness_enabled: bool = True, return_inactive: bool = False,
                                filter_last_level: bool = True, return_data_anyway: bool = False, options: str = "ovOnly",
                                tenant_id: str = RELTIO_TENANT) -> dict:
    """Get entity graph (hops) for a specific entity with comprehensive filtering and traversal options
    
    This tool retrieves the graph structure around an entity by traversing relationships to connected entities.
    It supports various filtering options to control which entities and relations are included in the traversal.
    
    IMPORTANT: To effectively use this tool with specific attributes, you should be familiar with the tenant's 
    data model to understand what attributes are available for each entity type.
    
    Args:
        entity_id (str): The ID of the entity to get graph for (can include 'entities/' prefix or just the ID)
        select (str): Comma-separated list of properties to return in response. Defaults to "label".
            Available options: label, secondaryLabel, entities.attributes, relations.attributes, 
            entities.attributes.SpecificAttribute
        graph_type_uris (str): Comma-separated list of graph type URIs for graphs to be traversed.
            Examples: "Hierarchy", "Hierarchy,Network"
        relation_type_uris (str): Comma-separated list of relation type URIs for relations to be traversed.
            Examples: "OrganizationHierarchy", "IndividualEmployer,OrganizationAffiliation"
        entity_type_uris (str): Comma-separated list of entity type URIs for entities to be traversed.
            Examples: "Individual", "Individual,Organization"
        deep (int): Limits traversing deep levels. Default is 1. Higher values traverse more relationship levels.
        max_results (int): Limits the amount of entities to be returned. Default is 100, maximum is 1500.
        activeness_enabled (bool): Flag to determine whether to return only active entities and relations. Default is True.
        return_inactive (bool): Flag to traverse inactive entities/relationships. Default is False.
        filter_last_level (bool): Flag to NOT count relationships from the last level. Default is True.
        return_data_anyway (bool): Flag to return partial data when credit consumption limit is exceeded. Default is False.
        options (str): Comma-separated list of options. Default is "ovOnly".
            Available: sendHidden, ovOnly, nonOvOnly, sendMasked, showAppliedSurvivorshipRules
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value
    
    Returns:
        A YAML formatted dictionary containing relations, entities, and dataComplete flag
    
    Examples:
        # Get basic entity graph with default settings (1 level deep, labels only)
        get_entity_graph_tool("entities/123")
        
        # Get deeper graph traversal (2 levels) with more entities
        get_entity_graph_tool("entities/123", deep=2, max_results=200)
        
        # Filter by specific relation types
        get_entity_graph_tool("entities/123", relation_type_uris="OrganizationHierarchy,OrganizationAffiliation")
    """
    return await get_entity_hops(entity_id, select, graph_type_uris, relation_type_uris, entity_type_uris, 
                                 deep, max_results, activeness_enabled, return_inactive, filter_last_level,
                                 return_data_anyway, options, tenant_id)


@mcp.tool()
async def get_entity_parents_tool(entity_id: str, graph_type_uris: str, select: str = "uri,label,type,secondaryLabel",
                                  options: str = "", tenant_id: str = RELTIO_TENANT) -> dict:
    """This tool queries the Reltio API to find all parent paths for a given entity, traversing the specified graph types.
    It returns detailed information about each path from the entity to its parents, including the entities and relations involved.
    A “parent” in Reltio is the upstream (super) entity linked to a another entity through a configured hierarchical Graph type (e.g., Hierarchy,OrganizationHierarchy,BusinessHierarchy, etc), as defined in your tenant’s model.
    This function is useful for understanding hierarchical relationships, such as organizational structures or reference data hierarchies etc.

    Args:
        entity_id (str): The ID of the entity to get parents for
        graph_type_uris (str): Comma-separated list of graph type URIs to traverse (required)
        select (str): Comma-separated list of properties to include in the response. Defaults to "uri,label,type,secondaryLabel"
        options (str): Comma-separated list of options affecting the response content:
            - sendHidden: Include hidden attributes in the response
            - ovOnly: Return only attribute values with the ov=true flag
            - nonOvOnly: Return only attribute values with the ov=false flag
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value
        trace (bool): if True, return the metadata as toolName, execTime, requestData, responseData.
        activity_client (str): The client identifier for activity logging. Defaults to ACTIVITY_LOG_LABEL.
    Response:
        parentPaths - this item is an array of arrays, each entire array is a path from the node to its parents, each element of an array contains the following items:
            entityUri - URI of an entity in the path
            relationsUris - URIs of relations from current entity to its children
            hasSelfRelation - boolean flag saying if entity has at least one self relation
            entities - this is a dictionary of all entities used in paths
            relations - this is a dictionary of all relations used in paths
    Examples:
        # Get the parents of an entity with default settings
        get_entity_parents_tool("e41", "Hierarchy")
        response: {
                "parentPaths": [
                    [
                    { "entityUri": "entities/e41" },
                    { "entityUri": "entities/e33", "relationsUris": ["relations/r_33_41"] }
                    ]
                ],
                "entities": {
                    "entities/e41": { "uri": "entities/e41", "type": "configuration/entityTypes/Individual" },
                    "entities/e33": { "uri": "entities/e33", "type": "configuration/entityTypes/Individual" }
                },
                "relations": {
                    "relations/r_33_41": {
                    "uri": "relations/r_33_41",
                    "type": "configuration/relationTypes/Family",
                    "direction": "bidirectional"
                    }
                }
                }
        # Get the parents of an entity with specific properties and options
        get_entity_parents_tool("entity_id", "OrganizationHierarchy,Hierarchy", "type,label", "sendHidden,ovOnly")
    """
    return await get_entity_parents(entity_id, graph_type_uris, select, options, tenant_id)


# ============================================================================
# NEW RELATION TOOLS
# ============================================================================

@mcp.tool()
async def create_relationships_tool(relations: List[Dict[str, Any]], options: Optional[str] = None, 
                                   tenant_id: str = RELTIO_TENANT) -> dict:
    """Create relationships between entities in Reltio
    
    This tool allows you to create one or more relationships between entities using the Reltio Relations API.
    Each relationship connects a startObject to an endObject and can include optional crosswalks for enhanced data lineage.
    
    Args:
        relations (list): List of relation objects to create. Each relation must include:
            - type (str): Relation type (mandatory) - e.g., 'configuration/relationTypes/OrganizationIndividual'
            - startObject (dict): Start object with:
                - type (str): Entity type (mandatory) - e.g., 'configuration/entityTypes/Organization'  
                - objectURI (str): Object URI (optional) - e.g., 'entities/e1'
                - crosswalks (list): List of crosswalks (optional), each with:
                    - type (str): Crosswalk type (defaults to 'configuration/sources/Reltio')
                    - sourceTable (str): Source table name (defaults to empty string, only included in payload if not empty)
                    - value (str): Crosswalk value (defaults to unique UUID4)
            - endObject (dict): End object with:
                - type (str): Entity type (mandatory) - e.g., 'configuration/entityTypes/Individual'
                - objectURI (str): Object URI (optional) - e.g., 'entities/e2' 
                - crosswalks (list): List of crosswalks (optional), each with:
                    - type (str): Crosswalk type (defaults to 'configuration/sources/Reltio')
                    - sourceTable (str): Source table name (defaults to empty string, only included in payload if not empty)
                    - value (str): Crosswalk value (defaults to unique UUID4)
            - crosswalks (list): Optional list of crosswalks for the relation itself, each with:
                - type (str): Crosswalk type (defaults to 'configuration/sources/Reltio')
                - sourceTable (str): Source table name (defaults to empty string, only included in payload if not empty)
                - value (str): Crosswalk value (defaults to unique UUID4)
        options (str, optional): Optional comma-separated list of options such as:
            - partialOverride: Allows partial override of existing relationships
            - directMatchMode: Uses direct matching mode for entity resolution
            - ignoreMissingObjects: Ignores missing objects during relationship creation
            - skipEntityResolution: Skips entity resolution and uses provided URIs directly
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the relationship creation results
    
    Raises:
        Exception: If there's an error creating the relationships
    
    Business Rules:
        - Type is mandatory in both startObject and endObject
        - Either objectURI or crosswalks (or both) must be provided for startObject and endObject
        - If both are missing, a validation error will occur
    
    Examples:
        # Create a relationship using entity URIs
        create_relationships_tool([{
            "type": "configuration/relationTypes/OrganizationIndividual",
            "startObject": {
                "type": "configuration/entityTypes/Organization",
                "objectURI": "entities/e1"
            },
            "endObject": {
                "type": "configuration/entityTypes/Individual",
                "objectURI": "entities/e2"
            }
        }])
        
        # Create a relationship using crosswalks
        create_relationships_tool([{
            "type": "configuration/relationTypes/OrganizationIndividual",
            "crosswalks": [{
                "type": "configuration/sources/Agent",
                "value": "R|4QrP0xy|185asgAe"
            }],
            "startObject": {
                "type": "configuration/entityTypes/Organization",
                "crosswalks": [{
                    "type": "configuration/sources/Reltio",
                    "value": "4QrP0xy"
                }]
            },
            "endObject": {
                "type": "configuration/entityTypes/Individual",
                "crosswalks": [{
                    "type": "configuration/sources/RFM",
                    "value": "CH|340"
                }]
            }
        }], options="partialOverride")
        
        # Create multiple relationships at once
        create_relationships_tool([
            {
                "type": "configuration/relationTypes/OrganizationIndividual",
                "startObject": {
                    "type": "configuration/entityTypes/Organization",
                    "objectURI": "entities/org1"
                },
                "endObject": {
                    "type": "configuration/entityTypes/Individual",
                    "objectURI": "entities/person1"
                }
            },
            {
                "type": "configuration/relationTypes/OrganizationIndividual", 
                "startObject": {
                    "type": "configuration/entityTypes/Organization",
                    "objectURI": "entities/org1"
                },
                "endObject": {
                    "type": "configuration/entityTypes/Individual",
                    "objectURI": "entities/person2"
                }
            }
        ], options="partialOverride,directMatchMode")
    """
    return await create_relationships(relations, options, tenant_id)

@mcp.tool()
async def delete_relation_tool(relation_id: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Delete a relation object from a tenant using the DELETE operation
    
    This tool deletes a relation object by its URI using the Reltio Relations DELETE API.
    According to Reltio documentation, it sends a DELETE request to {TenantURL}/{relation object URI}.
    
    Args:
        relation_id (str): The ID of the relation to delete (e.g., 'r1', '0ZbpiBc')
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the result of the delete operation with:
        - status: result of operation; possible values are "OK" or "failed"  
        - error: if object can't be deleted for some reason. Contains details of the problem.
    
    Raises:
        Exception: If there's an error deleting the relation
    
    Examples:
        # Delete relation by ID
        delete_relation_tool("r1", "tenant_id")
        
        # Delete another relation
        delete_relation_tool("0ZbpiBc", "tenant_id")
    """
    return await delete_relation(relation_id, tenant_id)

@mcp.tool()
async def get_entity_relations_tool(entity_id: str, entity_types: List[str], sort_by: str = "",
                                   in_relations: Optional[List[str]] = None, out_relations: Optional[List[str]] = None,
                                   offset: int = 0, max: int = 10, show_relationship: str = "",
                                   show_entity: str = "", next_entry: str = "", groups: Optional[List[str]] = None,
                                   filter: str = "", relation_filter: str = "", return_objects: bool = False,
                                   return_dates: bool = False, return_labels: bool = True, id: str = "",
                                   suggested: Optional[List[str]] = None, limit_credits_consumption: bool = False,
                                   return_data_anyway: bool = False, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get entity connections/relations using Reltio connections API
    
    This tool retrieves connections (relations) for a specific entity in Reltio.
    It provides detailed information about how entities are connected to each other through relationships.
    The tool supports advanced filtering, sorting, and pagination options.
    
    Args:
        entity_id (str): The ID of the entity to get connections for (mandatory)
        entity_types (list): List of entity types that will be returned (mandatory). 
            Example: ["configuration/entityTypes/Individual", "configuration/entityTypes/Organization"]
        sort_by (str): How to sort the results. Options include:
            - "groups" - Sorts by the group member label
            - "relations" - Sorts by the relation label or URI
            - "consolidatedRating" - Sorts by the field's value
            - "relation.type" - Sorts by the relation type
            - "relation.attributes.<attribute>" - Sorts by specified relation attribute
            - "relation.activeness.startDate" or "relation.activeness.endDate" - Sorts by relation dates
            - "suggested" - Applies sorting when suggested buckets are present
            - "relation.label" - Uses the same sorting behavior as relations
            - "entities" (default) - Sorts by the entity label
        in_relations (list): Types of relations that have endEntity equal to current entity. 
            Can be list of strings or list of objects with "uri" and "label" keys
        out_relations (list): Types of relations that have startEntity equal to current entity.
            Can be list of strings or list of objects with "uri" and "label" keys
        offset (int): First element in the request (default = 0, for pagination)
        max (int): Maximum number of elements to return (default = 10, maximum = 1000)
        show_relationship (str): URI of relationship to show specific page of connections
        show_entity (str): URI of connected entity to show specific page of connections
        next_entry (str): Next connection specification if connection path does not equal one hop
        groups (list): List of group types that have entities as a member
        filter (str): Entity filter conditions. Supported filter conditions include:
            - equals(property, value) — exact match (case-insensitive)
            - equalsCaseSensitive(property, value) — exact match with case sensitivity
            - containsWordStartingWith(property, value) — find words that start with specified text
            - startsWith(property, value) — find values that begin with specified text
            - fullText(property, value) — full-text search across indexed fields
            - fuzzy(property, value) — approximate text matching with typos allowed
            - missing(property) — find entities where property is null/empty
            - exists(property) — find entities where property has any value
            - in(property, comma-separated-values) — match any value from a list
            - lte(property, value) — less than or equal to numeric/date values
            - gte(property, value) — greater than or equal to numeric/date values
            - lt(property, value) — less than numeric/date values
            - gt(property, value) — greater than numeric/date values
            - range(property, start, end) — find values within a range
            - not(condition) — negate any filter condition
            - contains(property, '*value' or '?value') — wildcard pattern matching
            
            Filter examples:
            - Entity and Relationship Labels: 'startsWith(entity.label, "iri") and startsWith(relation.label, "fath")'
            - Relationship Attributes: 'equals(relation.attributes.ORG_RSHP_TYP_CD, "DOMESTICULTIMATE")'
            - Entity Attributes: 'equals(attributes.FirstName, "John") and equals(attributes.Country, "US")'
            
        relation_filter (str): Filter condition for relations (e.g., 'equals(attributes.AddressRank,"1")')
        return_objects (bool): Whether to include complete object data in results (default = false)
        return_dates (bool): Whether to include activeness (startDate, endDate) attributes (default = false)
        return_labels (bool): Whether to include entityLabel and relationLabel fields (default = true)
        id (str): Identifier for this connections group (used with suggested parameter)
        suggested (list): List of other bucket IDs to mix into this bucket
        limit_credits_consumption (bool): Whether to limit credits consumption (default = false)
        return_data_anyway (bool): Whether to return data anyway (default = false)
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the entity connections/relations data in YAML format
    
    Raises:
        Exception: If there's an error retrieving the entity relations
    
    Examples:
        # Basic usage - get connections for an entity
        get_entity_relations_tool("0Gs6OmA", ["configuration/entityTypes/Individual"])
        
        # Get connections with specific relation types
        get_entity_relations_tool(
            "0Gs6OmA", 
            ["configuration/entityTypes/Individual"],
            in_relations=["configuration/relationTypes/OrganizationIndividual"],
            out_relations=["configuration/relationTypes/IndividualHasAddress"]
        )
        
        # Get connections with sorting and pagination
        get_entity_relations_tool(
            "0Gs6OmA", 
            ["configuration/entityTypes/Individual", "configuration/entityTypes/Organization"],
            sort_by="entity.label",
            offset=0,
            max=20,
            return_dates=True
        )
        
        # Get connections with filtering
        get_entity_relations_tool(
            "0Gs6OmA", 
            ["configuration/entityTypes/Individual"],
            filter='equals(attributes.FirstName,"John")',
            relation_filter='equals(attributes.AddressRank,"1")'
        )
    """
    return await get_entity_relations(entity_id, entity_types, sort_by, in_relations, out_relations, offset, 
                                     max, show_relationship, show_entity, next_entry, groups, filter, 
                                     relation_filter, return_objects, return_dates, return_labels, id, 
                                     suggested, limit_credits_consumption, return_data_anyway, tenant_id)

@mcp.tool()
async def relation_search_tool(filter: str = "", select: str = "", max: int = 10, offset: int = 0,
                                sort: str = "", order: str = "asc", options: str = "",
                                activeness: str = "active", tenant_id: str = RELTIO_TENANT) -> dict:
    """Search for relationships in a tenant using the Relation Search API
    
    This tool searches for relationships by their start and/or end objects, attribute values, 
    tags, or type. It only works when relations indexing is enabled for the tenant.
    
    Important: This API can search Relations Records up to a maximum number of 10,000 items.
    Only tenants where relations indexing is enabled are able to use this API.
    
    Args:
        filter (str): Enables relations filtering by a condition. Format: filter=({Condition Type}[AND/OR {Condition Type}]*)
            Supported filter condition types include:
            - equals(property, value) — exact match (case-insensitive)
            - equalsCaseSensitive(property, value) — exact match with case sensitivity
            - containsWordStartingWith(property, tokenized value) — prefixed condition
            - startsWith(property, stricted value) — prefixed condition
            - fullText(property, value) — full-text search
            - fuzzy(property, value) — fuzzy match with minor differences allowed
            - missing(property) — fields with no values or empty values
            - exists(property) — fields with non-empty values
            - range(property, start, end) — property between start and end values
            - lte(property, value) — less than or equal to
            - gte(property, value) — greater than or equal to
            - lt(property, value) — less than
            - gt(property, value) — greater than
            - contains(property, *value or ?value) — wildcard pattern matching
            - in(property, comma-separated-values) — match any value from a list
            - not(condition) — negate any filter condition
            
            Filter examples:
            - Filter by start entity: filter="(equals(startObject,'entities/1'))"
            - Return relations of an entity: filter="(equals(startObject,'entities/1') or equals(endObject,'entities/1'))"
            - Filter by relationship type: filter="(equals(type,'configuration/relationTypes/Spouse'))"
            - Filter by attribute: filter="(equals(attributes.Commenters,'John'))"
            - Complex filter: filter="(equals(startObject,'entities/1') and equals(type,'configuration/relationTypes/HasAddress'))"
            
        select (str): Comma-separated list of properties from relation structure to return.
            Available properties: uri, type, startObject, endObject, attributes, crosswalks, 
            createdBy, createdTime, updatedTime, startDate, endDate
            Example: "uri,startObject,endObject"
            
        max (int): Maximum number of relations to return (default=10, maximum=10000)
        
        offset (int): Starting element in result set for pagination (default=0).
            Note: offset + max must not exceed 10000
            
        sort (str): Attribute or list of attributes for ordering. Multiple attributes can be 
            combined using & sign (encoded as %26 in request).
            Examples: "uri", "uri&startObject"
            
        order (str): Sort order: 'asc' (ascending, default) or 'desc' (descending)
        
        options (str): Comma-separated list of options affecting relation's JSON content:
            - nonOvOnly: Only attributes with ov="false" will be present
            - ovOnly: Only attributes with ov="true" will be present  
            - searchByOv: Search by attributes with Operational Values (OV) only
            - sendHidden: Include hidden attributes in response
            Example: "sendHidden,ovOnly"
            
        activeness (str): Activeness filter:
            - 'active' (default): Search among active relations only
            - 'all': Search among all (active/expired) relations
            - 'not_active': Search among expired relations only
            
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the search results in YAML format
    
    Raises:
        Exception: If there's an error searching relations or if relations indexing is not enabled
    
    Examples:
        # Search for all relationships of a specific entity
        relation_search_tool(filter="(equals(startObject,'entities/1') or equals(endObject,'entities/1'))")
        
        # Search for relationships by type
        relation_search_tool(filter="(equals(type,'configuration/relationTypes/Spouse'))")
        
        # Search with pagination and sorting
        relation_search_tool(
            filter="(equals(startObject,'entities/2'))",
            max=20,
            offset=0,
            sort="uri",
            order="desc"
        )
        
        # Search with specific fields selection
        relation_search_tool(
            filter="(equals(type,'configuration/relationTypes/HasAddress'))",
            select="uri,startObject,endObject",
            max=5
        )
        
        # Search for relations with specific attributes
        relation_search_tool(
            filter="(equals(attributes.Commenters,'John') and exists(attributes.Title))"
        )
        
        # Search for relations created after a specific time
        relation_search_tool(
            filter="(gt(createdTime,1540805153527))",
            sort="createdTime",
            order="desc"
        )
        
        # Search with options to include hidden attributes
        relation_search_tool(
            filter="(equals(startObject,'entities/1'))",
            options="sendHidden,ovOnly",
            activeness="all"
        )
    """
    return await search_relations(filter, select, max, offset, sort, order, options, activeness, tenant_id)

# ============================================================================
# NEW ACTIVITY TOOLS
# ============================================================================

@mcp.tool()
async def check_user_activity_tool(username: str, days_back: int = 7, tenant_id: str = RELTIO_TENANT) -> dict:
    """Check if a user has been active in the system within a specified number of days
    
    Args:
        username (str): Username to check for activity
        days_back (int): Number of days to look back for activity. Defaults to 7 days.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing activity status (is_active: true/false) and details of last activity if found:
        - is_active (bool): Whether the user was active within the specified time period
        - last_activity (dict): Details of the most recent activity if found, containing:
            - timestamp (int): Timestamp of the activity
            - event_type (str): Type of activity event
            - entity_type (str): Entity type involved in the activity
            - details (dict): Additional activity details
    
    Raises:
        Exception: If there's an error checking user activity
    
    Examples:
        # Check if user was active in last 7 days (default)
        check_user_activity_tool("user.name@company.com")
        
        # Check if user was active in last 14 days
        check_user_activity_tool("user.name@company.com", days_back=14)
        
        # Check if user was active in last 30 days for specific tenant
        check_user_activity_tool("john.doe@company.com", days_back=30, tenant_id="MQQzACV65IZ7MmL")
    """
    return await check_user_activity(username, days_back, tenant_id)

# ============================================================================
# NEW INTERACTION TOOLS
# ============================================================================

@mcp.tool()
async def get_entity_interactions_tool(entity_id: str, max: int = 50, offset: int = 0, 
                                      order: str = "asc", sort: str = "", filter: str = "",
                                      tenant_id: str = RELTIO_TENANT) -> dict:
    """Get interactions for a Reltio entity by ID
    
    This tool retrieves the list of interactions for an entity (interactions where this entity is the member).
    Available only in tenants provisioned for Reltio Intelligent 360.
    
    Args:
        entity_id (str): The ID of the entity to get interactions for
        max (int): Maximum number of interactions to return. Default is 50
        offset (int): Starting index for paginated results. Default is 0
        order (str): Sort order - 'asc' or 'desc'. Default is 'asc'
        sort (str): Field to sort by. Default sorting is by timestamp
        filter (str): Filter conditions for interactions. Supported filter conditions include:
            - equals(property, value) — exact match (case-insensitive)
            - equalsCaseSensitive(property, value) — exact match with case sensitivity
            - containsWordStartingWith(property, value) — find words that start with specified text
            - startsWith(property, value) — find values that begin with specified text
            - fullText(property, value) — full-text search across indexed fields
            - fuzzy(property, value) — approximate text matching with typos allowed
            - missing(property) — find entities where property is null/empty
            - exists(property) — find entities where property has any value
            - in(property, comma-separated-values) — match any value from a list
            - lte(property, value) — less than or equal to numeric/date values
            - gte(property, value) — greater than or equal to numeric/date values
            - lt(property, value) — less than numeric/date values
            - gt(property, value) — greater than numeric/date values
            - range(property, start, end) — find values within a range
            - not(condition) — negate any filter condition
            - contains(property, '*value' or '?value') — wildcard pattern matching
            
            Property filtering examples:
            - equals(type, "configuration/interactionTypes/Meeting") — Filter by interaction type
            - equals(attributes.Status, "Completed") — Filter by interaction status
            
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the interactions, totalFetched, and fetchedAll information
    
    Raises:
        Exception: If there's an error getting the entity interactions
    
    Examples:
        # Get interactions for an entity with default parameters
        get_entity_interactions_tool("entity_id")
        
        # Get interactions with filtering and pagination
        get_entity_interactions_tool(
            "entity_id", 
            max=10, 
            offset=0, 
            filter='equals(type,"configuration/interactionTypes/Meeting")'
        )
        
        # Filter by interaction status
        get_entity_interactions_tool(
            "entity_id",
            filter='equals(attributes.Status, "Completed")'
        )
    """
    return await get_entity_interactions(entity_id, max, offset, order, sort, filter, tenant_id)

@mcp.tool()
async def create_interaction_tool(interactions: List[Dict[str, Any]], source_system: str = "configuration/sources/Reltio",
                                  crosswalk_value: str = "", return_objects: bool = True, options: str = "",
                                  tenant_id: str = RELTIO_TENANT) -> dict:
    """Create interactions in the Reltio Platform
    
    This tool creates a collection of interactions in the Reltio Platform according to the JSON object definition.
    Available only in tenants provisioned for Reltio Intelligent 360.
    
    Args:
        interactions (List[Dict[str, Any]]): A JSON array with objects representing interactions to be created. 
            Each object must have the type property but may not have the URI, crosswalks, and referencedCrosswalks 
            properties (these properties are provided/generated by Reltio API).
            
        source_system (str): This parameter indicates the source system that this request is representing. 
            For example, configuration/sources/Reltio indicates that the data is not loaded from other source systems 
            and is instead created in the Reltio Platform directly. Default is 'configuration/sources/Reltio'.
            
        crosswalk_value (str): This parameter indicates the identifier of an interaction object in the source system. 
            Use this parameter to specify the crosswalkValue when there is no crosswalk in the request body. Optional.
            
        return_objects (bool): This parameter specifies if the response must include the created objects. 
            Use this parameter to display only the object URIs in the response and not the whole object. 
            The default value is true.
            
        options (str): This parameter includes or excludes the hidden attributes in the response using the sendHidden option. 
            By default, the sendHidden option is disabled, that is, the response will not contain the hidden attributes.
            If you want to view the hidden attributes, set the option parameter to sendHidden in the request query. Optional.
            
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the results for each interaction creation attempt. Each result has the following properties:
        - index: The index of an interaction object in the JSON array to be created (required)
        - URI: URI of the interaction object that is created (returned only if an object was created successfully)
        - error: Returned if an object cannot be created for some reason. Contains details of the problem
        - warning: Indicates that an object was created but there were some problems
        - status: Indicates the result of an API request. Possible values are OK and failed
    
    Raises:
        Exception: If there's an error creating the interactions
    
    Notes:
        - Interactions must have unique IDs across all uploads. Uploading interactions with duplicate IDs 
          can result in indexing errors and unexpected behavior in search results.
        - Attempting to create an interaction with an existing crosswalk returns an error.
        - Each interaction includes the required type property.
    
    Examples:
        # Create a simple email interaction
        create_interaction_tool([{
            "type": "configuration/interactionTypes/Email",
            "attributes": {"DateEmailSent": [{"value": "2025-01-02"}]},
            "members": {
                "Individual": {
                    "type": "configuration/interactionTypes/Email/memberTypes/Individual",
                    "members": [{"objectURI": "entities/0U3rzjF"}]
                }
            }
        }])
        
        # Create a lunch meeting interaction using objectURI
        create_interaction_tool([{
            "type": "configuration/interactionTypes/Lunch",
            "timestamp": 1338580800000,
            "attributes": {
                "Place": [{"value": "Shire, Bag End in Hobbiton"}],
                "Notes": [{"value": "All participants eat Lembas"}]
            },
            "members": {
                "Organizers": {
                    "type": "configuration/interactionTypes/Meeting/memberTypes/Organizers",
                    "members": [{"objectURI": "entities/30000"}]
                },
                "Participants": {
                    "type": "configuration/interactionTypes/Meeting/memberTypes/Participants",
                    "members": [
                        {"objectURI": "entities/10000"},
                        {"objectURI": "entities/10001"}
                    ]
                }
            }
        }])
        
        # Create interaction using crosswalks
        create_interaction_tool([{
            "type": "configuration/interactionTypes/Meeting",
            "timestamp": 1338580800000,
            "attributes": {"Location": [{"value": "Conference Room A"}]},
            "members": {
                "Organizers": {
                    "type": "configuration/entityTypes/Organizers",
                    "members": [{
                        "crosswalks": [{
                            "type": "configuration/sources/Salesforce",
                            "value": "EMP_600000"
                        }]
                    }]
                }
            }
        }])
    """
    return await create_interactions(interactions, source_system, crosswalk_value, return_objects, options, tenant_id)

# ============================================================================
# NEW LOOKUP TOOLS
# ============================================================================

@mcp.tool()
async def rdm_lookups_list_tool(lookup_type: str, tenant_id: str = RELTIO_TENANT, max_results: int = 10,
                                display_name_prefix: str = "") -> dict:
    """List lookups based on the given RDM lookup type
    
    This tool allows you to retrieve a list of lookups for a specific RDM lookup type 
    using the Reltio Reference Data Management (RDM) API.
    
    Args:
        lookup_type (str): RDM lookup type to filter by. Must start with 'rdm/lookupTypes/'.
            Examples: 
            - 'rdm/lookupTypes/VistaVegetarianOrVegan'
            - 'rdm/lookupTypes/CountryCode'
            - 'rdm/lookupTypes/StateProvince'
            - 'rdm/lookupTypes/CurrencyCode'
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        max_results (int): Maximum number of results to return. Defaults to 10.
        display_name_prefix (str): Display name prefix to filter by. Defaults to "".
    
    Returns:
        A dictionary containing the list of lookups for the specified type
    
    Raises:
        Exception: If there's an error retrieving the lookups
    
    Examples:
        # Get all vegetarian/vegan lookups
        rdm_lookups_list_tool("rdm/lookupTypes/VistaVegetarianOrVegan")
        
        # Get country code lookups for a specific tenant
        rdm_lookups_list_tool("rdm/lookupTypes/CountryCode", "MQQzACV65IZ7MmL")
        
        # Get state/province lookups
        rdm_lookups_list_tool("rdm/lookupTypes/StateProvince")
        
        # Get currency code lookups
        rdm_lookups_list_tool("rdm/lookupTypes/CurrencyCode")
    """
    return await rdm_lookups_list(lookup_type, tenant_id, max_results, display_name_prefix)

# ============================================================================
# NEW USER TOOLS
# ============================================================================

@mcp.tool()
async def get_users_by_role_and_tenant_tool(role: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get users by role and tenant
    
    This tool retrieves the list of users that have access to the current tenant with a specific role.
    As a result, it will return a list of users that have the role and the tenant assigned, along with 
    information about each user (user enabled or not, last login date, groups, etc).
    Use this tool to get users with a role and tenant assigned.
    
    Args:
        role (str): Role to filter by (e.g., 'ROLE_REVIEWER', 'ROLE_READONLY', 'ROLE_USER', 'ROLE_API')
        tenant_id (str): Tenant ID to filter by. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing filtered users information with role and tenant details
    
    Raises:
        Exception: If there's an error getting the users by role and tenant
    
    Examples:
        # Get all reviewers for a specific tenant
        get_users_by_role_and_tenant_tool("ROLE_REVIEWER", "MQQzACV65IZ7MmL")
        
        # Get all readonly users for current tenant
        get_users_by_role_and_tenant_tool("ROLE_READONLY", "tenant_id")
        
        # Get all API users for a specific tenant
        get_users_by_role_and_tenant_tool("ROLE_API", "2CWGQeoKOqUJ25n")
        
        # Get all users with user role
        get_users_by_role_and_tenant_tool("ROLE_USER", "tenant_id")
    """
    return await get_users_by_role_and_tenant(role, tenant_id)

@mcp.tool()
async def get_users_by_group_and_tenant_tool(group: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Get users by group and tenant
    
    This tool retrieves the list of users that have access to the current tenant and filters it by the ones 
    who belong to the selected group. As a result, it will return a list of users with access to the selected 
    tenant and under the selected group, along with information about each user (user enabled or not, last login 
    date, other groups, etc).
    Use this tool to get users with specific group for a given tenant.
    
    Args:
        group (str): Group to filter by (e.g., 'GROUP_LOCAL_RO_ALL', 'GROUP_LOCAL_DA_PT', 'Admin_User_Dev2')
        tenant_id (str): Tenant ID to filter by. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing filtered users information with group details
    
    Raises:
        Exception: If there's an error getting the users by group
    
    Examples:
        # Get all users in a specific group
        get_users_by_group_and_tenant_tool("GROUP_LOCAL_RO_ALL","tenant_id")
        
        # Get all users in a specific region group
        get_users_by_group_and_tenant_tool("GROUP_LOCAL_DA_PT","tenant_id")
        
        # Get all admin users in a dev environment
        get_users_by_group_and_tenant_tool("Admin_User_Dev2","tenant_id")
        
        # Get all data steward users for US dev environment
        get_users_by_group_and_tenant_tool("GROUP_LOCAL_DS_US_DEV2","tenant_id")
    """
    return await get_users_by_group(group, tenant_id)

# ============================================================================
# NEW WORKFLOW TOOLS
# ============================================================================

@mcp.tool()
async def get_user_workflow_tasks_tool(assignee: str, tenant_id: str = RELTIO_TENANT, offset: int = 0, 
                                      max_results: int = 10) -> dict:
    """Get workflow tasks for a specific user with total count and detailed task information
    
    Args:
        assignee (str): Username/assignee to get tasks for.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        offset (int): Starting index for paginated results. Use 0 for the first page. Defaults to 0.
        max_results (int): Maximum number of results to return. Defaults to 10. Set to 1 if you only need the total count.
    
    Returns:
        A dictionary containing total_tasks count and detailed workflow tasks with: 
        processType, taskType, createTime, dueDate, taskId
    
    Raises:
        Exception: If there's an error getting the workflow tasks
    
    Examples:
        # Get tasks for user with default pagination
        get_user_workflow_tasks_tool("girish.kalburgi.vistadcr1", "MQQzACV65IZ7MmL")
        
        # Get just one task assigned to user
        get_user_workflow_tasks_tool("girish.kalburgi.vistadcr1", "MQQzACV65IZ7MmL", max_results=1)
        
        # Get next page of tasks assigned to user
        get_user_workflow_tasks_tool("girish.kalburgi.vistadcr1", "MQQzACV65IZ7MmL", offset=10)
        
        # Get more tasks per page assigned to user
        get_user_workflow_tasks_tool("girish.kalburgi.vistadcr1", "MQQzACV65IZ7MmL", max_results=25)
    """
    return await get_user_workflow_tasks(assignee, tenant_id, offset, max_results)

@mcp.tool()
async def reassign_workflow_task_tool(task_id: str, assignee: str, tenant_id: str = RELTIO_TENANT) -> dict:
    """Reassign a workflow task to a different user for load balancing and task distribution
    
    Args:
        task_id (str): The ID of the task to reassign
        assignee (str): Username to assign the task to
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
    
    Returns:
        A dictionary containing the reassignment result with success status
    
    Raises:
        Exception: If there's an error reassigning the workflow task
    
    Examples:
        # Reassign a specific task to a user
        reassign_workflow_task_tool("250740924", "girish.kalburgi.vistadcr1", "MQQzACV65IZ7MmL")
        
        # Reassign task to user
        reassign_workflow_task_tool("250740924", "josefina.bollini@us.mcd.com")
        
        # Load balancing example - reassign task to less busy user
        reassign_workflow_task_tool("251412861", "joao.grilo@pt.mcd.com")
    """
    return await reassign_workflow_task(task_id, assignee, tenant_id)

@mcp.tool()
async def get_possible_assignees_tool(tenant_id: str = RELTIO_TENANT, tasks: Optional[List[str]] = None,
                                     task_filter: Optional[Dict[str, Any]] = None, 
                                     exclude: Optional[List[str]] = None) -> dict:
    """Get possible assignees for specific tasks or based on filter/exclude criteria
    
    IMPORTANT: Only one parameter approach can be used at a time:
    - Either use 'tasks' parameter alone, OR
    - Use 'task_filter' and/or 'exclude' parameters (but NOT with 'tasks')
    
    Args:
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        tasks (list, optional): List of task IDs to get possible assignees for.
        task_filter (dict, optional): Filter criteria for tasks. Parameters used as filtering criteria for the resulting tasks list.
        exclude (list, optional): List of task IDs to exclude.
    
    Returns:
        A dictionary containing the possible assignees data and total count
    
    Raises:
        Exception: If there's an error getting the possible assignees
    
    Examples:
        # Get possible assignees for specific task ID
        get_possible_assignees_tool("MQQzACV65IZ7MmL", tasks=["23173985"])
        
        # Who can be assigned to all open DCR review tasks currently assigned to user1?
        get_possible_assignees_tool(
            "MQQzACV65IZ7MmL",
            task_filter={
                "assignee": "user1",
                "taskType": "dcrReview",
                "state": "valid"
            }
        )
        
        # Find possible assignees for all DCR tasks except these specific ones
        get_possible_assignees_tool(
            "MQQzACV65IZ7MmL",
            task_filter={"processType": "dcr"},
            exclude=["1230009", "1230010"]
        )
        
        # Who can handle all urgent tasks that are currently unassigned?
        get_possible_assignees_tool(
            task_filter={
                "priorityClass": "Urgent",
                "state": "valid"
            }
        )
    """
    return await get_possible_assignees(tenant_id, tasks, task_filter, exclude)

@mcp.tool()
async def retrieve_tasks_tool(tenant_id: str = RELTIO_TENANT, assignee: Optional[str] = None,
                             process_instance_id: Optional[str] = None, process_type: Optional[str] = None,
                             process_types: Optional[List[str]] = None, offset: int = 0, max_results: int = 10,
                             suspended: Optional[bool] = None, created_by: Optional[str] = None,
                             priority_class: Optional[str] = None, order_by: str = "createTime", 
                             ascending: bool = False, task_type: Optional[str] = None, 
                             created_after: Optional[int] = None, created_before: Optional[int] = None, 
                             state: str = "valid", object_uris: Optional[List[str]] = None, 
                             show_task_variables: bool = False, show_task_local_variables: bool = False, 
                             object_filter: Optional[str] = None) -> dict:
    """Retrieve tasks by filter from Reltio workflow system
    
    This API retrieves the details of tasks using specific filters. It only retrieves tasks where you had READ access 
    to the objects (entities, change requests, or relations) when the task was created.
    
    Args:
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        assignee (str, optional): Task assignee. To retrieve unassigned tasks, use a value of 'none'.
            Examples: "adminqa", "john.doe@company.com", "none"
        process_instance_id (str, optional): Process instance ID to filter tasks for a specific process instance.
        process_type (str, optional): Process instance type. Use this field to filter on a single process type.
            Examples: "dataChangeRequestReview", "potentialMatchReview", "recommendForDelete"
        process_types (List[str], optional): Process instance types. Use this field to filter on multiple process types.
            Examples: ["dataChangeRequestReview", "recommendForDelete"]
        offset (int): Start position for pagination. Defaults to 0.
        max_results (int): Number of records to be returned. Defaults to 10, capped at 100.
        suspended (bool, optional): Filter by suspended status.
        created_by (str, optional): Task owner/creator username.
        priority_class (str, optional): Task priority. Possible values: Urgent, High, Medium, Low.
        order_by (str): Sort criteria. Possible values: createTime (default), assignee, dueDate, priority.
        ascending (bool): Sort order. True for ascending, False for descending (default).
        task_type (str, optional): Task type to filter specific kinds of tasks.
            Examples: "dcrReview", "dcrInternalReview", "deleteReview", "matchReview"
        created_after (int, optional): Filter tasks created after this time (in milliseconds since epoch).
        created_before (int, optional): Filter tasks created before this time (in milliseconds since epoch).
        state (str): Validation state of tasks. Possible values: valid (default), invalid, all.
        object_uris (List[str], optional): List of Reltio object URIs to filter tasks associated with these objects.
            Examples: ["changeRequests/AeFAoBPn", "entities/16lJbKKs"]
        show_task_variables (bool): Display task variables. Defaults to False.
        show_task_local_variables (bool): Display task local variables. Defaults to False.
        object_filter (str, optional): Search filter expression for entities linked to workflow tasks.
            Examples: "equals(attributes.FirstName,'Alex')"
    
    Returns:
        A dictionary containing offset, size, total, and data array with task results
    
    Raises:
        Exception: If there's an error retrieving the workflow tasks
    
    Examples:
        # Basic usage - Get all tasks assigned to a specific user
        retrieve_tasks_tool(assignee="adminqa", tenant_id="MQQzACV65IZ7MmL")
        
        # Get data change request review tasks
        retrieve_tasks_tool(process_types=["dataChangeRequestReview"], tenant_id="MQQzACV65IZ7MmL")
        
        # Get medium priority DCR review tasks with limited results
        retrieve_tasks_tool(priority_class="Medium", task_type="dcrReview", max_results=1)
        
        # Get unassigned tasks that need assignment
        retrieve_tasks_tool(assignee="none")
        
        # Get tasks associated with specific entities or change requests
        retrieve_tasks_tool(object_uris=["changeRequests/AeFAoBPn", "entities/16lJbKKs"])
        
        # Sort tasks by due date in ascending order (oldest first)
        retrieve_tasks_tool(order_by="dueDate", ascending=True)
        
        # Time-based filtering - Get tasks created in a specific time period
        retrieve_tasks_tool(created_after=1606292473723, created_before=1606465273724, order_by="createTime")
    """
    return await retrieve_tasks(tenant_id, assignee, process_instance_id, process_type, process_types, 
                               offset, max_results, suspended, created_by, priority_class, order_by, 
                               ascending, task_type, created_after, created_before, state, object_uris, 
                               show_task_variables, show_task_local_variables, object_filter)

@mcp.tool()
async def get_task_details_tool(task_id: str, tenant_id: str = RELTIO_TENANT, 
                                show_task_variables: bool = False,
                                show_task_local_variables: bool = False) -> dict:
    """Get complete details of a specific workflow task by ID
    
    This tool retrieves the complete task object with metadata, process information, and task-specific attributes.
    It provides comprehensive information about a single workflow task including its current state, assignee,
    process context, possible actions, and optional variable details.
    
    Args:
        task_id (str): The ID of the task to retrieve details for.
            Examples: "9757836", "250740924", "251412861"
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        show_task_variables (bool): Display task variables. Defaults to False.
            Set to True to include task variables in the response for debugging or detailed analysis.
        show_task_local_variables (bool): Display task local variables. Defaults to False.
            Set to True to include task local variables in the response for debugging or detailed analysis.
    
    Returns:
        A dictionary containing complete task details:
        - assignee: task assignee username
        - createTime: task creation time (timestamp in milliseconds)
        - createdBy: task creator username
        - dueDate: due date for the task (timestamp in milliseconds)
        - processInstanceComments: array of comments
        - taskId: unique task identifier
        - displayName: human-readable task name
        - processInstanceId: process instance identifier
        - processType: process definition type (e.g., "dataChangeRequestReview")
        - taskType: task definition type (e.g., "dcrReview", "matchReview")
        - suspended: indicates if task is suspended (true/false)
        - objectURIs: array of Reltio object URIs associated with the task
        - possibleActions: array of possible user actions
        - preferredAction: recommended action
        - priority: numeric priority value
        - priorityClass: priority classification (Urgent/High/Medium/Low)
        - valid: indicates if task is valid (true/false)
        - taskLocalVariables: task local variables (if show_task_local_variables=true)
        - taskVariables: task variables (if show_task_variables=true)
    
    Raises:
        Exception: If there's an error retrieving the task details
    
    Examples:
        # Basic usage - Get details for a specific task
        get_task_details_tool("9757836", "MQQzACV65IZ7MmL")
        
        # Get task details with variables for debugging
        get_task_details_tool("250740924", show_task_variables=True, show_task_local_variables=True)
        
        # Get details for a DCR review task
        get_task_details_tool("251412861")
        
        # Get task details including all variable information
        get_task_details_tool(
            task_id="250740924",
            tenant_id="MQQzACV65IZ7MmL",
            show_task_variables=True,
            show_task_local_variables=True
        )
    """
    return await get_task_details(task_id, tenant_id, show_task_variables, show_task_local_variables)

@mcp.tool()
async def start_process_instance_tool(process_type: str, object_uris: List[str], 
                                     tenant_id: str = RELTIO_TENANT, comment: Optional[str] = None, 
                                     variables: Optional[Dict[str, Any]] = None) -> dict:
    """Start a process instance in Reltio workflow for any type of change requests created by user
    
    Args:
        process_type (str): The type of process to start.
            Examples: 'dataChangeRequestReview', 'recommendForDelete', 'loopDataVerification', 'potentialMatchReview'
        object_uris (List[str]): List of object URIs to associate with the process instance.
            Examples: ["changeRequests/123", "entities/123"], ["entities/789", "entities/101"]
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        comment (Optional[str]): Optional comment for the process instance
        variables (Optional[Dict[str, Any]]): Optional variables to pass to the process instance.
            Can be used to specify assignee or other process-specific variables.
    
    Returns:
        A dictionary containing the process instance details including processInstanceId, processType, and status
    
    Raises:
        Exception: If there's an error starting the process instance
    
    Examples:
        # Start a data change request process for specific entities
        start_process_instance_tool("dataChangeRequestReview", ["changeRequests/123","entities/123"], "MQQzACV65IZ7MmL")
        
        # Start a DCR task and assign to user
        start_process_instance_tool(
            "dataChangeRequestReview", 
            ["changeRequests/123","entities/123"], 
            "MQQzACV65IZ7MmL", 
            comment="Merge duplicate entities", 
            variables={"assignee": "super.man@reltio.com"}
        )
        
        # Start a loop data verification process for multiple entities
        start_process_instance_tool(
            "loopDataVerification", 
            ["entities/789", "entities/101"], 
            "MQQzACV65IZ7MmL",
            comment="Bulk loop data verification process"
        )
    """
    return await start_process_instance(process_type, object_uris, tenant_id, comment, variables)

@mcp.tool()
async def execute_task_action_tool(task_id: str, action: str, tenant_id: str = RELTIO_TENANT,
                                  process_instance_comment: Optional[str] = None) -> dict:
    """Execute an action on a workflow task
    
    Comments are optional but if provided, they will be added to the process instance comment.
    Include activity_client in the comment to track the activity.
    
    Args:
        task_id (str): The ID of the task to execute action on
        action (str): The action to execute (e.g., 'Approve', 'Reject', 'Cancel', etc.) 
            This depends on the possible actions for the task mentioned in task details.
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        process_instance_comment (Optional[str]): Optional comment for the process instance
    
    Returns:
        A dictionary containing the action execution result including taskId, action, and status
    
    Raises:
        Exception: If there's an error executing the task action
    
    Examples:
        # Approve a workflow task
        execute_task_action_tool("task123", "Approve", "MQQzACV65IZ7MmL", "Entity Update approved")
        
        # Reject a workflow task with comment
        execute_task_action_tool("task456", "Reject", "MQQzACV65IZ7MmL", "Entity does not meet quality standards")
        
        # Approve a task without comment
        execute_task_action_tool("task789", "Approve", "MQQzACV65IZ7MmL")
    """
    return await execute_task_action(task_id, action, tenant_id, process_instance_comment)

@mcp.tool()
async def unmerge_entity_tool(origin_entity_id: str, contributor_entity_id: str, tenant_id: str = RELTIO_TENANT, tree: bool = False) -> dict:
    """Unmerge a contributor entity from a merged entity with optional tree behavior - either keeping any profiles merged beneath the contributor intact within the origin entity (tree=False) or unmerging the contributor along with all profiles merged beneath it from a merged entity (tree=True).
    
    Args:
        origin_entity_id (str): The ID of the origin entity (the merged entity)
        contributor_entity_id (str): The ID of the contributor entity to unmerge from the origin entity
        tenant_id (str): Tenant ID for the Reltio environment. Defaults to RELTIO_TENANT env value.
        tree (bool): If True, unmerge the contributor entity and all profiles merged beneath it from the origin entity.
    
    Returns:
        A dictionary containing the result of the unmerge operation with 'a' (modified origin) and 'b' (spawn) entities
    
    Raises:
        Exception: If there's an error during the unmerge operation
    
    Examples:
        # Unmerge a contributor entity from a merged entity
        unmerge_entity_tool("entity1", "entity2", "tenant_id",False)
        
        # Unmerge a contributor entity and all profiles beneath it from a merged entity
        unmerge_entity_tool("entity1", "entity2", "tenant_id", True)
    """
    if tree:
        result = await unmerge_entity_tree_by_contributor(origin_entity_id, contributor_entity_id, tenant_id)
    else:
        result = await unmerge_entity_by_contributor(origin_entity_id, contributor_entity_id, tenant_id)

    return result


@mcp.tool()
async def health_check_tool() -> dict:
    """Check if the MCP server is healthy."""
    try:
        result = {"status": "ok", "message": "MCP server is running"}
        return result
    except Exception as e:
        return {"error": str(e)}

