import logging
import paramiko
import psycopg2
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler,CallbackQueryHandler
import os
import re
from dotenv import load_dotenv

load_dotenv()

RM_HOST = os.getenv('RM_HOST')
RM_PORT = int(os.getenv('RM_PORT', '22'))
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')
TOKEN = os.getenv('TOKEN')

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_DATABASE = os.getenv('DB_DATABASE')

GET_APT_LIST_CHOICE, GET_PACKAGE_NAME = range(2)
SAVE_PHONE_NUMBER_STATE = 1
SAVE_EMAIL_ADDRESS_STATE = 2


logging.basicConfig(filename='bot.log', level=logging.INFO, format=' %(asctime)s - %(levelname)s - %(message)s', encoding="utf-8")
logger = logging.getLogger(__name__)
logger.info('Бот запущен')

def start(update: Update,context):
    user = update.effective_user
    update.message.reply_text(f'Привет {user.full_name},Бот запущен и готов выполнять твои команды')

def helpCommand(update: Update,context):
    """Отправляет сообщение с информацией об использовании бота."""
    update.message.reply_text('Вот список доступных команд:\n'
                              '/start - Начать диалог\n'
                              '/help - Показать справку\n'
                              '/find_email - Найти email адреса\n'
                              '/find_phone_number - Найти телефонные номера\n'
                              '/verify_password - Проверить сложность пароля\n'
                              '/get_release - Информация о релизе\n'
                              '/get_uname - Информация об архитектуры\n'
                              '/get_uptime - Время работы системы\n'
                              '/get_df - Состояние файловой системы\n'
                              '/get_free - Состояние оперативной памяти\n'
                              '/get_mpstat - Производительность системы\n'
                              '/get_w - Работающие пользователи\n'
                              '/get_auths - Последние 10 входов\n'
                              '/get_critical - Последние 5 критических событий\n'
                              '/get_ps - Запущенные процессы\n'
                              '/get_ss - Используемые порты\n'
                              '/get_apt_list - Информация об установленных пакетах\n'
                              '/get_repl_logs - Вывод логов о репликации\n'
                              '/get_emails - Получить Email-адреса\n'
                              '/get_phone_numbers - Получить номера телефонов\n'
                              '/get_services - Информация о запущенных сервисах\n'
                              )


def findPhoneNumbersCommand(update: Update,context):
    update.message.reply_text('Введите текст для поиска телефонных номеров:')
    return 'findPhoneNumbers'

