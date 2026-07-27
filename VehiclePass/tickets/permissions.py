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
    Enforces strict role isolation rules for internal chat.
    """
    if not user or not user.is_authenticated:
        return False, False, "Требуется авторизация."
    if user.is_superuser:
        return True, True, ""
        
    # 1. GLONASS has NO chat interface whatsoever
    if user.role == 'glonass':
        return False, False, "Отделу ГЛОНАСС переписка недоступна. Все диалоги с контрагентами ведутся специалистами Биобезопасности."
        
    # 2. Chat only activates when ticket reaches Bio stage
    if ticket.status in ['new', 'invalid_form']:
        return False, False, "Чат становится доступен только после перевода заявки в отдел Биобезопасности."
        
    # 3. Bio-Security role (Moderator 2nd line)
    if user.role == 'bio_security':
        if ticket.status in ['bio_check', 'waiting_contractor']:
            return True, True, ""
        elif ticket.status in ['approved', 'rejected']:
            return True, False, "Заявка закрыта. Переписка завершена."
        return False, False, "Недоступно в текущем статусе."
        
    # 4. Contractor role
    if user.role == 'contractor':
        if ticket.contractor != user:
            return False, False, "У вас нет доступа к чужой заявке."
        if ticket.status == 'bio_check':
            # Contractor CANNOT initiate or speak while Bio is reviewing
            return True, False, "Ожидайте результатов проверки или сообщения от отдела Биобезопасности. Вы сможете написать, когда инспекторы зададут вопрос в чат."
        elif ticket.status == 'waiting_contractor':
            # Unlocked! Bio asked a question, contractor can reply in loop
            return True, True, ""
        elif ticket.status in ['approved', 'rejected']:
            return True, False, "Заявка закрыта. Переписка завершена."
            
    return False, False, "Доступ ограничен."
