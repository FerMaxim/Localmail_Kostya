from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import Ticket, Attachment, ChatMessage, TicketHistory
from .permissions import can_access_chat

@transaction.atomic
def create_ticket(contractor, loading_place, unloading_place, cargo, vehicle_number=None, org_name_override=None, comment=None, files=None):
    ticket = Ticket.objects.create(
        contractor=contractor,
        loading_place=loading_place.strip(),
        unloading_place=unloading_place.strip(),
        cargo=cargo.strip(),
        vehicle_number=(vehicle_number or "").replace(' ', '').upper() or None,
        org_name_override=(org_name_override or "").strip() or None,
        comment=(comment or "").strip() or None,
        status='new'
    )
    
    if files:
        for f in files:
            Attachment.objects.create(ticket=ticket, file=f, uploaded_by=contractor)
            
    TicketHistory.objects.create(
        ticket=ticket,
        user=contractor,
        action_description="Контрагент: Заявка создана и направлена в отдел ГЛОНАСС"
    )
    return ticket

@transaction.atomic
def approve_by_glonass(ticket, user):
    if not (user.role == 'glonass' or user.is_superuser):
        raise PermissionDenied("Только сотрудники ГЛОНАСС могут выполнять данное действие на этапе первичной проверки.")
    if ticket.status != 'new':
        raise ValidationError("Согласовать на линии ГЛОНАСС можно только новые заявки.")
        
    ticket.status = 'approved'
    ticket.save()
    TicketHistory.objects.create(
        ticket=ticket,
        user=user,
        action_description="ГЛОНАСС: Маршрут за 72 часа проверен. Заявка СОГЛАСОВАНА (Въезд разрешен)."
    )
    return ticket

@transaction.atomic
def escalate_to_bio(ticket, user):
    if not (user.role == 'glonass' or user.is_superuser):
        raise PermissionDenied("Только сотрудники ГЛОНАСС могут направить заявку на вторичный фильтр.")
    if ticket.status != 'new':
        raise ValidationError("Перевести в Биобез можно только новые заявки.")
        
    ticket.status = 'bio_check'
    ticket.save()
    TicketHistory.objects.create(
        ticket=ticket,
        user=user,
        action_description="ГЛОНАСС: Спорная ситуация по маршруту/грузу. Направлено на проверку в отдел Биобезопасности."
    )
    return ticket

@transaction.atomic
def reject_by_glonass_invalid(ticket, user):
    if not (user.role == 'glonass' or user.is_superuser):
        raise PermissionDenied("Только сотрудники ГЛОНАСС или администраторы могут отклонить по форме.")
    ticket.status = 'invalid_form'
    ticket.save()
    TicketHistory.objects.create(
        ticket=ticket,
        user=user,
        action_description="ГЛОНАСС: Отклонено (неправильное или некорректное заполнение формы)."
    )
    return ticket

@transaction.atomic
def send_chat_message(ticket, user, text, file=None):
    can_view, can_send, reason = can_access_chat(user, ticket)
    if not can_send:
        raise PermissionDenied(reason or "У вас нет прав на отправку сообщения в данный момент.")
    
    if not text and not file:
        raise ValidationError("Сообщение не может быть полностью пустым.")
        
    msg = ChatMessage.objects.create(
        ticket=ticket,
        sender=user,
        text=(text or "").strip(),
        attachment=file
    )
    
    # If file was attached during chat, also save to Attachment list for easy viewing in document section
    if file:
        Attachment.objects.create(ticket=ticket, file=file, uploaded_by=user)

    # Status State Machine transition loop:
    if user.role == 'bio_security':
        # When Bio writes a question/comment, switch status to wait for contractor
        if ticket.status == 'bio_check':
            ticket.status = 'waiting_contractor'
            ticket.save()
            TicketHistory.objects.create(
                ticket=ticket,
                user=user,
                action_description="Биобез: Отправлен запрос в чат (Статус сменился на «Ожидает ответа от контрагента»)."
            )
    elif user.role == 'contractor':
        # When Contractor replies to Bio's query, switch back to bio_check
        if ticket.status == 'waiting_contractor':
            ticket.status = 'bio_check'
            ticket.save()
            TicketHistory.objects.create(
                ticket=ticket,
                user=user,
                action_description="Контрагент: Отправлен ответ в чат и/или приложены документы (Заявка вернулась к Биобезу)."
            )
            
    return msg

@transaction.atomic
def approve_by_bio(ticket, user):
    if not (user.role == 'bio_security' or user.is_superuser):
        raise PermissionDenied("Только сотрудники Биобезопасности могут принять это решение.")
    if ticket.status not in ['bio_check', 'waiting_contractor']:
        raise ValidationError("Заявка должна находиться в ведении отдела Биобезопасности.")
        
    ticket.status = 'approved'
    ticket.save()
    TicketHistory.objects.create(
        ticket=ticket,
        user=user,
        action_description="Биобезопасность: Ветеринарно-санитарный контроль пройден. Заявка СОГЛАСОВАНА."
    )
    return ticket

@transaction.atomic
def ban_vehicle_by_bio(ticket, user, ban_until_date):
    if not (user.role == 'bio_security' or user.is_superuser):
        raise PermissionDenied("Только сотрудники Биобезопасности могут выдать карантинный запрет въезда.")
    if ticket.status not in ['bio_check', 'waiting_contractor']:
        raise ValidationError("Заявка должна находиться в ведении отдела Биобезопасности.")
    if not ban_until_date:
        raise ValidationError("Обязательно укажите дату окончания запрета въезда (карантина).")
        
    ticket.status = 'rejected'
    ticket.ban_until = ban_until_date
    ticket.save()
    TicketHistory.objects.create(
        ticket=ticket,
        user=user,
        action_description=f"Биобезопасность: ВЪЕЗД ЗАПРЕЩЕН. Установлен строгий карантин до {ban_until_date}."
    )
    return ticket

@transaction.atomic
def revert_to_new(ticket, user):
    if not (user.role == 'glonass' or user.is_superuser):
        raise PermissionDenied("Только сотрудники ГЛОНАСС могут возвращать заявки.")
    ticket.status = 'new'
    ticket.ban_until = None
    ticket.save()
    TicketHistory.objects.create(
        ticket=ticket,
        user=user,
        action_description="ГЛОНАСС: Отмена решения. Заявка возвращена в работу (Новая)."
    )
    return ticket

@transaction.atomic
def revert_to_bio_check(ticket, user):
    if not (user.role == 'bio_security' or user.is_superuser):
        raise PermissionDenied("Только сотрудники ОАБ могут возвращать заявки.")
    if ticket.status not in ['approved', 'rejected']:
        raise ValidationError("Возврат возможен только для закрытых заявок.")
        
    ticket.status = 'bio_check'
    ticket.ban_until = None
    ticket.save()
    TicketHistory.objects.create(
        ticket=ticket,
        user=user,
        action_description="ОАБ: Отмена решения. Заявка возвращена на этап проверки."
    )
    return ticket
