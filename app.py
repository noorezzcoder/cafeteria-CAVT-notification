from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room
from flask_session import Session
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# إعدادات الجلسة
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_PERMANENT'] = True
app.permanent_session_lifetime = timedelta(days=1)  # الجلسة تدوم ليوم كامل مثلاً


Session(app)

# إعداد SocketIO بدون eventlet على Windows
socketio = SocketIO(app, async_mode='threading', manage_session=False)
#socketio = SocketIO(app, async_mode='eventlet')


orders = []

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.permanent = True
        username = request.form['username'].strip().lower()
        if username == 'owner':
            session['role'] = 'owner'
            return redirect(url_for('kitchen'))
        else:
            session['role'] = 'student'
            session['student_name'] = username
            return redirect(url_for('student'))
    return render_template('login.html')

@app.route('/student')
def student():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    name = session.get('student_name')
    return render_template('student.html', name=name, orders=orders)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    name = session.get('student_name')
    item = request.form['item']
    orders.append({'name': name, 'item': item, 'ready': False})

    # إرسال إشعار للـ owner
    message = f"🔔 طلب جديد من {name}: '{item}'"
    socketio.emit('new_order', {'message': message}, to='owner_room')

    flash("✅ تم إرسال طلبك.")
    return redirect(url_for('student'))


@app.route('/kitchen')
def kitchen():
    if session.get('role') != 'owner':
        return redirect(url_for('login'))
    return render_template('kitchen.html', orders=orders)

@app.route('/mark_ready/<int:order_id>')
def mark_ready(order_id):
    if session.get('role') != 'owner':
        return redirect(url_for('login'))
    if 0 <= order_id < len(orders):
        orders[order_id]['ready'] = True
        student_name = orders[order_id]['name']
        item = orders[order_id]['item']
        message = f"🍔 مرحبًا {student_name}، طلبك '{item}' جاهز!"
        socketio.emit('order_status', {'message': message}, to=student_name)
        flash(f"📢 الطلب جاهز للطالب: {student_name}")
    return redirect(url_for('kitchen'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@socketio.on('join')
def handle_join(data):
    join_room(data['name'])



if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)



