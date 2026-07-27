import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tickets.models import User, Ticket, ChatMessage, TicketHistory
from tickets import services

print(">>> Очистка старых данных...")
Ticket.objects.all().delete()
User.objects.filter(username__in=['contractor1', 'contractor2', 'glonass1', 'bio1']).delete()

print(">>> Создание эталонных учетных записей модераторов и контрагентов...")
# Contractors
contractor1 = User.objects.create_user(username='contractor1', password='pass123', role='contractor', organization_name='ООО Логист-Про', is_staff=True)
contractor2 = User.objects.create_user(username='contractor2', password='pass123', role='contractor', organization_name='АО Агро-Транс Гарант', is_staff=True)

# GLONASS 1st Line
glonass = User.objects.create_user(username='glonass1', password='pass123', role='glonass', is_staff=True, is_superuser=True)

# Bio-Security 2nd Line
bio = User.objects.create_user(username='bio1', password='pass123', role='bio_security', is_staff=True)

print(">>> Генерация тестового потока заявок во всех статусах...")

# 1. New ticket waiting for GLONASS
t1 = services.create_ticket(
    contractor=contractor1,
    loading_place='Склад Терминал-1, Воронежская обл.',
    unloading_place='Элеватор Центральный, Сектор В',
    cargo='Пшеница 4 класс (25 тонн, наливом)',
    vehicle_number='К 777 ХВ 136',
    comment='Логин: voronezh_track\nПароль: glonass_pass_2026\nМашина оборудована датчиком температуры.'
)

# 2. Ticket approved directly by GLONASS
t2 = services.create_ticket(
    contractor=contractor2,
    loading_place='Агрохолодильник №2, Липецк',
    unloading_place='Цех глубокой переработки №4',
    cargo='Кукурузный крахмал в биг-бэгах (18т)',
    vehicle_number='В 555 ОО 48',
    comment='Система мониторинга: Wialon_Pro\nID объекта: 998822'
)
services.approve_by_glonass(t2, glonass)

# 3. Ticket escalated to Bio-Security (currently under review, bio_check)
t3 = services.create_ticket(
    contractor=contractor1,
    loading_place='Птицеводческий комплекс "Северный", Ростов',
    unloading_place='Кормовой склад №1',
    cargo='Комбикорм специализированный (20т)',
    vehicle_number='М 123 НО 161',
    comment='Внимание: авто из приграничного района. Требуется сверка ветеринарных сертификатов.'
)
services.escalate_to_bio(t3, glonass)

# 4. Ticket in interactive communication loop (waiting_contractor)
t4 = services.create_ticket(
    contractor=contractor2,
    loading_place='Склад химических реагентов, Нижний Новгород',
    unloading_place='Очистные сооружения, Блок 3',
    cargo='Дезинфицирующие компоненты (12т)',
    vehicle_number='Х 999 ХХ 152',
    comment='Трекинг доступен по ссылке в телеграм-боте @track_bot'
)
services.escalate_to_bio(t4, glonass)
services.send_chat_message(t4, bio, text='Приложенный акт санитарной обработки от 12 числа истёк (прошло более 7 суток). Срочно загрузите актуальный скан акта мойки!')

# 5. Rejected ticket with active quarantine date
t5 = services.create_ticket(
    contractor=contractor1,
    loading_place='Ферма №7, Белгородская область (зона карантина)',
    unloading_place='Главный приемный пункт',
    cargo='Фуражное зерно (30т)',
    vehicle_number='А 001 АА 31',
    comment='Логин Wialon: bel_001 / pass: qwerty99'
)
services.escalate_to_bio(t5, glonass)
ban_expiration = date.today() + timedelta(days=21)
services.ban_vehicle_by_bio(t5, bio, ban_expiration)

print("\n=== Готово! База данных успешно наполнена тестовыми сценариями. ===")
print("Учетные записи (пароль для всех: pass123):")
print(" 1. ГЛОНАСС (1-я линия):     glonass1")
print(" 2. Биобез  (2-я линия):     bio1")
print(" 3. Контрагент Логист-Про: contractor1")
print(" 4. Контрагент Агро-Транс: contractor2")
