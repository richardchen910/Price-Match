#Price Match app
#Richard Chen

from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL 
from wtforms import Form, StringField, DecimalField, TextAreaField, validators
from passlib.hash import sha256_crypt
import MySQLdb
from functools import wraps


app = Flask(__name__)


# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '#7Basketball'
app.config['MYSQL_DB'] = 'price_match'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init MySQL
mysql = MySQL(app)


# Home
@app.route('/')
def index():
	return render_template('index.html')


# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		first_name = request.form['first_name']
		last_name = request.form['last_name']
		email = request.form['email']
		password = request.form['password']
		confirm = request.form['confirm']

		if password != confirm:
			flash('Passwords do not match', 'danger')
			return redirect(url_for('register'))
		
		# Encrypt password
		password = sha256_crypt.encrypt(str(password))

		# Create cursor
		cur = mysql.connection.cursor()

		try:
			# Add user to database
			cur.execute("INSERT INTO users(first_name, last_name, email, password) VALUES(%s, %s, %s, %s)", (first_name, last_name, email, password))
		except MySQLdb.IntegrityError:
			mysql.connection.rollback()						# Undoes all data changes
			flash('Email already exists', 'danger')
			return redirect(url_for('register'))
		else:
			# Commit to database
			mysql.connection.commit()
		finally:
			# Close connection
			cur.close()

		flash('Account created successfully', 'success')
		return redirect(url_for('login'))

	return render_template('register.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		email = request.form['email']
		password_candidate = request.form['password']

		#Create cursor
		cur = mysql.connection.cursor()

		# Check if user exists in database
		result = cur.execute("SELECT * FROM users WHERE email = %s", [email])
		if result > 0:
			# Get stored hash
			data = cur.fetchone()
			first_name = data['first_name']
			password = data['password']
			
			# Compare passwords to see if they match
			if sha256_crypt.verify(password_candidate, password):
				# Login sucessful
				session['logged_in'] = True
				session['email'] = email
				session['first_name'] = first_name
				session['id'] = data['id']

				cur.close()

				# Retrieve last url
				dest_url = request.args.get('next')

				#Fallback url if no 'next' parameter, otherwise redirect to last url
				if dest_url == None:
					return redirect(url_for('index'))
				return redirect(dest_url)
			else:
				# Password does not match username
				cur.close()
				error = 'The password you entered is incorrect'
				return render_template('login.html', error=error)
		else:
			# Username does not exist in database
			cur.close()
			error = 'The username you entered does not exist'
			return render_template('login.html', error=error) 

	return render_template('login.html')


# Check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:		# 'session' is a dict
			return f(*args, **kwargs)
		else:
			#Get url of last page, pass it through 'next' parameter
			login_url = url_for('login') + '?next=' + request.url

			return redirect(login_url)
	return wrap


#Logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('Logged out successfully', 'success')
	return redirect(url_for('login'))


# List of items
@app.route('/items')
@is_logged_in
def items():
	# Create a cursor
	cur = mysql.connection.cursor()

	# Get list of items
	result = cur.execute("SELECT * FROM items WHERE %s = user_id", [session['id']])
	if result > 0:
		items = cur.fetchall()
		return render_template('items.html', items=items)
	else:
		msg = 'No items found'
		return render_template('items.html', msg=msg)

	# Close connection
	cur.close()

	return render_template('items.html')


class ItemForm(Form):
	item = StringField('', [validators.DataRequired()], render_kw={"placeholder": "Item"})
	price = DecimalField('', [validators.DataRequired()], render_kw={"placeholder": "0.00"})
	store = StringField('', [validators.DataRequired()], render_kw={"placeholder": "Store"})
	description = TextAreaField('', [validators.Length(max=50)], render_kw={"placeholder": "Add description (optional)"})


# Single item
@app.route('/items/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_item(id):
	# Create a cursor
	cur = mysql.connection.cursor()

	# Get item
	result = cur.execute("SELECT * FROM items WHERE id = %s", [id])
	item = cur.fetchone()

	# Get form
	form = ItemForm(request.form)

	# Set form input values
	form.item.data = item['item']
	form.price.data = item['price']
	form.store.data = item['store']
	if form.description.data == "-":
		form.description.data = ""
	else:
		form.description.data = item['description']


	if request.method == 'POST':
		item = request.form['item']
		price = float(request.form['price'])
		store = request.form['store']
		description = request.form['description']
		if description == "":
			description = "-"

		# Create a cursor
		cur = mysql.connection.cursor()

		# Get item
		cur.execute("UPDATE items set item=%s, price=%s, store=%s, description=%s WHERE id = %s", (item, price, store, description, id))

		# Commit to DB
		mysql.connection.commit()

		# Close connection
		cur.close()

		flash('Item updated successfully', 'success')

		return redirect(url_for('items'))

	return render_template('edit_item.html', form=form)


@app.route('/delete_item/<string:id>', methods=['POST'])
@is_logged_in
def delete_item(id):
	# Create cursor
	cur = mysql.connection.cursor()

	# Delete item
	cur.execute("DELETE FROM items WHERE id = %s", [id])

	# Commit to DB
	mysql.connection.commit()

	# Close connection
	cur.close()

	flash('Item deleted successfully', 'success')

	return redirect(url_for('items'))


# Add item
@app.route('/add_item', methods=['GET', 'POST'])
@is_logged_in
def add_item():
	if request.method == 'POST':
		item = request.form['item']
		price = float(request.form['price'])
		store = request.form['store']
		description = request.form['description']
		if description == "":
			description = "-"

		# Create a cursor
		cur = mysql.connection.cursor()
		
		# Add item to database
		cur.execute("INSERT INTO items(item, price, store, description, user_id) VALUES(%s, %s, %s, %s, %s)", (item, price, store, description, session['id']))

		# Commit to database
		mysql.connection.commit()

		#Close connection
		cur.close()

		flash('Item added successfully', 'success')

		return redirect(url_for('items'))

	return render_template('add_item.html')




@app.route('/cart')
@is_logged_in
def cart():
	return render_template('cart.html')


if __name__ == "__main__":
	app.secret_key='aef8qdbn'
	app.run(debug=True)