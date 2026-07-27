from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Ticket, Attachment, ChatMessage, TicketHistory

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {'fields': ('role', 'organization_name')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'organization_name')
    list_filter = ('role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'organization_name')

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 1
    readonly_fields = ('sender', 'text', 'created_at', 'attachment')

class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ('user', 'action_description', 'created_at')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehicle_number', 'contractor_info', 'loading_place', 'unloading_place', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('vehicle_number', 'contractor__username', 'contractor__organization_name', 'loading_place', 'unloading_place', 'comment')
    inlines = [AttachmentInline, ChatMessageInline, TicketHistoryInline]
    readonly_fields = ('created_at', 'updated_at')

    def contractor_info(self, obj):
        return obj.org_name_override or obj.contractor.organization_name or obj.contractor.username
    contractor_info.short_description = "Контрагент / Org"

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'uploaded_by', 'uploaded_at')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'sender', 'created_at')

@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'user', 'action_description', 'created_at')
    readonly_fields = ('ticket', 'user', 'action_description', 'created_at')
