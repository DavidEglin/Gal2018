import os
import uuid
from flask import Flask, render_template, flash, redirect, url_for, logging, session, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, SelectField, FileField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.secret_key = "hkjlasdfbblasdkjgasdfgqowerqbfaosdfiuy7896"

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Config mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'd9*g1v!'
app.config['MYSQL_DB'] = 'gal2018'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init_mysql
mysql = MySQL(app)

#Check If Logged if logged In
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Nice try, but you need to be logged in first!', 'danger')
            return redirect(url_for('login'))
    return wrap

#Index Page
@app.route('/')
def index():
    return render_template('home.html')

#About Page
@app.route('/about')
def about():
    return render_template('about.html')

#Catagories Page
@app.route('/cat')
@is_logged_in
def cat():
    #Create cursor
    cur = mysql.connection.cursor()

    #Get catagories
    result = cur.execute("SELECT * FROM cat WHERE cat_hidden=0")

    cats = cur.fetchall()

    if result > 0:
        return render_template('cat.html', cats=cats)
    else:
        msg = 'No catagories found'
        return render_template('cat.html', msg=msg)

#Videos Page
@app.route('/videos/<string:cat_id>/')
@is_logged_in
def videos(cat_id):
    cur = mysql.connection.cursor()

    #Get videos
    result = cur.execute("SELECT * FROM video INNER JOIN cat ON cat.cat_id = video.vid_cat_id WHERE cat.cat_id= %s AND video.vid_hidden='0' ORDER BY video.vid_views DESC", [cat_id])

    vids = cur.fetchall()

    if result > 0:
        return render_template('videos.html', vids=vids)
    else:
        msg = 'There are no videos in this catagory'
        return render_template('videos.html', msg=msg)

#Video Player Page
@app.route('/video_player/<string:vid_id>/')
@is_logged_in
def videoplayer(vid_id):

    #Create Cursor - Add to viewed
    cur = mysql.connection.cursor()

    #update vid_views by 1
    cur.execute("UPDATE video SET vid_views=vid_views+1 WHERE vid_id=%s", [vid_id])

    #Commit to db
    mysql.connection.commit()

    #Get Video record
    result = cur.execute("SELECT * FROM video INNER JOIN cat ON cat.cat_id = video.vid_cat_id WHERE video.vid_id= %s", [vid_id])

    video = cur.fetchone()

    return render_template('video_player.html', video=video)

#Register User Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=4, max=75)])
    username = StringField('Username', [validators.Length(min=4, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message="Passwords Do Not Match")])
    confirm  = PasswordField('Confirm Password')

#User Register
@app.route('/register', methods=['GET', 'POST'])
@is_logged_in
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        username = form.username.data
        password = sha256_crypt.encrypt((str(form.password.data)))

        #Create Cursor
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users (users_name, users_username, users_pass) VALUES(%s, %s, %s)", (name, username, password))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('man_users'))
    return render_template('register.html', form=form)

#Manage users
@app.route('/man_users')
@is_logged_in
def man_users():
    #Create cursor
    cur = mysql.connection.cursor()

    #Get Users
    result = cur.execute("SELECT * FROM users")

    users = cur.fetchall()

    if result > 0:
        return render_template('man_users.html', users=users)
    else:
        msg = 'No Users found'
        return render_template('man_users.html', msg=msg)

    #Close connection
    cur.close()

    return render_template('dashboard.html')

