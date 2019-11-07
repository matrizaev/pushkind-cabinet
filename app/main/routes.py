from app import db
from flask import redirect, flash, render_template, request, jsonify, current_app, url_for
from flask_login import current_user, login_required
from app.models import User, Order, Product, Category, OrderProducts
from app.main.forms import PlaceOrderForm, UpdateProductPriceForm, UploadProductsForm, RemoveOrderForm
from collections import Counter
from sqlalchemy import or_
import pandas as pd
from app.main import bp

class OrderException(Exception):
	pass

class UpdatePriceException(Exception):
	pass

@bp.route('/')
@bp.route('/index/')
@login_required
def ShowIndex():
	orders = current_user.orders[:2]
	return render_template('index.html', menuItem = 0, orders = orders, removeOrderForm = RemoveOrderForm())

@bp.route('/products/', defaults = {'cat_id':0})
@bp.route('/products/<int:cat_id>')
@login_required
def ShowProducts(cat_id):
	form = UpdateProductPriceForm()
	keyword = request.args.get('search')
	if cat_id == 0 or keyword:
		cat_id = current_user.root_category
	category = Category.query.filter(Category.id == cat_id, Category.store_id == current_user.id).first_or_404()
	if not keyword:
		products = category.products
	else:
		products = Product.query.filter(Product.store_id == current_user.id, or_(Product.title.ilike(f'%{keyword}%'), Product.description.ilike(f'%{keyword}%'), Product.path.ilike(f'%{keyword}%'))).all()
	return render_template('products.html', menuItem = 2, products = products, category = category, form = form)
	
@bp.route('/settings/', methods=['GET', 'POST'])
@login_required
def ShowSettings():
	form = UploadProductsForm()
	if form.validate_on_submit():
		try:
			f = form.products.data
			df = pd.read_excel(form.products.data)
			df['store_id'] = current_user.id
			df['cat_id'] = current_user.root_category
			df['price'] = df['price'].astype('float64')
			Product.query.filter(Product.store_id == current_user.id).delete()
			db.session.commit()
			Category.query.filter(Category.store_id == current_user.id, Category.id != current_user.root_category).delete()
			db.session.commit()
			df.to_sql(name = 'product', con = db.engine, if_exists = 'append', index = False)
			current_user.LaunchRQjob()
			flash('Файл успешно загружен.')
		except:
			flash('Не удалось обработать файл.')
	return render_template('settings.html', menuItem = 3, form = form)
	
@bp.route('/upload_progress/', methods=['GET'])
@login_required
def GetUploadProgress():
	job_is_running = True if current_user.GetRQjob()is not None else False
	return jsonify({'status':job_is_running, 'flash': ['Прогресс обработки товаров: {0:.2f}%'.format(current_user.GetRQprogress())]})
	
@bp.route('/orders/')
@login_required
def ShowOrders():
	placeOrderForm = PlaceOrderForm()
	placeOrderForm.vendor_id.data = current_user.vendor_id
	orders = current_user.orders
	return render_template('orders.html', menuItem = 1, orders = orders, placeOrderForm = placeOrderForm, removeOrderForm = RemoveOrderForm())

@bp.route('/place_orders/', methods=['POST'])
@login_required
def PlaceOrder():
	flashMessages = list()
	status = False
	orderMarkup = ''
	form = PlaceOrderForm()
	if form.validate_on_submit():
		try:
			products_sku = [x.strip() for x in form.products.data.split(',') if x.strip() != '']
			products_sku = Counter(products_sku)
			vendor = User.query.filter(User.vendor_id == form.vendor_id.data).first()
			if vendor is None:
				flashMessages.append('Несуществующий поставщик.')
				raise OrderException()
			order = Order(store_id = current_user.id,
						address = form.address.data,
						city = form.city.data,
						email = form.email.data,
						country = form.country.data,
						phone = form.phone.data,
						province = form.province.data,
						comment = form.comment.data,
						postal_code = form.postal_code.data,
						name = form.name.data)
			orderProducts = list()
			for sku in products_sku:
				p = Product.query.filter(Product.sku == sku, Product.store_id == current_user.id).first()
				if p is None:
					flashMessages.append('Некорректные артикулы.')
					raise OrderException()
				op = OrderProducts (count=products_sku[sku], price=p.price, sku=sku, title=p.title, picture=p.picture, description=p.description)
				db.session.add(op)
				orderProducts.append(op)
			order.products = orderProducts
			db.session.add(order)
			db.session.commit()
			flashMessages.append('Заказ успешно размещён.')
			status = True
			orderMarkup = render_template('_order.html', order = order, removeOrderForm = RemoveOrderForm())
		except:
			flashMessages.append('Не удалось разместить заказ.')
	return jsonify({'status':status, 'flash':flashMessages, 'orderMarkup':orderMarkup})

@bp.route('/remove_order/', methods=['POST'])	
def RemoveOrder():
	form = RemoveOrderForm()
	if form.validate_on_submit():
		try:
			order = Order.query.filter(Order.store_id == current_user.id, Order.id == form.id.data).first()
			if order:
				db.session.delete(order)
				db.session.commit()
				flash('Заказ успешно удалён.')
			else:
				flash('Заказ не найден.')
		except:
			flash('Не удалось удалить заказ.')
	return redirect(url_for('main.ShowOrders'))

@bp.route('/update_price/', methods=['POST'])
@login_required
def UpdateProductPrice():
	form = UpdateProductPriceForm()
	flashMessages = list()
	status = False
	if form.validate_on_submit():
		try:
			product = Product.query.filter(Product.id == form.id.data, Product.store_id == current_user.id).first()
			if product is None:
				flashMessages.append('Товар с таким артикулом не существует.')
				raise UpdatePriceException()
			product.price = form.price.data
			current_user.want_to_publish = ''
			db.session.commit()
			flashMessages.append('Цена успешно изменена.')
			status = True
		except:
			flashMessages.append('Не удалось изменить цену.')
	return jsonify({'status':status, 'flash':flashMessages})
	
@bp.route('/publish_products/', methods=['POST'])
@login_required
def PusblishProducts():
	current_user.want_to_publish = 'publish'
	db.session.commit()
	return jsonify({'status':True, 'flash':['Запрос на публикацию отправлен.']})
