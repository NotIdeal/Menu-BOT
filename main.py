import telegram
import logging
import time
import os
import psycopg2
import bot_messages, bot_states

from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler, ConversationHandler, CallbackQueryHandler, PrefixHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from functools import wraps
from googlesheet import *

DB_Host = os.environ['DB_Host']
DB_Database = os.environ['DB_Database']
DB_User = os.environ['DB_User']
DB_Port = os.environ['DB_Port']
DB_Password = os.environ['DB_Password']

logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level = logging.INFO)
logger = logging.getLogger(__name__)
LIST_OF_ADMINS = [771840280]

custom_keyboard = [['🛎Заказать'],
                   ['🧺Добавить_в_корзину', '🧺Показать_ваш_заказ'],
                   ['🗑Очистить_корзину', '🗑Удалить_из_корзины'],
                   ['📅Указать_номер стола', '📬Отправить_отзыв'],
                   ['🗒️Все_функции']]
                   
reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard, resize_keyboard = True)
connection = psycopg2.connect(database = DB_Database, user = DB_User, password = DB_Password, host = DB_Host, port = DB_Port)
def log_text(debug_text):
  print(debug_text)
def send_message(context, chat_id, text):
    try:
        context.bot.send_message(chat_id = chat_id, text = text, parse_mode = "Markdown", reply_markup = reply_markup)
    except:
        log_text('No such chat_id using a bot')
def sql_table(connection):
    cur = connection.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS tasks(id BIGSERIAL PRIMARY KEY, user_id integer, task text)")
    connection.commit()
    cur.close()
def sql_insert(connection, user_id, new_task):
    cur = connection.cursor()
    cur.execute("INSERT INTO tasks(user_id, task) VALUES(%s, %s)", (user_id, new_task, ))
    connection.commit()
    cur.close()
def sql_clear(user_id):
    cur = connection.cursor()
    cur.execute("DELETE FROM tasks WHERE user_id = %s", (user_id, ))
    connection.commit()
    cur.close()
def sql_delete(user_id, task_number):
    cur = connection.cursor()
    task_number = task_number - 1
    cur.execute("DELETE FROM tasks WHERE id in (SELECT id FROM tasks WHERE user_id = %s LIMIT 1 OFFSET %s)", (user_id, task_number))
    connection.commit()
    cur.close()
def sql_number_of_tasks(user_id):
    cur = connection.cursor()
    cur.execute("SELECT COUNT(*) FROM tasks WHERE user_id = %s", (user_id, ))
    number_of_tasks = cur.fetchall()
    result = number_of_tasks[0][0]
    connection.commit()
    cur.close()
    return result
def sql_get_tasks(user_id):
    cur = connection.cursor()
    cur.execute("SELECT task FROM tasks WHERE user_id = %s", (user_id, ))
    tasks = cur.fetchall()
    connection.commit()
    cur.close()
    return tasks
def sql_get_distinct_ids():
    cur = connection.cursor()
    cur.execute("SELECT COUNT (DISTINCT user_id) FROM tasks")
    distinct_ids = cur.fetchall()
    connection.commit()
    cur.close()
    return distinct_ids[0][0]
def sql_get_ids():
    cur = connection.cursor()
    cur.execute("SELECT DISTINCT user_id FROM tasks")
    ids = cur.fetchall()
    user_ids = []
    for i in ids:
        user_ids.append(i[0])
    connection.commit()
    cur.close()
    return user_ids
def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            context.bot.send_message(chat_id = update.message.chat_id, text = "К сожалению, это функция доступна только админам 😬", reply_markup = reply_markup)
            return
        return func(update, context, *args, **kwargs)
    return wrapped
def add_to_database(user_id, new_task):
    print("/add: User with id: " + str(user_id) + " added a new task: ")
    sql_insert(connection, user_id, new_task)
def get_text(user_id):
    ith = 0
    text = ""
    tasks = sql_get_tasks(user_id)
    text = "Номер стола: " + tasks[0][0] + "\n"
    for task_i in tasks:
        ith = ith + 1
        if ith > 1:
            ith_text = str(ith - 1) + ". " + task_i[0] + "\n"
            text = text + ith_text
    return text
def cancel(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.cancelled_successfully, reply_markup = reply_markup)
    return ConversationHandler.END
@restricted
def admin_send_to_all(update, context):
    try:
        user_ids = sql_get_ids()
        text = ' '.join(context.args)
        text = text.replace('\\n', '\n')
        for sending_id in user_ids:
            send_message(context, sending_id, text)
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_all_success_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_all_error_command_response, reply_markup = reply_markup)
@restricted
def admin_send_to(update, context):
    try:
        user_id = context.args[0]
        text = context.args[1]
        ith = 0
        for word in context.args:
            ith = ith + 1
            if ith > 2:
                text = text + " " + word
        text = text.replace('\\n', '\n')
        send_message(context, user_id, text)
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_all_success_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.send_to_error_command_response, reply_markup = reply_markup)
@restricted
def admin_help(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.admin_help_command_response, reply_markup = reply_markup)
def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu
def clear(update, context):
    keyboard = [
        InlineKeyboardButton("Да", callback_data = '1'),
        InlineKeyboardButton("Нет", callback_data = '2')
    ]
    reply_keyboard = InlineKeyboardMarkup(build_menu(keyboard, n_cols = 1))
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.clear_command_confirmation, reply_markup = reply_keyboard)    
    return bot_states.CHECK