#Delete User Page
@app.route('/del_users/<string:users_id>', methods=['POST'])
@is_logged_in
def del_users(users_id):

    #Create cursor
    cur = mysql.connection.cursor()

    #Delete Record
    cur.execute("DELETE FROM users WHERE users_id = %s", [users_id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('User succesfully deleted', 'success')
    return redirect(url_for('man_users'))

#Edit Users Page
@app.route('/edit_users/<string:users_id>', methods=['GET', 'POST'])
@is_logged_in
def edit_users(users_id):
    #Create Cursor
    cur = mysql.connection.cursor()

    #Execute Query
    cur.execute("SELECT * FROM users WHERE users_id = %s", [users_id])

    users = cur.fetchone()

    #Get Form
    form = RegisterForm(request.form)

    #Populate UsersForm fields
    form.name.data = users['users_name']
    form.username.data = users['users_username']

    if request.method == 'POST' and form.validate():
        name = request.form['name']
        username = request.form['username']
        password = sha256_crypt.encrypt((str(form.password.data)))

        #create cursor
        cur = mysql.connection.cursor()

        #Execute Query
        cur.execute("UPDATE users SET users_name=%s, users_username=%s, users_pass=%s WHERE users_id=%s",(name, username, password, users_id))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('User succesfully updated', 'success')
        return redirect(url_for('man_users'))

    return render_template('edit_users.html', form=form)

#Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
         #Get Form Data
         username = request.form['username']
         password_candidate = request.form['password']

         #create Cursor
         cur = mysql.connection.cursor()

         #Get User by username
         result = cur.execute("SELECT * FROM users WHERE users_username = %s", [username])

         if result > 0:
             #Get Stored hash
             data = cur.fetchone()
             password = data['users_pass']

             #Compare Passwords
             if sha256_crypt.verify(password_candidate, password):
                 # Passwordss
                 session['logged_in'] = True
                 session['username'] = username

                 flash('You are now logged in', 'success')
                 return redirect(url_for('cat'))

             else:
                error = 'Invalid Login'
                return render_template('login.html', error=error)

             #Close Connection
             cur.close()

         else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

#Logout Page
@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))

#Dashboard Page
@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')

#Cat Form Class
class CatForm(Form):
    cat_name = StringField('Name', [validators.Length(min=4, max=20)])
    cat_thumb = StringField('Thumbnail', [validators.Length(min=4)])
    cat_hidden = StringField('Hidden', [validators.Length(max=1)])

#Add Catagory Page
@app.route('/add_cat', methods=['GET', 'POST'])
@is_logged_in
def add_cat():
    form = CatForm(request.form)
    if request.method == 'POST' and form.validate():
        cat_name = form.cat_name.data
        cat_thumb = form.cat_thumb.data
        cat_hidden  = form.cat_hidden.data

        #create cursor
        cur = mysql.connection.cursor()

        #Execute Query
        cur.execute("INSERT INTO cat(cat_name, cat_thumb, cat_hidden) VALUES (%s, %s, %s)", (cat_name, cat_thumb, cat_hidden))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Catagory succesfully added', 'success')

        return redirect(url_for('man_cat'))

    return render_template('add_cat.html', form=form)

#Edit Catagory Page
@app.route('/edit_cat/<string:cat_id>', methods=['GET', 'POST'])
@is_logged_in
def edit_cat(cat_id):
    #Create Cursor
    cur = mysql.connection.cursor()

    #Execute Query
    cur.execute("SELECT * FROM cat WHERE cat_id = %s", [cat_id])

    cat = cur.fetchone()

    #Get Form
    form = CatForm(request.form)

    #Populate CatForm fields
    form.cat_name.data = cat['cat_name']
    form.cat_thumb.data = cat['cat_thumb']
    form.cat_hidden.data = cat['cat_hidden']

    if request.method == 'POST' and form.validate():
        cat_name = request.form['cat_name']
        cat_thumb = request.form['cat_thumb']
        cat_hidden  = request.form['cat_hidden']

        #create cursor
        cur = mysql.connection.cursor()

        #Execute Query
        cur.execute("UPDATE cat SET cat_name=%s, cat_thumb=%s, cat_hidden=%s WHERE cat_id=%s",(cat_name, cat_thumb, cat_hidden, cat_id))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Catagory succesfully updated', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_cat.html', form=form)

