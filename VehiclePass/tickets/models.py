from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('contractor', 'Контрагент'),
        ('glonass', 'ГЛОНАСС'),
        ('bio_security', 'Биобезопасность'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='contractor', verbose_name="Роль")
    organization_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Организация")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class Ticket(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новая'),
        ('bio_check', 'На проверке ОАБ'),
        ('waiting_contractor', 'Ожидает ответа от контрагента'),
        ('approved', 'Согласовано'),
        ('rejected', 'Въезд запрещен'),
        ('invalid_form', 'Неправильное заполнение формы'),
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    
    contractor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets', verbose_name="Контрагент")
    loading_place = models.CharField(max_length=255, verbose_name="Место загрузки")
    unloading_place = models.CharField(max_length=255, verbose_name="Место выгрузки")
    cargo = models.CharField(max_length=255, verbose_name="Груз")
    
    vehicle_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Гос. номер ТС")
    org_name_override = models.CharField(max_length=255, blank=True, null=True, verbose_name="Наименование организации (если отличается)")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий (логины/пароли)")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    ban_until = models.DateField(blank=True, null=True, verbose_name="Запрет въезда до")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['vehicle_number']),
        ]

    def __str__(self):
        return f"Заявка #{self.id} - {self.vehicle_number or 'Без номера'} ({self.get_status_display()})"

    def get_excel_data(self):
        from django.db.models import Q
        # 1. Дата проверки, 2. Время проверки
        terminal_logs = self.history.filter(
            Q(action_description__icontains='согласован') | 
            Q(action_description__icontains='запрещен') | 
            Q(action_description__icontains='отклонен') |
            Q(action_description__icontains='неправильное')
        ).order_by('-created_at')
        
        check_date = ""
        check_time = ""
        operator_name = ""
        if terminal_logs.exists():
            last_log = terminal_logs.first()
            check_date = last_log.created_at.strftime("%d.%m.%Y")
            check_time = last_log.created_at.strftime("%H:%M")
            if last_log.user:
                operator_name = f"{last_log.user.last_name} {last_log.user.first_name}".strip() or last_log.user.username

        # 10. Необходимость согласования ОАБ
        oab_required = self.history.filter(
            Q(action_description__contains='Биобез') | Q(action_description__contains='ОАБ')
        ).exists()

        oab_required_str = "Да" if oab_required else ""
        
        # 11. Решение ОАБ
        oab_decision = ""
        if oab_required:
            if self.status == 'approved':
                oab_decision = "согласовано"
            elif self.status == 'rejected':
                oab_decision = "не согласовано"
                
        # 8. Результат проверки
        check_result = ""
        if self.status == 'approved' and not oab_required:
            check_result = "Известных зон АЧС не пересекал"
            
        # 13. Комментарии
        comments = "Решение о допуске по согласованию с отделом аудита биобезопасности." if oab_required else ""

        contractor_name = self.contractor.organization_name or self.contractor.username
        
        data = [
            check_date,
            check_time,
            self.vehicle_number or "",
            contractor_name,
            self.loading_place or "",
            self.unloading_place or "",
            self.cargo or "",
            check_result,
            "", # Признак АЧС
            oab_required_str,
            oab_decision,
            "", # Способ проверки
            comments,
            operator_name # ФИО оператора
        ]
        
        clean_data = [str(x).replace('\t', ' ').replace('\n', ' ').replace('\r', '') for x in data]
        return '\t'.join(clean_data)

class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments', verbose_name="Заявка")
    file = models.FileField(upload_to='ticket_attachments/', verbose_name="Файл")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Кто загрузил")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    def __str__(self):
        return f"Вложение #{self.id} для заявки #{self.ticket.id}"

class ChatMessage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages', verbose_name="Заявка")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Отправитель")
    text = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, verbose_name="Вложение")

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Сообщение от {self.sender.username} в заявке #{self.ticket.id}"

class TicketHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history', verbose_name="Заявка")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Пользователь")
    action_description = models.CharField(max_length=255, verbose_name="Действие")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата действия")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"История: {self.action_description} (Заявка #{self.ticket.id})"
