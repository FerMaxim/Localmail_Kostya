from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ValidationError
from datetime import date, timedelta
from .models import User, Ticket, ChatMessage, Attachment, TicketHistory
from .permissions import can_view_ticket, can_access_chat
from . import services

class RoleIsolationAndStateMachineTest(TestCase):
    def setUp(self):
        self.contractor = User.objects.create_user(username='contractor1', password='password123', role='contractor', organization_name='ООО ТестТранс')
        self.other_contractor = User.objects.create_user(username='contractor2', password='password123', role='contractor', organization_name='АО Чужой')
        self.glonass = User.objects.create_user(username='glonass1', password='password123', role='glonass')
        self.bio = User.objects.create_user(username='bio1', password='password123', role='bio_security')

        self.ticket_new = services.create_ticket(
            contractor=self.contractor,
            loading_place='Склад №1 (г. Воронеж)',
            unloading_place='Завод Центральный',
            cargo='Зерно фуражное 20т',
            vehicle_number='А111АА77',
            comment='Логин: user_track / Пароль: secret123'
        )

    def test_glonass_can_approve_or_escalate_but_not_bio(self):
        # Bio cannot approve a 'new' ticket that wasn't escalated (throws ValidationError for status)
        with self.assertRaises(ValidationError):
            services.approve_by_bio(self.ticket_new, self.bio)
        
        # GLONASS can escalate to Bio
        services.escalate_to_bio(self.ticket_new, self.glonass)
        self.assertEqual(self.ticket_new.status, 'bio_check')

    def test_glonass_has_no_chat_access(self):
        services.escalate_to_bio(self.ticket_new, self.glonass)
        can_view, can_send, reason = can_access_chat(self.glonass, self.ticket_new)
        self.assertFalse(can_send)
        self.assertFalse(can_view)
        self.assertIn("Отделу ГЛОНАСС переписка недоступна", reason)

        with self.assertRaises(PermissionDenied):
            services.send_chat_message(self.ticket_new, self.glonass, text='Попытка ГЛОНАСС написать в чат')

    def test_contractor_cannot_initiate_chat_in_biocheck(self):
        services.escalate_to_bio(self.ticket_new, self.glonass)
        # Ticket is now in bio_check
        can_view, can_send, reason = can_access_chat(self.contractor, self.ticket_new)
        self.assertTrue(can_view) # Can see read-only chat feed
        self.assertFalse(can_send) # CANNOT initiate dialog
        self.assertIn("Ожидайте результатов проверки", reason)

        with self.assertRaises(PermissionDenied):
            services.send_chat_message(self.ticket_new, self.contractor, text='Почему долго проверяете?')

    def test_bio_can_initiate_chat_loop_and_unlock_contractor(self):
        services.escalate_to_bio(self.ticket_new, self.glonass)
        
        # Bio sends first message in chat -> triggers waiting_contractor
        services.send_chat_message(self.ticket_new, self.bio, text='Акт от 10.05 просрочен. Загрузите свежий скан акта.')
        self.assertEqual(self.ticket_new.status, 'waiting_contractor')

        # Now contractor is UNLOCKED in waiting_contractor status!
        can_view, can_send, reason = can_access_chat(self.contractor, self.ticket_new)
        self.assertTrue(can_send)
        
        # Contractor replies -> switches status back to bio_check
        services.send_chat_message(self.ticket_new, self.contractor, text='Направляем свежий акт от 27.07.')
        self.assertEqual(self.ticket_new.status, 'bio_check')
        
        # Contractor is locked again once replied
        can_view_after, can_send_after, _ = can_access_chat(self.contractor, self.ticket_new)
        self.assertFalse(can_send_after)

    def test_quarantine_ban_requires_date(self):
        services.escalate_to_bio(self.ticket_new, self.glonass)
        with self.assertRaises(ValidationError):
            services.ban_vehicle_by_bio(self.ticket_new, self.bio, ban_until_date=None)
            
        ban_date = date.today() + timedelta(days=14)
        services.ban_vehicle_by_bio(self.ticket_new, self.bio, ban_until_date=ban_date)
        self.assertEqual(self.ticket_new.status, 'rejected')
        self.assertEqual(self.ticket_new.ban_until, ban_date)

    def test_contractor_data_isolation(self):
        # Another contractor cannot view or chat on someone else's ticket
        self.assertFalse(can_view_ticket(self.other_contractor, self.ticket_new))
        self.assertTrue(can_view_ticket(self.contractor, self.ticket_new))


class RoleDashboardRoutingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.contractor = User.objects.create_user(username='client_test', password='password123', role='contractor')
        self.glonass = User.objects.create_user(username='glonass_test', password='password123', role='glonass')
        self.bio = User.objects.create_user(username='bio_test', password='password123', role='bio_security')

    def test_contractor_receives_client_portal(self):
        self.client.force_login(self.contractor)
        response = self.client.get(reverse('tickets:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tickets/dashboard_contractor.html')
        self.assertIn('total_count', response.context)

    def test_glonass_receives_dispatcher_console(self):
        self.client.force_login(self.glonass)
        response = self.client.get(reverse('tickets:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tickets/dashboard_glonass.html')
        self.assertIn('new_count', response.context)

    def test_bio_receives_security_terminal(self):
        self.client.force_login(self.bio)
        response = self.client.get(reverse('tickets:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tickets/dashboard_bio.html')
        self.assertIn('quarantine_count', response.context)
