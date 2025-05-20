from typing import Optional, Dict, Any

def find_service_info_by_apikey_value(registered_services: Optional[Dict[str, Any]], 
                                      apikey_value: str) -> Optional[Dict[str, Any]]:
    """
    API_Key.registered_service JSONB 딕셔너리에서
    'apikey' 필드 값이 주어진 apikey_value와 일치하는 첫 번째 서비스 정보를 찾습니다.
    """
    if not isinstance(registered_services, dict):
        return None

    for service_id_key, service_details in registered_services.items():
        if isinstance(service_details, dict) and service_details.get('apikey') == apikey_value:
            # 반환할 때 해당 서비스의 내부 service_id (JSONB 키)도 함께 반환하면 유용할 수 있습니다.
            # 여기서는 일단 상세 정보만 반환. 필요에 따라 수정 가능.
            return service_details

    return None # Not found

def find_service_info_by_apikey_value(registered_services: Optional[Dict[str, Any]], apikey_value: str) -> Optional[Dict[str, Any]]:
    # ... (implementation remains the same)
    if not isinstance(registered_services, dict): return None
    for service_id_key, service_details in registered_services.items():
        if isinstance(service_details, dict) and service_details.get('apikey') == apikey_value:
            return service_details
    return None
 
def find_service_info_by_service_id_key(registered_services: Optional[Dict[str, Any]], service_id_key_value: str) -> Optional[Dict[str, Any]]:
    # ... (implementation remains the same)
    if not isinstance(registered_services, dict): return None
    service_details = registered_services.get(service_id_key_value)
    return service_details if isinstance(service_details, dict) else None
 
def find_service_apikey_by_service_id_key(registered_services: Optional[Dict[str, Any]], service_id_key_value: str) -> Optional[str]:
    """
    API_Key.registered_service JSONB 딕셔너리에서 키(key)로 서비스 정보 찾고 apikey 필드 값을 반환.
    """
    service_details = find_service_info_by_service_id_key(registered_services, service_id_key_value)
    if service_details:
        return service_details.get('apikey')
    return None

def find_internal_service_id_by_apikey_value(registered_services: Optional[Dict[str, Any]], apikey_value: str) -> Optional[str]:
    """
    API_Key.registered_service JSONB 딕셔너리에서
    'apikey' 필드 값이 주어진 apikey_value와 일치하는 서비스의 JSONB 키(내부 service_id)를 찾습니다.
    """
    if not isinstance(registered_services, dict):
        return None

    for service_id_key, service_details in registered_services.items():
        if isinstance(service_details, dict) and service_details.get('apikey') == apikey_value:
            return service_id_key # Return the JSONB key

    return None # Not found