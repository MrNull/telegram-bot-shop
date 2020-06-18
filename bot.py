#!/usr/bin/python3
# -*- coding: utf-8 -*-

import telebot
import sqlite3
import datetime
import re
import config
import Lang_RU
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


class AdminStates:  # класс хранения состояний админа, при добавление товаров
    state: str

    def __init__(self, state):
        self.state = state
                 
    def get_state(self):
        return self.state


def create_bd(): # создание структуры бд магазина
    try:
        conn = sqlite3.connect('mybd.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE userslist (id int, first_name text, 
            user_name text, language text, status text, basket_id int, 
            orders_amount int, datе_reg datetime, date_order datetime, phone_number text)''')
        c.execute('''CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name text, price int, 
            description text, picture_url text, status int)''')
        c.execute('''CREATE TABLE basket (id_order INTEGER PRIMARY KEY AUTOINCREMENT, user_id text, status text,
            cost int, product_amount int)''')
        c.execute('''CREATE TABLE basket_list (id_order int, user_id text, product_id int,
            amount int, sum int)''')
        c.execute('''CREATE TABLE history_orders (id_order int, user_id int, product_id int, product_amount int, 
            sum int, date_order datetime)''')
        conn.commit()
        conn.close()
        print(Lang_RU.Create_BD)
    except:
        print(Lang_RU.Error_Create_BD)


def showing_daily_orders():  # вывод статистики покупок за день
    date = datetime.datetime.now().date()
    date = str(date)+'%'
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    orders = c.execute("SELECT COUNT(DISTINCT user_id), sum(product_amount), sum(sum) FROM history_orders \
        WHERE date_order LIKE ?",([date]))
    orders = orders.fetchall()
    conn.commit()
    conn.close()
    answer = 'клиентов сегодня {} \nтоваров купленно {}шт. \nна сумму {}р.'.format(orders[0][0],orders[0][1],orders[0][2])
    bot.send_message(config.ID_Admin, answer)


def showing_active_buyers(): # показ самых активных клиентов за все время
    answer = 'самые активные покупатели: \n'
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    buyers = c.execute("SELECT userslist.first_name, userslist.user_name, userslist.orders_amount, \
        userslist.date_order, userslist.phone_number, SUM(history_orders.sum) \
        FROM userslist JOIN history_orders ON userslist.id=history_orders.user_id \
        GROUP BY user_id ORDER BY orders_amount  DESC LIMIT 10")
    for i in buyers:
        answer += 'Имя <b>{}</b> {} Количество заказов <b>{}</b>. Дата последнего заказа {}. телефон {}. сумма покупок <b>{}p.</b>\n' \
        .format(i[0],i[1],i[2],i[3][:10],i[4],i[5])
    conn.commit()
    conn.close()
    bot.send_message(config.ID_Admin, answer, parse_mode='HTML')


def check_user(user_id, first_name, user_name, user_lang):   #проверка существует ли такой пользователь. Если нет, то создаем
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    user = conn.execute("SELECT id FROM userslist WHERE id =?", ([user_id]))
    uid = user.fetchall()
    if len(uid) == 0:
        date = datetime.datetime.now()
        c.execute("INSERT INTO userslist VALUES (?,?,?,?,?,?,?,?,?,?)",(user_id, first_name, 
        	user_name, user_lang, 0, 0, 0, date, date, 0))
        count = c.execute("SELECT COUNT (id_order) FROM basket")
        count = count.fetchall()
        number=int(count[0][0])+1
        c.execute("INSERT INTO basket VALUES (?,?,?,?,?)",(number, user_id,0,0,0))
        print('Регистрация нового пользователя', first_name, user_name)
 
    conn.commit()
    conn.close()

def admin_control(data):  # управление состояниями админа
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    if admin.get_state() == 'ADD_PICTURE':
        c.execute("UPDATE products set picture_url = ?, status = ? WHERE status = 'is_being_created'", 
            ([data,'on_sale']))
        bot.send_message(config.ID_Admin,Lang_RU.Message_product_ready)

    elif admin.get_state() == 'ADD_DESCRIPTION':
        c.execute("UPDATE products set description = ? WHERE status = 'is_being_created'", 
            ([data]))
        admin.state='ADD_PICTURE'
        bot.send_message(config.ID_Admin,Lang_RU.Message_picture_add)

    elif admin.get_state() == 'ADD_PRICE':
        c.execute("UPDATE products set price = ? WHERE status = 'is_being_created'", ([data]))
        admin.state='ADD_DESCRIPTION'
        bot.send_message(config.ID_Admin,Lang_RU.Message_description_add)

    elif admin.get_state() == 'ADD_NAME':
        c.execute("UPDATE products set name = ? WHERE status = 'is_being_created'", ([data]))
        admin.state='ADD_PRICE'
        bot.send_message(config.ID_Admin, Lang_RU.Message_price_add)

    conn.commit()
    conn.close()

def user_product_add(user_id,product_id,message_id):  #функция добавление товара в корзину
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    product = conn.execute("SELECT amount FROM basket_list WHERE user_id =? and product_id =?", 
        ([user_id, product_id]))
    amount = product.fetchall()
    if len(amount) == 0:  #если у данного пользователя еще нет такого товара, то создаем новую строку для него
        basket_id = conn.execute("SELECT id_order FROM basket WHERE user_id =?", ([user_id]))
        basket_id = basket_id.fetchall()
        basket_id = int(basket_id[0][0])
        product_price = conn.execute("SELECT price FROM products WHERE id = ?", ([product_id]))
        product_price = str(product_price.fetchall())
        product_price = int(product_price[2:-3])
        c.execute("INSERT INTO basket_list VALUES (?,?,?,?,?)", (basket_id, user_id, 
            product_id, 1, product_price))
    else:       #если у пользователя уже есть такой товар, то добавляем +1 и +цену к общей сумме товара
        product_prices = conn.execute("SELECT price FROM products WHERE id = ?", ([product_id]))
        product_price = product_prices.fetchall()
        product_prices = int(product_price[0][0])
        basket_id = conn.execute("SELECT id_order FROM basket WHERE user_id =?", ([user_id]))
        basket_id = basket_id.fetchall()
        basket_id = int(basket_id[0][0])
        conn.execute("UPDATE basket_list set amount = amount+1, sum = sum+? WHERE id_order =? and product_id =?", 
            ([product_prices, basket_id, product_id]))
    conn.commit()
    conn.close()
    update_basket(user_id)
    update_buttons(user_id, message_id, product_id)


def user_product_sub(user_id, product_id, message_id):  # функция вычитания товара из корзины
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    product = conn.execute("SELECT amount FROM basket_list WHERE user_id =? and product_id =?", 
        ([user_id, product_id]))
    amount = product.fetchall()
    if len(amount) == 0:   # если нет такой строки, то выходим
        conn.commit()
        conn.close()
        return  
    else:
        product = conn.execute("SELECT amount FROM basket_list WHERE user_id =? and product_id =?", 
            ([user_id, product_id]))
        amount_product = product.fetchall()
        amount_product = int(amount_product[0][0])
        if amount_product == 0: #если товара 0, то тоже выходим. В остальных случаях вычитаем количество и общую стоимость
            conn.commit()
            conn.close()
            return
        product_prices = conn.execute("SELECT price FROM products WHERE id = ?", ([product_id]))
        for i in product_prices:
            product_prices = i[0]
        basket_id = conn.execute("SELECT id_order FROM basket WHERE user_id =?", ([user_id]))
        basket_id = basket_id.fetchall()
        basket_id = int(basket_id[0][0])
        conn.execute("UPDATE basket_list set amount = amount-1, sum = sum-? WHERE id_order =? and product_id =?", 
            ([product_prices, basket_id, product_id]))
    conn.commit()
    conn.close()
    update_basket(user_id)
    update_buttons(user_id, message_id, product_id)


def product_delete(product_id, message_id): # удаление админом товара из продажи
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    conn.execute("DELETE FROM products WHERE id = ?", ([product_id]))
    conn.commit()
    conn.close()
    bot.edit_message_text(chat_id=config.ID_Admin, message_id=message_id, text = 'товар удален')


def update_basket(user_id): # обновление и пересчет корзины после изменений
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    summ = conn.execute("SELECT SUM(amount), SUM(sum) FROM basket_list WHERE user_id=?", ([user_id]))
    for i in summ:
        amount = i[0]
        sum_all = i[1]
    conn.execute("UPDATE basket set cost = ?, product_amount = ? WHERE user_id = ?", 
        ([sum_all, amount, user_id]))
    conn.commit()
    conn.close()

def get_basket(user_id): #вывод содержимого корзины покупателя
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    cost = conn.execute("SELECT cost FROM basket WHERE user_id=?", ([user_id]))
    cost_basket = cost.fetchall()
    cost_basket = int(cost_basket[0][0])
    if (cost_basket) == 0:
        bot.send_message(user_id,Lang_RU.Message_basket_is_empty)
        return
    answer = 'Ваша корзина: \n'
    basket = conn.execute("SELECT products.name, products.price, basket_list.amount, \
        basket_list.sum FROM products JOIN basket_list ON products.id=basket_list.product_id \
        WHERE basket_list.user_id = ? AND basket_list.amount > 0", ([user_id]))
    for i in basket:
        answer += '<b>{}</b> {}р х {} = {}р. \n'.format(i[0],i[1],i[2],i[3])
    answer += 'Итоговая стоимость: {}р'.format(cost_basket)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Оформить заказ", callback_data='order'))
    bot.send_message(user_id, answer, reply_markup=markup, parse_mode='HTML')
    conn.commit()
    conn.close()


def get_products(user_id):  #вывод покупателю списка товаров
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    products=conn.execute("SELECT id, name, price, description, picture_url FROM products WHERE status = 'on_sale'")
    for i in products:
        add='add'+str(i[0])
        sub='sub'+str(i[0])
        answer='<b>{}</b> {}р \n {}'.format(i[1],i[2],i[3])
        markup = InlineKeyboardMarkup()
        markup.row_width = 3
        markup.add(InlineKeyboardButton("-", callback_data=sub),
            InlineKeyboardButton("0", callback_data="cbn"),
            InlineKeyboardButton("+", callback_data=add))
        bot.send_photo(user_id,i[4])
        bot.send_message(user_id, answer, reply_markup=markup, parse_mode='HTML')
    conn.commit()
    conn.close()


def showing_products_editor(): #вывод админу списка товаров для редактирования
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    products=conn.execute("SELECT id, name, price, description, picture_url, status FROM products")
    for i in products:
        delete='del'+str(i[0])
        answer='<b>{}</b> {}р \n {} \n статус товара: {}'.format(i[1],i[2],i[3],i[5])
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("удалить", callback_data=delete))

        bot.send_photo(config.ID_Admin,i[4])
        bot.send_message(config.ID_Admin, answer, reply_markup=markup, parse_mode='HTML')

    conn.commit()
    conn.close()

def update_buttons(user_id, message_id, product_id): #перерисовка кнопок после изменения количества товара
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    products=conn.execute("SELECT name, price, description FROM products WHERE id = ? ", ([product_id]))
    for i in products:
        add='add' + str(product_id)
        sub='sub' + str(product_id)
        answer='<b>{}</b> {}р \n {}'.format(i[0],i[1],i[2])
        amount = conn.execute("SELECT amount FROM basket_list WHERE user_id = ? and product_id =?", 
            ([user_id, product_id]))
        amount_product = amount.fetchall()
        amount_product = int(amount_product[0][0])
        markup = InlineKeyboardMarkup()
        markup.row_width = 3
        markup.add(InlineKeyboardButton("-", callback_data=sub),
            InlineKeyboardButton(amount_product, callback_data="cbn"),
            InlineKeyboardButton("+", callback_data=add))
        bot.edit_message_reply_markup(chat_id =user_id, message_id =message_id, reply_markup=markup)
    conn.commit()
    conn.close()


def user_order_request(user_id):  # покупатель нажал оформление заказа. спрашиваем у него номер телефона
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    conn.execute("UPDATE basket set status = 'waiting_phone_number' WHERE user_id = ?", ([user_id]))
    conn.commit()
    conn.close()
    bot.send_message(user_id, Lang_RU.Message_phone_number)


def check_phone_number(user_id, text): #проверка телефона введенного покупателем. И отправка заказа на обработку
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    status = conn.execute("SELECT status FROM basket WHERE user_id = ?", ([user_id]))
    status = status.fetchall()
    if status[0][0] == 'waiting_phone_number':
        if re.match('(8|\+7|9)\d{9,10}',text):
            bot.send_message(user_id,Lang_RU.Message_order_processing)
            conn.execute("UPDATE basket set status = 0 WHERE user_id = ?", ([user_id]))
            conn.execute("UPDATE userslist set status = 'waiting_execute_order' WHERE id = ?", ([user_id]))
            answer = 'Заказ {} телефон {} \n'.format(user_id, text)
            order = conn.execute("SELECT products.name, products.price, basket_list.amount, basket_list.sum \
                FROM products JOIN basket_list ON products.id=basket_list.product_id \
                WHERE basket_list.user_id = ? AND basket_list.amount > 0", ([user_id]))
            for i in order:
                answer += '{} {}р х {} = {}р. \n'.format(i[0],i[1],i[2],i[3])

            orders_amount = conn.execute("SELECT cost FROM basket WHERE user_id=?", ([user_id]))
            orders_amount = orders_amount.fetchall()
            answer += 'Итоговая стоимость: '
            answer += str(orders_amount[0][0])
            answer += 'p'
            order_id = 'taken' + str(user_id)
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Заказ принят", callback_data=order_id))
            bot.send_message(config.ID_Admin, answer, reply_markup=markup)

            date = datetime.datetime.now()
            history = conn.execute("SELECT id_order, user_id, product_id, amount, sum FROM basket_list \
                WHERE user_id = ? and amount > 0", ([user_id]))
            for i in history:
                c.execute("INSERT INTO history_orders VALUES (?,?,?,?,?,?)",(i[0], i[1], i[2], i[3], i[4], date))

            conn.execute("UPDATE basket_list set amount = 0, sum = 0 WHERE user_id =?", ([user_id])) 
            conn.execute("UPDATE userslist set date_order = ?, phone_number = ? WHERE id = ?", ([date, text, user_id]))
            conn.execute("UPDATE basket set cost = 0, product_amount = 0 WHERE user_id = ?", ([user_id]))
        else:
            bot.send_message(user_id, Lang_RU.Message_number_error)
    conn.commit()
    conn.close()


def order_taken(order_id): # подтверждение взятия заказа
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    conn.execute("UPDATE userslist set orders_amount = orders_amount+1, status = 0 WHERE id = ?", ([order_id]))

    conn.commit()
    conn.close()


def add_product(): # запуск добавления товара в каталог админом
    conn = sqlite3.connect('mybd.db')
    c = conn.cursor()
    c.execute("INSERT INTO products (status) VALUES ('is_being_created')")
    conn.commit()
    conn.close()
    admin.state='ADD_NAME'
    bot.send_message(config.ID_Admin,Lang_RU.Message_product_add)





admin = AdminStates('NULL')
bot = telebot.TeleBot(config.TOKEN)


@bot.message_handler(commands=['start'])
def command_handler(message):
    check_user(message.from_user.id, message.from_user.first_name, 
    	message.from_user.username, message.from_user.language_code)
    if message.chat.id == config.ID_Admin:                          # меню админа
        user_markup=telebot.types.ReplyKeyboardMarkup(True,False)
        user_markup.row(Lang_RU.KEY_PRODUCT, Lang_RU.KEY_BASKET)
        user_markup.row(Lang_RU.ADMIN_KEY_ADD, Lang_RU.ADMIN_KEY_EDIT)
        user_markup.row(Lang_RU.ADMIN_KEY_DAILY_ORDERS, Lang_RU.ADMIN_KEY_ACTIVE_BUYERS)
        bot.send_message(config.ID_Admin,Lang_RU.Start_text,reply_markup=user_markup)
    else:                                                          # меню покупателей
        user_markup=telebot.types.ReplyKeyboardMarkup(True,False)
        user_markup.row(Lang_RU.KEY_PRODUCT,Lang_RU.KEY_BASKET)
        user_markup.row(Lang_RU.KEY_ABOUT)
        bot.send_message(message.from_user.id,Lang_RU.Start_text,reply_markup=user_markup)


@bot.message_handler(commands=['help'])
def handle_text(message):
    bot.send_message(message.chat.id, Lang_RU.Help_text)


@bot.message_handler(commands=['create_bd'])   #команда для создания новой базы данных (предварительно удалить или переименовать старую)
def command_handler(message):
    if message.chat.id == config.ID_Admin:
        create_bd()


@bot.message_handler(content_types=["text"])
def handle_text(message):
    if message.text==Lang_RU.KEY_PRODUCT:
        get_products(message.chat.id)

    elif message.text==Lang_RU.KEY_BASKET:
        get_basket(message.chat.id)

    elif message.text==Lang_RU.KEY_ABOUT:
        bot.send_message(message.from_user.id,Lang_RU.Message_about)

    elif message.text==Lang_RU.ADMIN_KEY_ADD:
        if message.chat.id ==config.ID_Admin:
            add_product()

    elif message.text==Lang_RU.ADMIN_KEY_EDIT:
        if message.chat.id ==config.ID_Admin:
        	showing_products_editor()

    elif message.text==Lang_RU.ADMIN_KEY_DAILY_ORDERS:
        if message.chat.id ==config.ID_Admin:
            showing_daily_orders()

    elif message.text==Lang_RU.ADMIN_KEY_ACTIVE_BUYERS:
        if message.chat.id ==config.ID_Admin:
            showing_active_buyers()

    else:
        if message.chat.id ==config.ID_Admin:
            admin_control(message.text)
        check_phone_number(message.chat.id,message.text)

@bot.message_handler(content_types=['photo']) 
def photo_handler(message):                    # фото принимаем только от админа в момент добавления фото товара
    if message.from_user.id == config.ID_Admin:
        admin_control(str(message.photo[-1].file_id))


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data[:3] == "add":
        user_product_add(call.from_user.id, int(call.data[3:]), int(call.message.message_id))
    elif call.data[:3] == "sub":
        user_product_sub(call.from_user.id, int(call.data[3:]), int(call.message.message_id))
    elif call.data[:3] == "del":
    	product_delete(int(call.data[3:]), int(call.message.message_id))
    elif call.data == 'order':
        user_order_request(call.from_user.id)
    elif call.data[:5] == 'taken':
        order_taken(call.data[5:])



if __name__ == '__main__':
    bot.polling(none_stop=True)