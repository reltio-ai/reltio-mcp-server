import logging
from typing import List, Dict, Any, Optional


# Configure logging
logger = logging.getLogger("mcp.server.reltio")
   
def simplify_reltio_attributes(attributes_dict):
    """
    Simplifies a Reltio-style attributes dictionary by extracting 'value' fields,
    preserving the nested structure and handling multiple values.
    """
    result = {}
    for key, value_list in attributes_dict.items():
        if isinstance(value_list, list) and value_list:
            simplified_list = []
            for item in value_list:
                if isinstance(item, dict) and 'value' in item:
                    if isinstance(item['value'], dict):
                        simplified_list.append(simplify_reltio_attributes(item['value']))
                    else:
                        simplified_list.append(item['value'])
            
            if not simplified_list:
                continue

            if len(simplified_list) == 1:
                result[key] = simplified_list[0]
            else:
                result[key] = simplified_list
    return result

def slim_crosswalks(cws: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep only id, type, value, createDate for each crosswalk. Explicitly omit attributeURIs and any other keys.
    Skip any items that are not dicts.
    """
    out: List[Dict[str, Any]] = []
    for cw in cws:
        if not isinstance(cw, dict):
            continue
        
        # Extract ID from URI
        uri = cw.get("uri", "")
        if uri and "/" in uri:
            id_value = uri.rsplit("/", 1)[-1]
        else:
            id_value = cw.get("id")
        
        # Extract type (last part after /)
        type_value = cw.get("type", "")
        if type_value and "/" in type_value:
            type_value = type_value.rsplit("/", 1)[-1]
        
        # Extract createDate with fallbacks
        create_date = cw.get("createDate") or cw.get("createTime") or cw.get("createdTime")
        
        out.append({
            "id": id_value,
            "type": type_value,
            "value": cw.get("value"),
            "createDate": create_date,
        })
    return out

def format_entity_matches(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {d["object"]["uri"]:{
        "matchRules":d["matchRules"],
        "createdTime":d["createdTime"],
        "matchScore":d["matchScore"],
        "relevance":d.get("relevance",None),
        "label":d.get("label",None)} for d in matches}