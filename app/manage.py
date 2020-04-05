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

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['SQLALCHEMY_DATABASE_URI'] = \
    'sqlite:///diacompanion.db'
app.config['TESTING'] = False
app.config['MAIL_SERVER'] = 'smtp.yandex.ru'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'art.isakow@yandex.ru'
app.config['MAIL_PASSWORD'] = 'Justice1m'
app.config['MAIL_DEFAULT_SENDER'] = ('Еженедельник', 'art.isakow@yandex.ru')
app.config['MAIL_MAX_EMAILS'] = None

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
    cur.execute("""SELECT DISTINCT (name) name ,_id FROM
                receipts WHERE category LIKE ?
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

        cur.execute(""" SELECT category FROM receiptsGroups""")
        category_b = cur.fetchall()

        if (request.form['input_query'],) in category_a:
            cur.execute("""SELECT name, _id FROM
                        constant_food WHERE category LIKE ?
                        GROUP BY name""", ('%{}%'.format(search_string),))
            result = cur.fetchall()
        elif (request.form['input_query'],) in category_b:
            cur.execute("""SELECT name, _id, additional FROM
                        receipts WHERE category LIKE ?
                        GROUP BY name""", ('%{}%'.format(search_string),))
            result = cur.fetchall()
        else:
            cur.execute("""SELECT name, _id, additional FROM
                        constant_food WHERE name LIKE ?
                        GROUP BY name""", ('%{}%'.format(search_string),))
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

        select = request.form['food_type']
        if select == "Авто":
            if now < brf1 and now > brf2:
                select = "Завтрак"
            elif now < obed2 and now > obed1:
                select = "Обед"
            elif now < ujin2 and now > ujin1:
                select = "Ужин"
            else:
                select = "Перекус"

        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()

        time = request.form['timer']
        if time == "":
            y = datetime.datetime.now().time()
            yy = y.strftime("%R")
        else:
            y = datetime.datetime.strptime(time, "%H:%M")
            yy = y.strftime("%R")

        date = request.form['calendar']
        if date == "":
            x = datetime.datetime.today().date()
            xx = x.strftime("%A")
        else:
            x = datetime.datetime.strptime(date, "%Y-%m-%d")
            x = x.date()
            xx = x.strftime("%A")

        for i in range(len(L1)):
            cur.execute("""INSERT INTO favourites VALUES(?,?,?,?,?,?)""",
                        (session['user_id'], xx, x, yy, L1[i], select))
            con.commit()
        con.close()
    return redirect(url_for('news'))


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
    elif td.strftime("%A") == 'Suterday':
        delta = datetime.timedelta(5)
    else:
        delta = datetime.timedelta(6)

    m = td - delta
    M = m.strftime("%d/%m/%Y")
    t = m + datetime.timedelta(1)
    T = t.strftime("%d/%m/%Y")
    w = m + datetime.timedelta(2)
    W = w.strftime("%d/%m/%Y")
    tr = m + datetime.timedelta(3)
    TR = tr.strftime("%d/%m/%Y")
    fr = m + datetime.timedelta(4)
    FR = fr.strftime("%d/%m/%Y")
    st = m + datetime.timedelta(5)
    ST = st.strftime("%d/%m/%Y")
    sd = m + datetime.timedelta(6)
    SD = sd.strftime("%d/%m/%Y")

    path = os.path.dirname(os.path.abspath(__file__))
    db = os.path.join(path, 'diacompanion.db')
    con = sqlite3.connect(db)
    cur = con.cursor()

    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Monday',
                                      'Завтрак', m))
    MondayZ = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Monday', 'Обед', m))
    MondayO = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Monday', 'Ужин', m))
    MondayY = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Monday',
                                      'Перекус', m))
    MondayP = cur.fetchall()

    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Tuesday',
                                      'Завтрак', t))
    TuesdayZ = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Tuesday',
                                      'Обед', t))
    TuesdayO = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Tuesday',
                                      'Ужин', t))
    TuesdayY = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Tuesday',
                                      'Перекус', t))
    TuesdayP = cur.fetchall()

    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Wednesday',
                                      'Завтрак', w))
    WednesdayZ = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Wednesday',
                                      'Обед', w))
    WednesdayO = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Wednesday',
                                      'Ужин', w))
    WednesdayY = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Wednesday',
                                      'Перекус', w))
    WednesdayP = cur.fetchall()

    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Thursday',
                                      'Завтрак', tr))
    ThursdayZ = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Thursday',
                                      'Обед', tr))
    ThursdayO = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Thursday',
                                      'Ужин', tr))
    ThursdayY = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Thursday',
                                      'Перекус', tr))
    ThursdayP = cur.fetchall()

    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Friday',
                                      'Завтрак', fr))
    FridayZ = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Friday',
                                      'Обед', fr))
    FridayO = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Friday',
                                      'Ужин', fr))
    FridayY = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type FROM favourites
                WHERE user_id = ? AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Friday',
                                      'Перекус', fr))
    FridayP = cur.fetchall()

    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Saturday',
                                      'Завтрак', st))
    SaturdayZ = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Saturday',
                                      'Обед', st))
    SaturdayO = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Saturday',
                                      'Ужин', st))
    SaturdayY = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type = ?
                AND datetime = ?""", (session['user_id'], 'Saturday',
                                      'Перекус', st))
    SaturdayP = cur.fetchall()

    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type =?
                AND datetime = ?""", (session['user_id'], 'Sunday',
                                      'Завтрак', sd))
    SundayZ = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type =?
                AND datetime = ?""", (session['user_id'], 'Sunday',
                                      'Обед', sd))
    SundayO = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type =?
                AND datetime = ?""", (session['user_id'], 'Sunday',
                                      'Ужин', sd))
    SundayY = cur.fetchall()
    cur.execute(""" SELECT fav,date,time,datetime,type
                FROM favourites WHERE user_id = ?
                AND date = ?
                AND type =?
                AND datetime = ?""", (session['user_id'], 'Sunday',
                                      'Перекус', sd))
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
            cur.execute('''DELETE FROM favourites WHERE fav = ?
                        AND datetime = ?
                        AND time = ?
                        AND type = ? ''', (L1[0], L1[1], L1[2], L1[3]))
        con.commit()
        con.close()
    return redirect(url_for('lk'))


@app.route('/arch')
@login_required
def arch():
    # Архив за все время
    path = os.path.dirname(os.path.abspath(__file__))
    db = os.path.join(path, 'diacompanion.db')
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("""SELECT date,datetime,time,fav,type FROM favourites""")
    L = cur.fetchall()
    con.close()
    return render_template('arch.html', L=L)


@app.route('/email', methods=['GET'])
@login_required
def email():
    # Отправляем отчет по почте (пока что отправляем просто какой-то PDF)
    if request.method == 'GET':
        path = os.path.dirname(os.path.abspath(__file__))
        db = os.path.join(path, 'diacompanion.db')
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute('''SELECT date,datetime,time,fav,type FROM favourites''')
        L = cur.fetchall()
        con.close()
        s = pd.DataFrame(L, columns=['День недели', 'Дата', 'Время',
                                     'Избранное', 'Тип'])
        writer = pd.ExcelWriter('app\\table.xlsx', engine='xlsxwriter')
        s.to_excel(writer, 'Sheet1')
        writer.save()

        msg = Message(recipients=['art.isackov@gmail.com',
                                  'eupustozerov@etu.ru'])
        msg.subject = "Никнейм пользователя: %s" % session["username"]
        msg.body = 'Электронный отчет'
        with app.open_resource('table.xlsx') as attach:
            msg.attach('table.xlsx', 'Sheet/xlsx',
                       attach.read())
        mail.send(msg)

    return redirect(url_for('lk'))


if __name__ == '__main__':
    app.run(debug=True)