def findPhoneNumbers(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    user_input = update.message.text

    phoneNumRegex = re.compile(
        r'(?:\+7|8)'             
        r'(?:[\s-]?)'            
        r'(?:\(?\d{3}\)?)'       
        r'(?:[\s-]?)'            
        r'(?:'                   
        r'\d{7}'                 
        r'|'                     
        r'\d{3}'                 
        r'(?:[\s-]?)'            
        r'\d{2}'                 
        r'(?:[\s-]?)'            
        r'\d{2}'                 
        r')'
    )
    phoneNumberList = phoneNumRegex.findall(user_input)

    if not phoneNumberList:
        logger.error('Телефонные номера не найдены')
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    normalizedPhoneNumbers = []
    foundPhoneNumbers = ''
    for i, rawNumber in enumerate(phoneNumberList):
        digits = re.sub(r'\D', '', rawNumber)
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        elif digits.startswith('7'):
            pass
        else:
            logger.warning(f'Номер {rawNumber} имеет некорректный формат')
            continue
        if len(digits) == 11:
            normalized_number = '+' + digits
            normalizedPhoneNumbers.append(normalized_number)
            foundPhoneNumbers += f'{i+1}. {rawNumber} (нормализованный: {normalized_number})\n'

    if not normalizedPhoneNumbers:
        logger.error('Нет корректных телефонных номеров после нормализации')
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    logger.info(f'Найдены номера:\n{foundPhoneNumbers}')
    update.message.reply_text(foundPhoneNumbers)

    context.user_data['saved_phones'] = normalizedPhoneNumbers

    keyboard = [
        [InlineKeyboardButton("Да", callback_data='save_phones')],
        [InlineKeyboardButton("Нет", callback_data='decline_saving')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("Хотите ли вы сохранить эти номера телефонов в базе данных?", reply_markup=reply_markup)
    return SAVE_PHONE_NUMBER_STATE

def findEmailsCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска email адресов:')
    return 'findEmails'

def findEmails(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} ввел:\n{update.message.text}')
    user_input = update.message.text
    emailRegex = re.compile(r"([a-zA-Z0-9_.]+@[a-zA-Z0-9-]+\.[a-z-.]+)")
    emailList = emailRegex.findall(user_input)

    if not emailList:
        logger.error('Email адреса не найдены')
        update.message.reply_text('Email адреса не найдены')
        return ConversationHandler.END
    foundEmails = ''
    for i, emailAddress in enumerate(emailList):
        foundEmails += f'{i+1}. {emailAddress}\n'

    logger.info(f'Найдены адреса:\n{foundEmails}')
    update.message.reply_text(foundEmails)

    context.user_data['saved_emails'] = emailList
    keyboard = [
        [InlineKeyboardButton("Да", callback_data='save_emails')],
        [InlineKeyboardButton("Нет", callback_data='decline_saving')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Хотите ли вы сохранить эти email адреса в базе данных?", reply_markup=reply_markup)
    return SAVE_EMAIL_ADDRESS_STATE

def checkPasswordCommand(update: Update,context):
    update.message.reply_text('Введите ваш пароль для проверки:')
    return 'checkPassword'

def checkPassword(update: Update,context):
    logger.info(f'Пользователь {update.message.from_user.username} ввел пароль')
    user_password = update.message.text
    if not user_password:
        logger.info('Передана пустая строка')
        update.message.reply_text('Передана пустая строка')
        return ConversationHandler.END
    pattern = r'^(?=.*[A-Z])(?=.*[!@#$%^&*()])(?=.*[0-9])(?=.*[a-z]).{8,}$'

    if re.match(pattern, user_password):
        logger.info(f'Пароль пользователя {update.message.from_user.username} сложный')
        update.message.reply_text(f"Пароль сложный")
    else:
        logger.info(f'Пароль пользователя {update.message.from_user.username} простой')
        update.message.reply_text(f"Пароль простой")

    return ConversationHandler.END

def connectToHost(command):
    try:
        logger.info(f'Подключение к {RM_HOST}')
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=RM_HOST, username=RM_USER, password=RM_PASSWORD, port=RM_PORT)

        logger.info(f'Выполнение команды: {command}')
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        exit_status = stdout.channel.recv_exit_status()

        client.close()

        if exit_status != 0:
            logger.error(f'Ошибка при выполнении команды: {error.strip()}')
            return None
        full_output = output.strip() + '\n' + error.strip()
        return full_output.strip()

    except Exception as e:
        logger.error(f'Ошибка при подключении к хосту: {str(e)}')
        return None

def getRelease(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил информацию о релизе')
    command = "lsb_release -a"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о релизе')

def getUname(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил информацию об архитектуре')
    command = "uname -a"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию об архитектуре')

def getUptime(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил время работы системы')

    command = "uptime"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о времени работы системы')

def getDf(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил состояние файловой системы')
    command = "df -h"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о состоянии файловой системы')


def getFree(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил состояние оперативной памяти')

    command = "free -h"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о состоянии оперативной памяти')

def getMpstat(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил производительность системы')
    command = "mpstat"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о производительности системы')

def getW(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил информацию о работающих пользователях')
    command = "w"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о работающих пользователях')

def getAuths(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил последние 10 входов')
    command = "last -n 10"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о последних 10 входах')


def getCritical(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил последние 5 критических событий')
    command = f"grep -i 'critical' /var/log/syslog | tail -n 5"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о последних критических событиях')


def getPs(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил информацию о запущенных процессах')
    command = "ps"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию о запущенных процессах')

def getSs(update: Update, context):
    logger.info(f'Пользователь {update.message.from_user.username} запросил информацию об используемых портах')
    command = "ss -tulnp"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось получить информацию об используемых портах')

def get_apt_list(update: Update, context):
    logger.info(f"Пользователь {update.effective_user.username} вызвал /get_apt_list")
    keyboard = [
        [
            InlineKeyboardButton("Вывести все пакеты", callback_data='all_packages'),
            InlineKeyboardButton("Поиск пакета", callback_data='search_package'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Пожалуйста, выберите действие:', reply_markup=reply_markup)

    return GET_APT_LIST_CHOICE

def apt_list_choice(update: Update, context):
    query = update.callback_query
    query.answer()
    choice = query.data

    if choice == 'all_packages':
        logger.info("Пользователь выбрал вывод всех пакетов")
        command = "dpkg --list | grep '^ii'"
        result = connectToHost(command)
        if result:
            parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
            for part in parts:
                query.message.reply_text(part)
        else:
            query.message.reply_text('Не удалось получить список пакетов')

        return ConversationHandler.END

    elif choice == 'search_package':
        logger.info("Пользователь выбрал поиск пакета")
        query.message.reply_text('Введите название пакета для поиска:')
        return GET_PACKAGE_NAME

def apt_package_search(update: Update, context):
    package_name = update.message.text.strip()
    logger.info(f"Пользователь ищет информацию о пакете: {package_name}")
    command = f"apt show {package_name}"
    result = connectToHost(command)

    if result:
        update.message.reply_text(result)
    else:
        update.message.reply_text('Не удалось найти информацию об этом пакете')

    return ConversationHandler.END

def cancel(update: Update, context):
    update.message.reply_text('Действие отменено.')
    return ConversationHandler.END

def run_remote_command(command, host, username, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        client.close()

        if error:
            return None, error
        return output, None
    except Exception as e:
        return None, str(e)

def get_repl_logs(update: Update, context):
    try:
        command = "cat /var/log/postgresql/postgresql-15-main.log | grep repl | tail -n 15"
        remote_host = DB_HOST
        remote_username = "bobkov"
        remote_password = DB_PASSWORD

        logs, error = run_remote_command(command, remote_host, remote_username, remote_password)

        if logs:
            update.message.reply_text(f"Последние репликационные логи:\n{logs}")
        elif error:
            update.message.reply_text(f"Ошибка при получении логов: {error}")
        else:
            update.message.reply_text("Репликационные логи не найдены.")

    except Exception as e:
        update.message.reply_text(f"Ошибка при выполнении команды для получения логов: {str(e)}")

def get_emails(update: Update, context):
    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Emails")
        emails = cursor.fetchall()

        if emails:
            response = '\n'.join([f"{email[0]}: {email[1]}" for email in emails])
            update.message.reply_text(response)
        else:
            update.message.reply_text("Нет email-адресов в базе данных.")

    except (Exception, psycopg2.Error) as error:
        logger.error(f"Ошибка при работе с PostgreSQL: {error}")
        update.message.reply_text("Ошибка при работе с базой данных.")

    finally:
        if connection:
            cursor.close()
            connection.close()

def get_phone_numbers(update: Update, context):
    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM PhoneNumbers")
        phone_numbers = cursor.fetchall()

        if phone_numbers:
            response = '\n'.join([f"{phone[0]}: {phone[1]}" for phone in phone_numbers])
            update.message.reply_text(response)
        else:
            update.message.reply_text("Нет номеров телефонов в базе данных.")

    except (Exception, psycopg2.Error) as error:
        logger.error(f"Ошибка при работе с PostgreSQL: {error}")
        update.message.reply_text("Ошибка при работе с базой данных.")

    finally:
        if connection:
            cursor.close()
            connection.close()


def saveEmailAddress(update: Update, context):
    query = update.callback_query
    query.answer()
    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)
        cursor = connection.cursor()
        saved_emails = context.user_data.get('saved_emails', [])
        if not saved_emails:
            query.message.reply_text('Нет email адресов для сохранения.')
            return ConversationHandler.END

        for email in saved_emails:
            cursor.execute("INSERT INTO Emails (email) VALUES (%s)", (email,))

        connection.commit()
        query.message.reply_text('Email адреса успешно сохранены в базе данных.')

    except (Exception, psycopg2.Error) as error:
        logger.error(f"Ошибка при сохранении email адресов: {error}")
        query.message.reply_text("Ошибка при сохранении email адресов.")

    finally:
        if connection:
            cursor.close()
            connection.close()

    return ConversationHandler.END

def declineSaving(update: Update, context):
    query = update.callback_query
    query.answer()
    query.message.reply_text('Данные не будут сохранены.')
    return ConversationHandler.END


def savePhoneNumber(update: Update, context):
    query = update.callback_query
    query.answer()
    try:
        connection = psycopg2.connect(user=DB_USER,
                                      password=DB_PASSWORD,
                                      host=DB_HOST,
                                      port=DB_PORT,
                                      database=DB_DATABASE)
        cursor = connection.cursor()
        saved_phones = context.user_data.get('saved_phones', [])
        if not saved_phones:
            query.message.reply_text('Нет номеров телефонов для сохранения.')
            return ConversationHandler.END

        for phone in saved_phones:
            cursor.execute("INSERT INTO PhoneNumbers (phone_number) VALUES (%s)", (phone,))

        connection.commit()
        query.message.reply_text('Номера телефонов успешно сохранены в базе данных.')

    except (Exception, psycopg2.Error) as error:
        logger.error(f"Ошибка при сохранении номеров телефонов: {error}")
        query.message.reply_text("Ошибка при сохранении номеров телефонов.")

    finally:
        if connection:
            cursor.close()
            connection.close()
    return ConversationHandler.END

def get_services(update: Update, context):
    try:
        command = "systemctl list-units --type=service --state=running"
        result = connectToHost(command)

        if result:
            update.message.reply_text(f"Запущенные сервисы:\n{result}")
        else:
            update.message.reply_text('Не удалось получить информацию о запущенных сервисах.')

    except Exception as e:
        logger.error(f"Ошибка при выполнении команды для получения запущенных сервисов: {str(e)}")
        update.message.reply_text(f"Ошибка при получении информации о сервисах: {str(e)}")


def echo(update: Update, context):
    update.message.reply_text(update.message.text)

def set_bot_commands(updater):
    commands = [
        BotCommand("start", "Начать диалог"),
        BotCommand("help", "Показать справку"),
        BotCommand("find_email", "Найти email адреса"),
        BotCommand("find_phone_number", "Найти телефонные номера"),
        BotCommand("verify_password", "Проверить сложность пароля"),
        BotCommand("get_release", "Информация о релизе"),
        BotCommand("get_uname", "Информация об архитектуре"),
        BotCommand("get_uptime", "Время работы системы"),
        BotCommand("get_df", "Состояние файловой системы"),
        BotCommand("get_free", "Состояние оперативной памяти"),
        BotCommand("get_mpstat", "Производительность системы"),
        BotCommand("get_w", "Работающие пользователи"),
        BotCommand("get_auths", "Последние 10 входов"),
        BotCommand("get_critical", "Последние 5 критических событий"),
        BotCommand("get_ps", "Запущенные процессы"),
        BotCommand("get_ss", "Используемые порты"),
        BotCommand("get_apt_list", "Информация об установленных пакетах"),
        BotCommand("get_repl_logs", "Вывод логов о репликации"),
        BotCommand("get_emails", "Получить Email-адреса"),
        BotCommand("get_phone_numbers", "Получить номера телефонов"),
        BotCommand("get_services", "Информация о запущенных сервисах")
    ]

    updater.bot.set_my_commands(commands)


def main():
    updater = Updater(TOKEN, use_context=True)
    ud = updater.dispatcher

    convHandlerFindEmails = ConversationHandler(
        entry_points=[CommandHandler('find_email', findEmailsCommand)],
        states={
            'findEmails': [MessageHandler(Filters.text & ~Filters.command, findEmails)],
            SAVE_EMAIL_ADDRESS_STATE: [
                CallbackQueryHandler(saveEmailAddress, pattern='save_emails'),
                CallbackQueryHandler(declineSaving, pattern='decline_saving')
            ],
        },
        fallbacks=[]
    )

    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            'findPhoneNumbers': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            SAVE_PHONE_NUMBER_STATE: [
                CallbackQueryHandler(savePhoneNumber, pattern='save_phones'),
                CallbackQueryHandler(declineSaving, pattern='decline_saving')
            ],
        },
        fallbacks=[]
    )

    convHandlerCheckPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', checkPasswordCommand)],
        states={
            'checkPassword': [MessageHandler(Filters.text & ~Filters.command, checkPassword)],
        },
        fallbacks=[]
    )

    apt_list_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list)],
        states={
            GET_APT_LIST_CHOICE: [
                CallbackQueryHandler(apt_list_choice),
            ],
            GET_PACKAGE_NAME: [
                MessageHandler(Filters.text & ~Filters.command, apt_package_search),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    ud.add_handler(apt_list_conv_handler)
    set_bot_commands(updater)

    ud.add_handler(CommandHandler("start", start))
    ud.add_handler(CommandHandler("help", helpCommand))
    ud.add_handler(convHandlerFindEmails)
    ud.add_handler(convHandlerFindPhoneNumbers)
    ud.add_handler(convHandlerCheckPassword)
    ud.add_handler(CommandHandler('get_release', getRelease))
    ud.add_handler(CommandHandler('get_uname', getUname))
    ud.add_handler(CommandHandler('get_uptime', getUptime))
    ud.add_handler(CommandHandler('get_df', getDf))
    ud.add_handler(CommandHandler('get_free', getFree))
    ud.add_handler(CommandHandler('get_mpstat', getMpstat))
    ud.add_handler(CommandHandler('get_w', getW))
    ud.add_handler(CommandHandler('get_auths', getAuths))
    ud.add_handler(CommandHandler('get_critical', getCritical))
    ud.add_handler(CommandHandler('get_ps', getPs))
    ud.add_handler(CommandHandler('get_ss', getSs))
    ud.add_handler(apt_list_conv_handler)
    ud.add_handler(CommandHandler('get_repl_logs', get_repl_logs))
    ud.add_handler(CommandHandler('get_emails', get_emails))
    ud.add_handler(CommandHandler('get_phone_numbers', get_phone_numbers))
    ud.add_handler(CommandHandler('get_services', get_services))

    ud.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    updater.start_polling(timeout=60)
    logger.info("Бот запущен и ожидает сообщений")
    updater.idle()

if __name__ == '__main__':
    main()