def check_query(update, context):
    query = update.callback_query
    user_id = update.effective_user.id
    user_tasks = sql_number_of_tasks(user_id)
    if query.data == '1':
        if user_tasks > 0:
            sql_clear(user_id)
            print("/clear: User with id: " + str(user_id) + " cleared all his tasks")
            query.edit_message_text(text = bot_messages.clear_successfully_command_response)
        else:
            print("/clear: User with id: " + str(user_id) + " could not clear his tasks")
            query.edit_message_text(text = bot_messages.tasks_empty_command_response)
    else:
        query.edit_message_text(text = "Окей 😉")
    return ConversationHandler.END

def delete_task(update, context):
    keyboard = []
    user_id = update.message.from_user.id
    tasks = sql_get_tasks(user_id)
    number_of_tasks = sql_number_of_tasks(user_id)
    if number_of_tasks == 0:
        context.bot.send_message(chat_id = update.effective_user.id, text = bot_messages.tasks_empty_command_response, reply_markup = reply_markup)
        return ConversationHandler.END
    ith = 0
    for i in tasks:
        ith = ith + 1
        keyboard.append(InlineKeyboardButton(i[0], callback_data = str(ith)))
    reply_keyboard = InlineKeyboardMarkup(build_menu(keyboard, n_cols = 1))
    context.bot.send_message(chat_id = update.effective_user.id, text = bot_messages.delete_task_write_task, reply_markup = reply_keyboard)
    return bot_states.CHECK_DELETE

def show_menu(update, context):
    keyboard = []
    menu = get_type("all")
    number_of_meal = len(menu)
    if number_of_meal == 0:
        context.bot.send_message(chat_id = update.effective_user.id, text = bot_messages.tasks_empty_command_response, reply_markup = reply_markup)
    ith = 0
    for i in menu:
        ith += 1
        keyboard.append(InlineKeyboardButton(i[0] + ' | ' + str(i[1]), callback_data = str(ith)))
    reply_keyboard = InlineKeyboardMarkup(build_menu(keyboard, n_cols = 1))

    context.bot.send_message(chat_id = update.effective_user.id , text = bot_messages.delete_task_write_task , reply_markup = reply_keyboard)

def check_delete_query(update, context):
    user_id = update.effective_user.id
    query = update.callback_query
    task_number = int(query.data)
    sql_delete(user_id, task_number)
    query.edit_message_text(text = bot_messages.delete_task_successfully_command_response)
    return ConversationHandler.END
    
def read_task_num(update, context):
    task = update.message.text
    try:
        task_number = int(task)
        user_id = update.message.from_user.id
        number_of_tasks = sql_number_of_tasks(user_id)
        if task_number < 1 or task_number > number_of_tasks:
            context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_wrong_number_command_response, reply_markup = reply_markup)
            return ConversationHandler.END
        sql_delete(user_id, task_number)
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_successfully_command_response, reply_markup = reply_markup)
    except (IndexError, ValueError):
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.delete_task_error_command_response, reply_markup = reply_markup)
    return ConversationHandler.END

def add_task(update, context):
    if not context.args:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.add_task_write_task, reply_markup = reply_markup)
        return bot_states.READ_NEW_TASK
    new_task = ' '.join(context.args)
    user_id = update.message.from_user.id
    add_to_database(user_id, new_task)
    whole_text = bot_messages.updated_tasks_command_response + get_text(user_id)
    whole_text = whole_text + bot_messages.guide_order
    context.bot.send_message(chat_id = update.message.chat_id, text = whole_text, reply_markup = reply_markup)

def order(update, context):
    user_id = update.message.from_user.id
    whole_text = get_text(user_id)
    text = bot_messages.order_start + whole_text
    for admin_id in LIST_OF_ADMINS:
        send_message(context, admin_id, text)
    send_message(context, user_id, bot_messages.successfully_ordered)
    sql_clear(user_id)

def read_new_task(update, context):
    new_task = update.message.text
    user_id = update.message.from_user.id
    add_to_database(user_id, new_task)
    whole_text = bot_messages.updated_tasks_command_response + get_text(user_id)
    context.bot.send_message(chat_id = update.message.chat_id, text = whole_text, reply_markup = reply_markup)
    if sql_number_of_tasks(user_id) == 1:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.guide_set_timer, reply_markup = reply_markup)
    return ConversationHandler.END

