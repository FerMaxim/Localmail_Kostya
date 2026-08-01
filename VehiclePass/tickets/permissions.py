from django.core.exceptions import PermissionDenied

def can_view_ticket(user, ticket):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.role == 'glonass':
        # GLONASS sees new tickets and archived/processed ones in read-only
        return True
    if user.role == 'bio_security':
        # Bio sees only tickets routed to them by GLONASS or processed by Bio
        return ticket.status in ['bio_check', 'waiting_contractor', 'approved', 'rejected']
    if user.role == 'contractor':
        # Contractors only see their own tickets
        return ticket.contractor == user
    return False

def can_access_chat(user, ticket):
    """
    Returns a tuple: (can_view_chat: bool, can_send_messages: bool, disable_reason: str)
    """
    if not user or not user.is_authenticated:
        return False, False, "Требуется авторизация."
    if user.is_superuser:
        return True, True, ""
        
    # 1. GLONASS can chat while ticket is in their jurisdiction
    if user.role == 'glonass':
        if ticket.status in ['new', 'invalid_form']:
            return True, True, ""
        return True, False, "Чат для отдела ГЛОНАСС доступен только на этапе первичной проверки."
        
    # 2. Bio-Security role (ОАБ)
    if user.role == 'bio_security':
        if ticket.status in ['bio_check', 'waiting_contractor', 'approved', 'rejected']:
            return True, True, ""
        return False, False, "Недоступно в текущем статусе."
        
    # 3. Contractor role
    if user.role == 'contractor':
        if ticket.contractor != user:
            return False, False, "У вас нет доступа к чужой заявке."
        # Контрагент может писать в чат на любом этапе своей заявки
        return True, True, ""
            
    return False, False, "Доступ ограничен."