#Delete Catagory Page
@app.route('/del_cat/<string:cat_id>', methods=['POST'])
@is_logged_in
def del_cat(cat_id):

    #Create cursor
    cur = mysql.connection.cursor()

    #Delete Record
    cur.execute("DELETE FROM cat WHERE cat_id = %s", [cat_id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Catagory succesfully deleted', 'success')
    return redirect(url_for('man_cat'))

#Manage Catagories Page
@app.route('/man_cat')
@is_logged_in
def man_cat():
    #Create cursor
    cur = mysql.connection.cursor()

    #Get catagoried
    result = cur.execute("SELECT * FROM cat")

    cats = cur.fetchall()

    if result > 0:
        return render_template('man_cat.html', cats=cats)
    else:
        msg = 'No catagories found'
        return render_template('man_cat.html', msg=msg)

    #Close connection
    cur.close()

    return render_template('dashboard.html')

#Video Upload Form Class
class VideoUploadForm(Form):
    videotitle = StringField('Title', [validators.Length(min=1, max=75)])
    videocat = SelectField('cat_id'), [validators.length(min=1, max=10)]

@app.route("/add_video")
@is_logged_in
def add_video():
    form = VideoUploadForm(request.form)

    #Generate a new cursor
    cur = mysql.connection.cursor()

    #Get Catagories
    result = cur.execute("SELECT * FROM cat")

    cat = cur.fetchall()

    return render_template('upload.html', cat=cat)

#Video Upload Page
@app.route("/upload", methods=['POST'])
@is_logged_in
def upload():
    target = os.path.join(APP_ROOT, 'stage/')
    print(target)

    form = VideoUploadForm(request.form)
    if request.method == 'POST' and form.validate():
        videoname = request.form.get('videoname')
        videocat = request.form.get('videocat')


    if not os.path.isdir(target):
        os.mkdir(target)

    for file in request.files.getlist("file"):
        print(file)
        filename = file.filename
        filename = str(uuid.uuid4())
        destination = "/".join([target, filename])
        print(destination)
        file.save(destination)

        #Generate a new cursor
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO video (vid_name, vid_title, vid_cat_id) VALUES(%s, %s, %s)", (videoname, filename, videocat))

        # Commit to DB
        mysql.connection.commit()

        #retrieve last row from database
        lastrow = cur.lastrowid

        #Close connection
        cur.close()

        #Generate a new cursor
        cur = mysql.connection.cursor()

        #Get Catagories
        result = cur.execute("SELECT * FROM cat WHERE cat_id = %s", [videocat])

        cat = cur.fetchone()

        #Close Cursor
        cur.close()

    return render_template("complete.html", filename = filename, videoname = videoname, videocat = videocat, lastrow = lastrow, cat = cat)

@app.route("/complete")
@is_logged_in
def complete():

    return render_template("complete.html")

@app.route("/edit_video/<string:vid_id>", methods=['GET', 'POST'])
@is_logged_in
def edit_video(vid_id):

    #Create cursor
    cur = mysql.connection.cursor()

    #select video data
    result = cur.execute("SELECT * FROM video WHERE vid_id = %s", [vid_id])

    #define video
    video = cur.fetchone()

    #Close Cursor
    cur.close()

    #Create cursor
    cur = mysql.connection.cursor()

    #select video data
    result = cur.execute("SELECT * FROM cat")

    #define video
    cat = cur.fetchall()

    #Close Cursor
    cur.close()

    #Get form
    form = VideoUploadForm(request.form)

    #Populate Form fields
    form.videotitle.data = video['vid_title']

    if request.method == 'POST'and form.validate():
        videotitle = request.form['vid_title']

        #create cursor
        cur = mysql.connection.cursor()

        #execute Query
        cur.execute("UPDATE video SET vid_title=%s, vid_cat_id=%s WHERE vid_id=%s",(videotitle, cat_id))

        #Commit to DB
        mysql.connection.commit()

        #Close Connection
        cur.close()

        flash('Video succesfully updated', 'success')
        return redirect(url_for('cat'))

    return render_template("edit_video.html", form = form, cat = cat )

if __name__ == '__main__':
    app.debug = True
    app.run()
