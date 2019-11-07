from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from sqlalchemy import or_
from flask import current_app
from flask import url_for

import redis
import rq

@login.user_loader
def load_user(id):
	return User.query.get(int(id))
	
class PaginatedAPIMixin(object):
    @staticmethod
    def ToCollectionDict(query, page, per_page, endpoint, **kwargs):
        resources = query.paginate(page, per_page, False)
        data = {
            'items': [item.ToDict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data
	
class User(PaginatedAPIMixin, UserMixin, db.Model):
	id  = db.Column(db.Integer, primary_key = True)
	email    = db.Column(db.String(120), index = True, unique = True, nullable=False)
	vendor_id = db.Column(db.String(120), unique = True, nullable=False)
	password = db.Column(db.String(128), nullable=False)
	products = db.relationship('Product', backref = 'store', lazy='dynamic')
	orders = db.relationship('Order', lazy='dynamic', order_by='Order.timestamp.desc()')
	root_category = db.Column(db.Integer, nullable=False, default = 0, server_default = '0')
	task_id = db.Column(db.String(36), default = '', server_default = '0')
	section = db.Column(db.String(128), nullable=True)
	owner = db.Column(db.String(128), nullable=True)
	want_to_publish = db.Column(db.String(128), nullable=False, default = '', server_default = '')
	
	def __repr__ (self):
		return '<User {}>'.format(self.email)
	
	def SetPassword(self, password):
		self.password = generate_password_hash(password)
		db.session.commit()
		
	def CheckPassword(self, password):
		return check_password_hash(self.password, password)
		
	def GetAvatar(self, size):
		digest = md5(self.email.lower().encode('utf-8')).hexdigest()
		return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)
		
	def CreateRootCategory(self):
		cat = Category (name = 'Товары', store_id = self.id)
		db.session.add(cat)
		db.session.commit()
		self.root_category = cat.id
		db.session.commit()
		
	def GetRQjob(self):
		try:
			rq_job = rq.job.Job.fetch(self.task_id, connection=current_app.redis)
		except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
			return None
		return rq_job
		
	def GetRQprogress(self):
		job = self.GetRQjob()
		return job.meta.get('progress', 0) if job is not None else 100
		
	def LaunchRQjob(self):
		rq_job = current_app.task_queue.enqueue('app.tasks.CreateUserCategoriesTask', self.id)
		self.task_id = rq_job.get_id()
		db.session.commit()
	
	def ToDict(self):
		data = {
			'id': self.id,
			'vendor_id': self.vendor_id,
			'email': self.email,
			'products_count': self.products.count(),
			'orders_count': self.orders.count(),
			'section': self.section,
			'owner':self.owner,
			'want_to_publish': self.want_to_publish,
			'_links': {
				'self': url_for('api.GetStore', id=self.id),
				'products': url_for('api.GetStoreProducts', id=self.id),
				'orders': url_for('api.GetStoreOrders', id=self.id)
			}
		}
		return data
		
	def FromDict(self, data):
		for field in ['section', 'owner', 'want_to_publish']:
			if field in data:
				setattr(self, field, data[field])
		db.session.commit()
		
		
class OrderProducts(db.Model):
	__tablename_ = 'order_products'
	id = db.Column(db.Integer, primary_key=True)
	order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
	count = db.Column(db.Integer, nullable=False)
	price = db.Column(db.Integer, nullable=False, default = 0, server_default = '0')
	sku = db.Column(db.String(128), nullable=False, default = '', server_default = '')
	title = db.Column(db.String(128), nullable=False, default = '', server_default = '')
	picture = db.Column(db.String(1024))
	description = db.Column(db.Text())
	
	def ToDict(self):
		data = {
			'id': self.id,
			'count': self.count,
			'price': self.price,
			'sku': self.sku,
			'title': self.title,
			'picture':self.picture,
			'description':self.description
		}
		return data

class Product(PaginatedAPIMixin, db.Model):
	id = db.Column(db.Integer, primary_key = True)
	store_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	sku = db.Column(db.String(128), nullable=False)
	title = db.Column(db.String(128), nullable=False)
	path = db.Column(db.Text(), nullable=False)
	cat_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False, default = 0, server_default = '0')
	price = db.Column(db.Float(), nullable=False)
	description = db.Column(db.Text())
	picture = db.Column(db.String(1024))
	
	def ToDict(self):
		data = {
			'id': self.id,
			'sku': self.sku,
			'title': self.title,
			'path': self.path,
			'price': self.price,
			'description': self.description,
			'picture': self.picture
		}
		return data
	
	def CreateCategories(self):
		path_list = self.path.split('/')
		
		for idx, p in enumerate(path_list):
			if p.strip() == '':
				path_list.pop(idx)
		
		root = Category.query.filter(Category.name == path_list[0], Category.store_id == self.store_id).first()
		if not root:
			root = Category(name = path_list[0], parent_id = self.store.root_category, store_id = self.store_id)
			db.session.add(root)
			db.session.commit()
		for item in path_list[1:]:
			cat = Category.query.filter(Category.name == item, Category.parent_id == root.id).first()
			if not cat:
				cat = Category(name = item, parent_id = root.id, store_id = self.store_id)
				db.session.add(cat)
				db.session.commit()
			root = cat
		self.cat_id = root.id
		db.session.commit()
			
	
class Category(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	name = db.Column(db.Text(), nullable=False)
	store_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False, default = 0, server_default = '0')
	products = db.relationship('Product', backref = 'category', lazy=True)
	children = db.relationship('Category', lazy=True)
	story = db.relationship ('User', lazy=True)
	
	def GetFullPath(self):
		path = []
		cat = self
		while cat.id != self.story.root_category:
			path.insert(0, {'name':cat.name, 'id':cat.id})
			cat = Category.query.get(cat.parent_id)
		return path
			

class Order(PaginatedAPIMixin, db.Model):
	id = db.Column(db.Integer, primary_key = True)
	store_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
	address = db.Column(db.String(1024), nullable=False)
	city = db.Column(db.String(128), nullable=False)
	email = db.Column(db.String(128), nullable=False)
	country = db.Column(db.String(), nullable=False)
	phone = db.Column(db.String(128), nullable=False)
	comment = db.Column(db.Text(), nullable=False)
	province = db.Column(db.String(128), nullable=False)
	postal_code = db.Column(db.String(128), nullable=False)
	name = db.Column(db.String(128), nullable=False)
	timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
	products = db.relationship('OrderProducts')
	
	def GetOrderPrice(self):
		summary = 0
		for op in self.products:
			summary += op.count * op.price
		return summary
		
	def ToDict(self):
		data = {
			'id': self.id,
			'store_id': self.store_id,
			'address': self.address,
			'city': self.city,
			'country': self.country,
			'phone': self.phone,
			'comment':self.comment,
			'province':self.province,
			'postal_code':self.postal_code,
			'name':self.name,
			'timestamp':self.timestamp,
			'products':[item.ToDict() for item in self.products],
			'_links': {
				'self': url_for('api.GetOrder', id=self.id),
			}		
		}
		return data