def feedback(update, context):
    if not context.args:
        context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.feedback_write_text,  reply_markup = reply_markup)
        return bot_states.READ_FEEDBACK
    text = context.args[0]
    ith = 0
    for word in context.args:
        ith = ith + 1
        if ith > 1:
            text = text + " " + word
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    text = "❗️Хей, пользоветель бота отправил новый фидбэк всем админам: ❗️\n\nFeedback:\n" + text + "\n\nUsername: @" + str(username) + "\n\nUser ID: " + str(user_id)
    for admin_id in LIST_OF_ADMINS:
        context.bot.send_message(chat_id = admin_id, text = text)
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.feedback_success_command_response, reply_markup = reply_markup)

def read_feedback(update, context):
    text = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    text =  "❗️Хей, пользоветель бота отправил новый фидбэк всем админам: ❗️\n\nFeedback:\n" + text + "\n\nUsername: @" + str(username) + "\n\nUser ID: " + str(user_id)
    for admin_id in LIST_OF_ADMINS:
        context.bot.send_message(chat_id = admin_id, text = text)
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.feedback_success_command_response, reply_markup = reply_markup)
    return ConversationHandler.END

def show_tasks(update, context):
    user_id = update.message.from_user.id
    user_tasks = sql_number_of_tasks(user_id)
    if user_tasks > 0:
        whole_text = bot_messages.show_tasks_command_response + get_text(user_id)
    else:
        whole_text = bot_messages.tasks_empty_command_response
    context.bot.send_message(chat_id = update.message.chat_id, text = whole_text, reply_markup = reply_markup)

def start(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.start_command_response, reply_markup = reply_markup)

def help(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.help_command_response, reply_markup = reply_markup)

def unknown(update, context):
    context.bot.send_message(chat_id = update.message.chat_id, text = bot_messages.unknown_command_response, reply_markup = reply_markup)

def main():
    updater = Updater(token = os.environ['BOT_TOKEN'], use_context = True)
    dp = updater.dispatcher
    sql_table(connection)
    feedback_handler = CommandHandler('feedback', feedback, pass_args = True, pass_chat_data = True)
    clear_handler = CommandHandler('clear', clear)
    delete_handler = CommandHandler('delete', delete_task, pass_args = True, pass_chat_data = True)
    show_tasks_handler = CommandHandler('showmenu', show_menu)
    add_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('add', add_task)],
        states = {
            bot_states.READ_NEW_TASK: [MessageHandler(Filters.text, read_new_task)]
        },
        fallbacks = [CommandHandler('cancel', cancel)]
    )
    del_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('delete', delete_task)],
        states = {
            bot_states.CHECK_DELETE: [CallbackQueryHandler(check_delete_query)]
        },
        fallbacks = [CommandHandler('cancel', cancel)]
    )
    feedback_conv_handler = ConversationHandler(
        entry_points = [CommandHandler('feedback', feedback)],
        states = {
            bot_states.READ_FEEDBACK: [MessageHandler(Filters.text, read_feedback)]
        },
        fallbacks = [CommandHandler('cancel', cancel)]
    )
    clear_conv_hnadler = ConversationHandler(
        entry_points = [CommandHandler('clear', clear)],
        states = {
            bot_states.CHECK: [CallbackQueryHandler(check_query)]
        },
        fallbacks = [CommandHandler('cancel', cancel)]
    )
                #    ['', '🧺Показать ваш заказ'],
                #    ['🗑Очистить корзину', '🗑Удалить из корзины'],
                #    ['📅Указать номер стола', '📬Отправить отзыв'],
    order_handler = PrefixHandler('🛎', 'Заказать', order)
    add_handler = PrefixHandler('🧺', 'Добавить' + 'в' + 'корзину', add_task)
    start_handler = CommandHandler('start', start)
    help_handler = PrefixHandler('🗒️', 'Все_функции', help)
    admin_help_handler = CommandHandler('admin_help', admin_help)
    admin_send_to_all_handler = CommandHandler('admin_send_to_all', admin_send_to_all, pass_args = True, pass_chat_data = True)
    admin_send_to_handler = CommandHandler('admin_send_to', admin_send_to, pass_args = True, pass_chat_data = True)
    unknown_handler = MessageHandler(Filters.command, unknown)
    
    dp.add_handler(order_handler)
    dp.add_handler(clear_conv_hnadler)
    dp.add_handler(feedback_conv_handler)
    dp.add_handler(del_conv_handler)
    dp.add_handler(add_conv_handler)
    dp.add_handler(feedback_handler)
    dp.add_handler(clear_handler)
    dp.add_handler(delete_handler)
    dp.add_handler(show_tasks_handler)
    dp.add_handler(add_handler)
    dp.add_handler(start_handler)
    dp.add_handler(help_handler)
    dp.add_handler(admin_help_handler)
    dp.add_handler(admin_send_to_all_handler)
    dp.add_handler(admin_send_to_handler)
    dp.add_handler(unknown_handler)

    updater.start_polling()
    updater.idle()
if __name__ == '__main__':
    main()
