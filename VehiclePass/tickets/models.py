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
