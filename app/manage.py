from flask import Flask, render_template, request, redirect, url_for, session
from flask_mail import Mail, Message
import sqlite3
import os
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Length, Email
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required
from flask_login import logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import time
from time import strftime
import pandas as pd
import xlsxwriter
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Color, colors, PatternFill
from openpyxl.styles.borders import Border, Side
import numpy as np
from numpy import array


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///diacompanion.db'
app.config['TESTING'] = False
app.config['MAIL_SERVER'] = 'smtp.yandex.ru'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'dnewnike@yandex.ru'
app.config['MAIL_PASSWORD'] = 'AjPR6kAs897jasb'
app.config['MAIL_DEFAULT_SENDER'] = ('Еженедельник', 'dnewnike@yandex.ru')
app.config['MAIL_MAX_EMAILS'] = None
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_ASCII_ATTACHMENTS'] = False
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
mail = Mail(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(15))


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя',
                           validators=[InputRequired(), Length(min=5, max=15)])
    password = PasswordField('Пароль', validators=[InputRequired(),
                                                   Length(min=8, max=15)])
    remember = BooleanField('Запомнить меня')


class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(),
                                             Email(message='Invalid email'),
                                             Length(max=50)])
    username = StringField('Имя пользователя', validators=[InputRequired(),
                                                           Length(min=5,
                                                                  max=15)])
    password = PasswordField('Пароль', validators=[InputRequired(),
                                                   Length(min=8, max=15)])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def zero():
    # Перенаправляем на страницу входа/регистрации
    return redirect(url_for('login'))


@app.route('/news')
@login_required
def news():
    # Главная страница
    session['username'] = current_user.username
    session['user_id'] = current_user.id
    session['date'] = datetime.datetime.today().date()
    return render_template("news.html", name=session['username'])


@app.route('/search_page')
@login_required
def search_page():
    # Поисковая страница
    return render_template("search_page.html", name=session['username'])


@app.route('/searchlink/<string:search_string>')
def searchlink(search_string):
    # Работа бокового меню
    path = os.path.dirname(os.path.abspath(__file__))
    db = os.path.join(path, 'diacompanion.db')
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("""SELECT DISTINCT (name) name,_id FROM
                constant_food WHERE category LIKE ?
                GROUP BY name""", ('%{}%'.format(search_string),))
    result = cur.fetchall()
    con.close()

    return render_template('search_page.html', result=result,
                           name=session['username'])


@app.route('/search', methods=['POST'])
def search():
    # Основная функция сайта - поиск по базе данных
    if request.method == 'POST':
        search_string = request.form['input_query']
        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()

        cur.execute(""" SELECT category FROM constant_foodGroups""")
        category_a = cur.fetchall()
        if (request.form['input_query'],) in category_a:
            cur.execute('''SELECT name,_id FROM constant_food
                        WHERE category LIKE ?
                        GROUP BY name''', ('%{}%'.format(search_string),))
            result = cur.fetchall()
        else:
            cur.execute('''SELECT name,_id FROM constant_food
                        WHERE name LIKE ?
                        GROUP BY name''', ('%{}%'.format(search_string),))
            result = cur.fetchall()
        con.close()
        return render_template('search_page.html', result=result,
                               name=session['username'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Авторизация пользователя
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('news'))
        return '<h1>Неверное имя пользователя или пароль</h1>'

    return render_template('login.html', form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Регистрация пользователя
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data,
                                                 method='sha256')
        new_user = User(username=form.username.data, email=form.email.data,
                        password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return '<h1>Новый пользователь создан</h1>'

    return render_template('signup.html', form=form)


@app.route('/logout')
@login_required
def logout():
    # Выход из сети
    logout_user()
    return redirect(url_for('login'))


@app.route('/favourites', methods=['POST', 'GET'])
def favour():
    # Добавляем блюда в список избранного
    if request.method == 'POST':

        L1 = request.form.getlist('row')
        brf1 = datetime.time(7, 0)
        brf2 = datetime.time(11, 30)
        obed1 = datetime.time(12, 0)
        obed2 = datetime.time(15, 0)
        ujin1 = datetime.time(18, 0)
        ujin2 = datetime.time(22, 0)
        now = datetime.datetime.now().time()

        typ = request.form['food_type']
        if typ == "Авто":
            if now < brf1 and now > brf2:
                typ = "Завтрак"
            elif now < obed2 and now > obed1:
                typ = "Обед"
            elif now < ujin2 and now > ujin1:
                typ = "Ужин"
            else:
                typ = "Перекус"

        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()

        time = request.form['timer']
        if time == "":
            x = datetime.datetime.now().time()
            time = x.strftime("%R")
        else:
            x = datetime.datetime.strptime(time, "%H:%M")
            time = x.strftime("%R")

        date = request.form['calendar']
        if date == "":
            y = datetime.datetime.today().date()
            date = y.strftime("%d.%m.%Y")
            week_day = y.strftime("%A")
        else:
            y = datetime.datetime.strptime(date, "%Y-%m-%d")
            y = y.date()
            date = y.strftime("%d.%m.%Y")
            week_day = y.strftime("%A")

        if week_day == 'Monday':
            week_day = 'Понедельник'
        elif week_day == 'Tuesday':
            week_day = 'Вторник'
        elif week_day == 'Wednesday':
            week_day = 'Среда'
        elif week_day == 'Thursday':
            week_day = 'Четверг'
        elif week_day == 'Friday':
            week_day = 'Пятница'
        elif week_day == 'Saturday':
            week_day = 'Суббота'
        else:
            week_day = 'Воскресенье'

        libra = request.form['libra']
        if libra == "":
            libra = "150"

        index_b = request.form['index_b']
        if index_b == "":
            index_b = "3.88"

        index_a = request.form['index_a']
        if index_a == "":
            index_a = "6.88"

        # Достаем все необходимые для диеты параметры
        for i in range(len(L1)):
            cur.execute('''SELECT prot FROM constant_food
                        WHERE name = ?''', (L1[i],))
            prot = cur.fetchall()
            cur.execute('''SELECT carbo FROM constant_food
                        WHERE name = ?''', (L1[i],))
            carbo = cur.fetchall()
            cur.execute('''SELECT fat FROM constant_food
                        WHERE name = ?''', (L1[i],))
            fat = cur.fetchall()
            cur.execute('''SELECT ec FROM constant_food
                        WHERE name = ?''', (L1[i],))
            ec = cur.fetchall()
            cur.execute('''SELECT water FROM constant_food
                        WHERE name = ?''', (L1[i],))
            water = cur.fetchall()
            cur.execute('''SELECT mds FROM constant_food
                        WHERE name = ?''', (L1[i],))
            mds = cur.fetchall()
            cur.execute('''SELECT kr FROM constant_food
                        WHERE name = ?''', (L1[i],))
            kr = cur.fetchall()
            cur.execute('''SELECT pv FROM constant_food
                        WHERE name = ?''', (L1[i],))
            pv = cur.fetchall()
            cur.execute('''SELECT ok FROM constant_food
                        WHERE name = ?''', (L1[i],))
            ok = cur.fetchall()
            cur.execute('''SELECT zola FROM constant_food
                        WHERE name = ?''', (L1[i],))
            zola = cur.fetchall()
            cur.execute('''SELECT na FROM constant_food
                        WHERE name = ?''', (L1[i],))
            na = cur.fetchall()
            cur.execute('''SELECT k FROM constant_food
                        WHERE name = ?''', (L1[i],))
            k = cur.fetchall()
            cur.execute('''SELECT ca FROM constant_food
                        WHERE name = ?''', (L1[i],))
            ca = cur.fetchall()
            cur.execute('''SELECT mg FROM constant_food
                        WHERE name = ?''', (L1[i],))
            mg = cur.fetchall()
            cur.execute('''SELECT p FROM constant_food
                        WHERE name = ?''', (L1[i],))
            p = cur.fetchall()
            cur.execute('''SELECT fe FROM constant_food
                        WHERE name = ?''', (L1[i],))
            fe = cur.fetchall()
            cur.execute('''SELECT a FROM constant_food
                        WHERE name = ?''', (L1[i],))
            a = cur.fetchall()
            cur.execute('''SELECT kar FROM constant_food
                        WHERE name = ?''', (L1[i],))
            kar = cur.fetchall()
            cur.execute('''SELECT re FROM constant_food
                        WHERE name = ?''', (L1[i],))
            re = cur.fetchall()
            cur.execute('''SELECT b1 FROM constant_food
                        WHERE name = ?''', (L1[i],))
            b1 = cur.fetchall()
            cur.execute('''SELECT b2 FROM constant_food
                        WHERE name = ?''', (L1[i],))
            b2 = cur.fetchall()
            cur.execute('''SELECT rr FROM constant_food
                        WHERE name = ?''', (L1[i],))
            rr = cur.fetchall()
            cur.execute('''SELECT c FROM constant_food
                        WHERE name = ?''', (L1[i],))
            c = cur.fetchall()
            cur.execute('''SELECT hol FROM constant_food
                        WHERE name = ?''', (L1[i],))
            hol = cur.fetchall()
            cur.execute('''SELECT nzhk FROM constant_food
                        WHERE name = ?''', (L1[i],))
            nzhk = cur.fetchall()
            cur.execute('''SELECT ne FROM constant_food
                        WHERE name = ?''', (L1[i],))
            ne = cur.fetchall()
            cur.execute('''SELECT te FROM constant_food
                        WHERE name = ?''', (L1[i],))
            te = cur.fetchall()
            for pr in prot:
                print(pr[0])
            for car in carbo:
                print(car[0])
            for fa in fat:
                print(fa[0])
            for energy in ec:
                print(energy[0])
            for wat in water:
                print(wat[0])
            for md in mds:
                print(md[0])
            for kr1 in kr:
                print(kr1[0])
            for pv1 in pv:
                print(pv1[0])
            for ok1 in ok:
                print(ok1[0])
            for zola1 in zola:
                print(zola1[0])
            for na1 in na:
                print(na1[0])
            for k1 in k:
                print(k1[0])
            for ca1 in ca:
                print(ca1[0])
            for mg1 in mg:
                print(mg1[0])
            for p1 in p:
                print(p1[0])
            for fe1 in fe:
                print(fe1[0])
            for a1 in a:
                print(a1[0])
            for kar1 in kar:
                print(kar1[0])
            for re1 in re:
                print(re1[0])
            for b11 in b1:
                print(b11[0])
            for b21 in b2:
                print(b21[0])
            for rr1 in rr:
                print(rr1[0])
            for c1 in c:
                print(c1[0])
            for hol1 in hol:
                print(hol1[0])
            for nzhk1 in nzhk:
                print(nzhk1[0])
            for ne1 in ne:
                print(ne1[0])
            for te1 in te:
                print(te1[0])
            pustoe = ''
            cur.execute("""INSERT INTO favourites
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                        ?,?,?,?,?,?,?,?,?,?,?,?,?)""", (session['user_id'],
                        week_day,
                        date, time, typ, L1[i], libra, index_b, index_a,
                        str(pr[0]), str(car[0]), str(fa[0]), str(energy[0]),
                        pustoe, str(wat[0]), str(md[0]), str(kr1[0]),
                        str(pv1[0]), str(ok1[0]), str(zola1[0]), str(na1[0]),
                        str(k1[0]), str(ca1[0]), str(mg1[0]), str(p1[0]),
                        str(fe1[0]), str(a1[0]), str(kar1[0]), str(re1[0]),
                        str(b11[0]), str(b21[0]), str(rr1[0]),
                        str(c1[0]), str(hol1[0]), str(nzhk1[0]),
                        str(ne1[0]), str(te1[0])))
            con.commit()
        con.close()

    return redirect(url_for('news'))


@app.route('/activity')
@login_required
def activity():
    # Страница физической активности
    path = os.path.dirname(os.path.abspath(__file__))
    db = os.path.join(path, 'diacompanion.db')
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("""SELECT date,time,min,type,user_id
                    FROM activity WHERE user_id = ?""", (session['user_id'],))
    Act = cur.fetchall()
    con.close()
    return render_template('activity.html', Act=Act)


@app.route('/add_activity', methods=['POST'])
@login_required
def add_activity():
    # Добавляем нагрузку в базу данных
    if request.method == 'POST':
        td = datetime.datetime.today().date()
        date = td.strftime("%d.%m.%Y")
        min1 = request.form['min']
        type1 = request.form['type1']
        if type1 == '1':
            type1 = 'Ходьба'
        elif type1 == '2':
            type1 = 'Зарядка'
        elif type1 == '3':
            type1 = 'Спорт'
        elif type1 == '4':
            type1 = 'Уборка'
        elif type1 == '5':
            type1 = 'Работа в саду'
        else:
            type1 = 'Сон'
        time1 = request.form['timer']
        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("""INSERT INTO activity VALUES(?,?,?,?,?)""",
                    (session['user_id'], min1, type1, time1, date))
        con.commit()
        con.close()
    return redirect(url_for('activity'))


@app.route('/lk')
@login_required
def lk():
    # Выводим названия блюд (дневник на текущую неделю)
    td = datetime.datetime.today().date()
    if td.strftime("%A") == 'Monday':
        delta = datetime.timedelta(0)
    elif td.strftime("%A") == 'Tuesday':
        delta = datetime.timedelta(1)
    elif td.strftime("%A") == 'Wednesday':
        delta = datetime.timedelta(2)
    elif td.strftime("%A") == 'Thursday':
        delta = datetime.timedelta(3)
    elif td.strftime("%A") == 'Friday':
        delta = datetime.timedelta(4)
    elif td.strftime("%A") == 'Saturday':
        delta = datetime.timedelta(5)
    else:
        delta = datetime.timedelta(6)

    m = td - delta
    M = m.strftime("%d.%m.%Y")
    t = m + datetime.timedelta(1)
    T = t.strftime("%d.%m.%Y")
    w = m + datetime.timedelta(2)
    W = w.strftime("%d.%m.%Y")
    tr = m + datetime.timedelta(3)
    TR = tr.strftime("%d.%m.%Y")
    fr = m + datetime.timedelta(4)
    FR = fr.strftime("%d.%m.%Y")
    st = m + datetime.timedelta(5)
    ST = st.strftime("%d.%m.%Y")
    sd = m + datetime.timedelta(6)
    SD = sd.strftime("%d.%m.%Y")

    path = os.path.dirname(os.path.abspath(__file__))
    db = os.path.join(path, 'diacompanion.db')
    con = sqlite3.connect(db)
    cur = con.cursor()

    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Понедельник',
                                  'Завтрак', M))
    MondayZ = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""",
                (session['user_id'], 'Понедельник', 'Обед', M))
    MondayO = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""",
                (session['user_id'], 'Понедельник', 'Ужин', M))
    MondayY = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Понедельник',
                                  'Перекус', M))
    MondayP = cur.fetchall()

    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Вторник',
                                  'Завтрак', T))
    TuesdayZ = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Вторник',
                                  'Обед', T))
    TuesdayO = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Вторник',
                                  'Ужин', T))
    TuesdayY = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Вторник',
                                  'Перекус', T))
    TuesdayP = cur.fetchall()

    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Среда',
                                  'Завтрак', W))
    WednesdayZ = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Среда',
                                  'Обед', W))
    WednesdayO = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Среда',
                                  'Ужин', W))
    WednesdayY = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Среда',
                                  'Перекус', W))
    WednesdayP = cur.fetchall()

    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Четверг',
                                  'Завтрак', TR))
    ThursdayZ = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Четверг',
                                  'Обед', TR))
    ThursdayO = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Четверг',
                                  'Ужин', TR))
    ThursdayY = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Четверг',
                                  'Перекус', TR))
    ThursdayP = cur.fetchall()

    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Пятница',
                                  'Завтрак', FR))
    FridayZ = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Пятница',
                                  'Обед', FR))
    FridayO = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Пятница',
                                  'Ужин', FR))
    FridayY = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type FROM favourites
                WHERE user_id = ? AND week_day = ?
                AND type = ?
                AND date= ?""", (session['user_id'], 'Пятница',
                                 'Перекус', FR))
    FridayP = cur.fetchall()

    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Суббота',
                                  'Завтрак', ST))
    SaturdayZ = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Суббота',
                                  'Обед', ST))
    SaturdayO = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Суббота',
                                  'Ужин', ST))
    SaturdayY = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type = ?
                AND date = ?""", (session['user_id'], 'Суббота',
                                  'Перекус', ST))
    SaturdayP = cur.fetchall()

    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type =?
                AND date = ?""", (session['user_id'], 'Воскресенье',
                                  'Завтрак', SD))
    SundayZ = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type =?
                AND date = ?""", (session['user_id'], 'Воскресенье',
                                  'Обед', SD))
    SundayO = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type =?
                AND date = ?""", (session['user_id'], 'Воскресенье',
                                  'Ужин', SD))
    SundayY = cur.fetchall()
    cur.execute(""" SELECT food,week_day,time,date,type
                FROM favourites WHERE user_id = ?
                AND week_day = ?
                AND type =?
                AND date = ?""", (session['user_id'], 'Воскресенье',
                                  'Перекус', SD))
    SundayP = cur.fetchall()
    con.close()

    return render_template('bootstrap_lk.html', name=session['username'],
                           MondayZ=MondayZ,
                           MondayO=MondayO,
                           MondayY=MondayY,
                           MondayP=MondayP,
                           TuesdayZ=TuesdayZ,
                           TuesdayO=TuesdayO,
                           TuesdayY=TuesdayY,
                           TuesdayP=TuesdayP,
                           WednesdayZ=WednesdayZ,
                           WednesdayO=WednesdayO,
                           WednesdayY=WednesdayY,
                           WednesdayP=WednesdayP,
                           ThursdayZ=ThursdayZ,
                           ThursdayO=ThursdayO,
                           ThursdayY=ThursdayY,
                           ThursdayP=ThursdayP,
                           FridayZ=FridayZ,
                           FridayO=FridayO,
                           FridayY=FridayY,
                           FridayP=FridayP,
                           SaturdayZ=SaturdayZ,
                           SaturdayO=SaturdayO,
                           SaturdayY=SaturdayY,
                           SaturdayP=SaturdayP,
                           SundayZ=SundayZ,
                           SundayO=SundayO,
                           SundayY=SundayY,
                           SundayP=SundayP,
                           m=M,
                           t=T,
                           w=W,
                           tr=TR,
                           fr=FR,
                           st=ST,
                           sd=SD)


@app.route('/delete', methods=['POST'])
@login_required
def delete():
    # Удаление данных из дневника за неделю
    if request.method == 'POST':
        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()
        L = request.form.getlist('checked')
        for i in range(len(L)):
            L1 = L[i].split('/')
            cur.execute('''DELETE FROM favourites WHERE food = ?
                        AND date = ?
                        AND time = ?
                        AND type = ?
                        AND user_id = ?''', (L1[0], L1[1], L1[2], L1[3],
                                             session['user_id']))
        con.commit()
        con.close()
    return redirect(url_for('lk'))


@app.route('/remove', methods=['POST'])
@login_required
def remove():
    # Удаление данных из физической активности за неделю
    if request.method == 'POST':
        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()
        L = request.form.getlist('selected')
        for i in range(len(L)):
            L1 = L[i].split('/')

            cur.execute('''DELETE FROM activity WHERE date = ?
                        AND time = ?
                        AND min = ?
                        AND type = ?
                        AND user_id = ?''', (L1[0], L1[1], L1[2], L1[3],
                                             session['user_id']))
        con.commit()
        con.close()
    return redirect(url_for('activity'))


@app.route('/arch')
@login_required
def arch():
    # Архив за все время
    path = os.path.dirname(os.path.abspath(__file__))
    db = os.path.join(path, 'diacompanion.db')
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(
        """SELECT week_day,date,time,food,libra,type,index_b,
           index_a,prot,carbo,fat,energy
           FROM favourites WHERE user_id = ?""", (session['user_id'],))
    L = cur.fetchall()
    con.close()
    return render_template('arch.html', L=L)


@app.route('/email', methods=['GET', 'POST'])
@login_required
def email():
    # Отправляем отчет по почте отчет
    if request.method == 'POST':
        # Получили список имейлов на которые надо отправить
        mail1 = request.form.getlist('email_sendto')

        # Получили все необходимые данные из базы данных
        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute('''SELECT week_day,date,time,type,
                    food,libra,index_b,index_a,prot,carbo,
                    fat,energy,micr,water,mds,kr,pv,ok,
                    zola,na,k,ca,mg,p,fe,a,kar,re,b1,b2,
                    rr,c,hol,nzhk,ne,te FROM favourites
                    WHERE user_id = ?''', (session['user_id'],))
        L = cur.fetchall()
        cur.execute('''SELECT date,time,min,type FROM activity
                       WHERE user_id = ?''', (session['user_id'],))
        L1 = cur.fetchall()
        cur.execute('''SELECT date,time,hour FROM sleep
                        WHERE user_id =?''', (session['user_id'],))
        L2 = cur.fetchall()
        cur.execute('''SELECT date,type,index_b,index_a FROM favourites
                       GROUP BY date,type,index_a,index_b''')
        L3 = cur.fetchall()
        cur.execute('''SELECT DISTINCT date FROM
                        favourites WHERE user_id = ?''', (session['user_id'],))
        date = cur.fetchall()

        for d in date:
            print(d[0])                    
            cur.execute('''SELECT avg(water), avg(prot), avg(fat) FROM favourites
                           WHERE date = ?''', d)
            avg = cur.fetchall()
            print(avg[0])   
        con.close()      
        # Считаем средний уровень сахара
        c = []
        for i in range(len(L3)):
            a1 = float(L3[i][3])
            b = a1*1
            c.append(b)
        с1 = pd.Series(c)
        mean_index_a = с1.mean()
        print('Уровень сахара после', mean_index_a)
        d1 = []
        for i in range(len(L3)):
            a1 = float(L3[i][2])
            b = a1*1
            d1.append(b)
        d1 = pd.Series(d1)
        mean_index_b = d1.mean()
        print('Уровень сахара до', mean_index_b)

        # Приемы пищи
        food_weight = pd.DataFrame(L, columns=['День', 'Дата', 'Время', 'Тип',
                                               'Продукт', 'Масса (в граммах)',
                                               'Уровень сахара до',
                                               'Уровень сахара после',
                                               'Белки', 'Углеводы', 'Жиры',
                                               'Энергетическая ценность',
                                               'Микроэлементы', 'Вода', 'МДС',
                                               'Крахмал', 'Пиш. волокна',
                                               'Орган. кислота', 'Зола',
                                               'Натрий', 'Калий', 'Кальций',
                                               'Магний', 'Фосфор', 'Железо',
                                               'Ретинол', 'Каротин',
                                               'Ретиноловый экв.', 'Тиамин',
                                               'Рибофлавин',
                                               'Ниацин', 'Аскорбиновая кисл.',
                                               'Холестерин',
                                               'НЖК',
                                               'Ниационвый эквивалент',
                                               'Токоферол эквивалент'])
        food_weight = food_weight.drop('День', axis=1)
        # Считаем средний уровень микроэлементов
        list_of = ['Масса (в граммах)',
                   'Белки', 'Углеводы', 'Жиры',
                   'Энергетическая ценность',
                   'Микроэлементы', 'Вода', 'МДС',
                   'Крахмал', 'Пиш. волокна',
                   'Орган. кислота', 'Зола',
                   'Натрий', 'Калий', 'Кальций',
                   'Магний', 'Фосфор', 'Железо',
                   'Ретинол', 'Каротин',
                   'Ретиноловый экв.', 'Тиамин', 'Рибофлавин',
                   'Ниацин', 'Аскорбиновая кисл.',
                   'Холестерин', 'НЖК',
                   'Ниационвый эквивалент',
                   'Токоферол эквивалент']

        mean2 = list()
        for i in list_of:
            exp = pd.to_numeric(food_weight[i])
            mean2.append(exp.mean())
        print('Среднее по дням', mean2)
        a = food_weight.groupby(['Дата',
                                 'Тип',
                                 'Уровень сахара до',
                                 'Уровень сахара после',
                                 'Время']).agg({
                                  "Продукт": lambda tags: '\n'.join(tags),
                                  "Масса (в граммах)": lambda tags: '\n'.join(tags),
                                  "Белки": lambda tags: '\n'.join(tags),
                                  "Углеводы": lambda tags: '\n'.join(tags),
                                  "Жиры": lambda tags: '\n'.join(tags),
                                  "Энергетическая ценность": lambda tags: '\n'.join(tags),
                                  "Микроэлементы": lambda tags: '\n'.join(tags),
                                  "Вода": lambda tags: '\n'.join(tags),
                                  "МДС": lambda tags: '\n'.join(tags),
                                  "Крахмал": lambda tags: '\n'.join(tags),
                                  "Пиш. волокна": lambda tags: '\n'.join(tags),
                                  "Орган. кислота": lambda tags: '\n'.join(tags),
                                  "Зола": lambda tags: '\n'.join(tags),
                                  "Натрий": lambda tags: '\n'.join(tags),
                                  "Калий": lambda tags: '\n'.join(tags),
                                  "Кальций": lambda tags: '\n'.join(tags),
                                  "Магний": lambda tags: '\n'.join(tags),
                                  "Фосфор": lambda tags: '\n'.join(tags),
                                  "Железо": lambda tags: '\n'.join(tags),
                                  "Ретинол": lambda tags: '\n'.join(tags),
                                  "Каротин": lambda tags: '\n'.join(tags),
                                  "Ретиноловый экв.": lambda tags: '\n'.join(tags),
                                  "Тиамин": lambda tags: '\n'.join(tags),
                                  "Рибофлавин": lambda tags: '\n'.join(tags),
                                  "Ниацин": lambda tags: '\n'.join(tags),
                                  "Аскорбиновая кисл.": lambda tags: '\n'.join(tags),
                                  "Холестерин": lambda tags: '\n'.join(tags),
                                  "НЖК": lambda tags: '\n'.join(tags),
                                  "Ниационвый эквивалент": lambda tags: '\n'.join(tags),
                                  "Токоферол эквивалент": lambda tags: '\n'.join(tags)})

        # Физическая активность
        activity1 = pd.DataFrame(L1, columns=['Дата', 'Время', 'Минуты',
                                              'Тип'])
        length1 = str(len(activity1['Время'])+3)
        activity2 = activity1.groupby(['Дата',
                                       'Время']).agg({
                                        'Минуты': lambda tags: '\n'.join(tags),
                                        'Тип': lambda tags: '\n'.join(tags)})
        # Сон
        sleep1 = pd.DataFrame(L2, columns=['Дата', 'Время', 'Часы'])
        sleep2 = sleep1.groupby(['Дата'
                                 ]).agg({'Время': lambda tags: '\n'.join(tags),
                                         'Часы': lambda tags: '\n'.join(tags)})

        # Создаем общий Excel файл
        # можно добавить options={'strings_to_numbers': True} в writer
        # THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
        # my_file = os.path.join(THIS_FOLDER, '%s.xlsx' % session["username"])
        writer = pd.ExcelWriter('app\\%s.xlsx' % session["username"],
                                engine='xlsxwriter',
                                options={'strings_to_numbers': True,
                                         'default_date_format': 'dd/mm/yy',
                                         'nan_inf_to_errors': True})
        a.to_excel(writer, sheet_name='Приемы пищи')
        activity2.to_excel(writer, sheet_name='Физическая активность',
                           startrow=0, startcol=0)
        sleep2.to_excel(writer, sheet_name='Физическая активность',
                        startrow=0, startcol=4)
        writer.close()

        # Редактируем оформление приемов пищи
        wb = openpyxl.load_workbook('app\\%s.xlsx' % session["username"])
        sheet = wb['Приемы пищи']
        ws = wb.active
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = cell.alignment.copy(wrapText=True)
                cell.alignment = cell.alignment.copy(vertical='center')

        sheet.column_dimensions['A'].width = 13
        sheet.column_dimensions['B'].width = 13
        sheet.column_dimensions['C'].width = 20
        sheet.column_dimensions['D'].width = 25
        sheet.column_dimensions['E'].width = 13
        sheet.column_dimensions['F'].width = 50
        sheet.column_dimensions['G'].width = 20
        sheet.column_dimensions['H'].width = 20
        sheet.column_dimensions['I'].width = 20
        sheet.column_dimensions['J'].width = 20
        sheet.column_dimensions['K'].width = 20
        sheet.column_dimensions['L'].width = 20
        sheet.column_dimensions['M'].width = 20
        sheet.column_dimensions['P'].width = 20
        sheet.column_dimensions['Q'].width = 20
        sheet.column_dimensions['AA'].width = 20
        sheet.column_dimensions['AC'].width = 20
        sheet.column_dimensions['AE'].width = 20
        sheet.column_dimensions['AF'].width = 20
        sheet.column_dimensions['AH'].width = 20
        sheet.column_dimensions['AI'].width = 20

        a1 = ws['A1']
        a1.fill = PatternFill("solid", fgColor="FFCC99")
        b1 = ws['B1']
        b1.fill = PatternFill("solid", fgColor="FFCC99")
        c1 = ws['C1']
        c1.fill = PatternFill("solid", fgColor="FFCC99")
        d1 = ws['D1']
        d1.fill = PatternFill("solid", fgColor="FFCC99")
        e1 = ws['E1']
        e1.fill = PatternFill("solid", fgColor="FFCC99")
        f1 = ws['F1']
        f1.fill = PatternFill("solid", fgColor="FFCC99")
        g1 = ws['G1']
        g1.fill = PatternFill("solid", fgColor="FFCC99")
        h1 = ws['H1']
        h1.fill = PatternFill("solid", fgColor="FFCC99")
        i1 = ws['I1']
        i1.fill = PatternFill("solid", fgColor="FFCC99")
        j1 = ws['J1']
        j1.fill = PatternFill("solid", fgColor="FFCC99")
        k1 = ws['K1']
        k1.fill = PatternFill("solid", fgColor="FFCC99")
        l1 = ws['L1']
        l1.fill = PatternFill("solid", fgColor="FFCC99")
        m1 = ws['M1']
        m1.fill = PatternFill("solid", fgColor="FFCC99")
        n1 = ws['N1']
        n1.fill = PatternFill("solid", fgColor="FFCC99")
        o1 = ws['O1']
        o1.fill = PatternFill("solid", fgColor="FFCC99")
        p1 = ws['P1']
        p1.fill = PatternFill("solid", fgColor="FFCC99")
        q1 = ws['Q1']
        q1.fill = PatternFill("solid", fgColor="FFCC99")
        r1 = ws['R1']
        r1.fill = PatternFill("solid", fgColor="FFCC99")
        s1 = ws['S1']
        s1.fill = PatternFill("solid", fgColor="FFCC99")
        t1 = ws['T1']
        t1.fill = PatternFill("solid", fgColor="FFCC99")
        u1 = ws['U1']
        u1.fill = PatternFill("solid", fgColor="FFCC99")
        v1 = ws['V1']
        v1.fill = PatternFill("solid", fgColor="FFCC99")
        w1 = ws['W1']
        w1.fill = PatternFill("solid", fgColor="FFCC99")
        x1 = ws['X1']
        x1.fill = PatternFill("solid", fgColor="FFCC99")
        y1 = ws['Y1']
        y1.fill = PatternFill("solid", fgColor="FFCC99")
        z1 = ws['Z1']
        z1.fill = PatternFill("solid", fgColor="FFCC99")
        aa1 = ws['AA1']
        aa1.fill = PatternFill("solid", fgColor="FFCC99")
        ab1 = ws['AB1']
        ab1.fill = PatternFill("solid", fgColor="FFCC99")
        ac1 = ws['AC1']
        ac1.fill = PatternFill("solid", fgColor="FFCC99")
        ad1 = ws['AD1']
        ad1.fill = PatternFill("solid", fgColor="FFCC99")
        ae1 = ws['AE1']
        ae1.fill = PatternFill("solid", fgColor="FFCC99")
        af1 = ws['AF1']
        af1.fill = PatternFill("solid", fgColor="FFCC99")
        ah1 = ws['AH1']
        ah1.fill = PatternFill("solid", fgColor="FFCC99")
        ai1 = ws['AI1']
        ai1.fill = PatternFill("solid", fgColor="FFCC99")
        ag1 = ws['AG1']
        ag1.fill = PatternFill("solid", fgColor="FFCC99")
        thin_border = Border(left=Side(style='thin'),
                             right=Side(style='thin'),
                             top=Side(style='thin'),
                             bottom=Side(style='thin'))

        for row in ws.iter_rows():
            for cell in row:
                cell.border = thin_border

        merged_cells_range = ws.merged_cells.ranges

        for merged_cell in merged_cells_range:
            merged_cell.shift(0, 2)
        ws.insert_rows(1, 2)

        length = str(len(a['Микроэлементы'])+3)

        if (len(a['Микроэлементы'])+3) > 3:
            sheet.merge_cells('L4:L%s' % length)
        l4 = ws['L4']
        l4.fill = PatternFill("solid", fgColor="FFCC99")
        ws['A2'] = 'Приемы пищи'
        ws['A1'] = 'Исаков Артём Олегович'
        sheet.merge_cells('A1:AF1')
        sheet.merge_cells('A2:AF2')

        length2 = str(len(a['Микроэлементы'])+5)
        ws['A%s' % length2] = 'Срденее за период'
        sheet.merge_cells('A%s:B%s' % (length2,length2))
        ws['C%s' % length2 ] = mean_index_b
        ws['D%s' % length2 ] = mean_index_a
        i = 0
        for c in ['G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI']:
            print(f'{c}%s' % length2 +' ' +str(mean2[i]))
            ws[f'{c}%s' % length2] = str(mean2[i])
            i = i+1
        # length1 = str(len(activity1['Время'])+3)
        # for b in ['G','H']:
        #     for i in range(4,((len(a['Микроэлементы'])+4))):
        #         k=i
        #         print(k)
        #         print(b)
        #         cs = sheet['%s' % b+str(k) ]
        #         cs.alignment = Alignment(horizontal='left')

        wb.save('app\\%s.xlsx' % session["username"])
        wb.close()

        # Форматируем физическую активность как надо
        wb = openpyxl.load_workbook('app\\%s.xlsx' % session["username"])
        sheet1 = wb['Физическая активность']

        for row in sheet1.iter_rows():
            for cell in row:
                cell.alignment = cell.alignment.copy(wrapText=True)
                cell.alignment = cell.alignment.copy(vertical='center')
                cell.alignment = cell.alignment.copy(horizontal='center')

        thin_border = Border(left=Side(style='thin'),
                             right=Side(style='thin'),
                             top=Side(style='thin'),
                             bottom=Side(style='thin'))

        for row in sheet1.iter_rows():
            for cell in row:
                cell.border = thin_border

        merged_cells_range = sheet1.merged_cells.ranges

        for merged_cell in merged_cells_range:
            merged_cell.shift(0, 2)
        sheet1.insert_rows(1, 2)

        sheet1['A1'] = 'Исаков Артём Олегович'
        sheet1['A2'] = 'Физическая активность'
        sheet1['E2'] = 'Сон'
        sheet1.merge_cells('A1:G1')
        sheet1.merge_cells('A2:D2')
        sheet1.merge_cells('E2:G2')

        for row in sheet1['D4:D%s' % length1]:
            for cell in row:
                cell.alignment = cell.alignment.copy(wrapText=True)
                cell.alignment = cell.alignment.copy(vertical='top')
                cell.alignment = cell.alignment.copy(horizontal='left')

        sheet1.column_dimensions['A'].width = 13
        sheet1.column_dimensions['B'].width = 13
        sheet1.column_dimensions['C'].width = 13
        sheet1.column_dimensions['D'].width = 20
        sheet1.column_dimensions['E'].width = 13
        sheet1.column_dimensions['F'].width = 13
        sheet1.column_dimensions['G'].width = 13
        a1 = sheet1['A3']
        a1.fill = PatternFill("solid", fgColor="FFCC99")
        b1 = sheet1['B3']
        b1.fill = PatternFill("solid", fgColor="FFCC99")
        c1 = sheet1['C3']
        c1.fill = PatternFill("solid", fgColor="FFCC99")
        d1 = sheet1['D3']
        d1.fill = PatternFill("solid", fgColor="FFCC99")
        e1 = sheet1['E3']
        e1.fill = PatternFill("solid", fgColor="FFCC99")
        f1 = sheet1['F3']
        f1.fill = PatternFill("solid", fgColor="FFCC99")
        g1 = sheet1['G3']
        g1.fill = PatternFill("solid", fgColor="FFCC99")

        wb.save('app\\%s.xlsx' % session["username"])
        wb.close()
        # Отправляем по почте
        msg = Message(recipients=[mail1])
        msg.subject = "Никнейм пользователя: %s" % session["username"]
        msg.body = 'Электронный отчет'
        with app.open_resource('%s.xlsx' % session["username"]) as attach:
            msg.attach('%s.xlsx' % session["username"], 'Sheet/xlsx',
                       attach.read())
        # mail.send(msg)

    return redirect(url_for('lk'))


if __name__ == '__main__':
    app.run(debug=True)
