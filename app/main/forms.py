from flask_wtf import FlaskForm
from wtforms import SubmitField, IntegerField, StringField, FloatField
from wtforms.validators import ValidationError, DataRequired, Email
from wtforms.fields.html5 import EmailField
from flask_wtf.file import FileField, FileRequired, FileAllowed

class PlaceOrderForm(FlaskForm):
	address = StringField('Улица, дом, квартира', validators = [DataRequired()])
	email = EmailField('Электронная почта', validators = [DataRequired(), Email()])
	country = StringField('Страна', validators = [DataRequired()])
	city = StringField('Город', validators = [DataRequired()])
	phone = StringField('Телефон', validators = [DataRequired()])
	comment = StringField('Комментарий', validators = [DataRequired()])
	province = StringField('Область', validators = [DataRequired()])
	postal_code = StringField('Почтовый индекс', validators = [DataRequired()])
	name = StringField('ФИО', validators = [DataRequired()])
	products = StringField('Артикулы товаров', validators = [DataRequired()])
	vendor_id = StringField('Идентификатор поставщика', validators = [DataRequired()])
	submit = SubmitField('Заказать')
	
class RemoveOrderForm(FlaskForm):
	id = IntegerField('Идентификатор', validators = [DataRequired()])
	submit = SubmitField('Удалить')
	
class UpdateProductPriceForm(FlaskForm):
	id = IntegerField('Идентификатор', validators = [DataRequired()])
	price = FloatField('Цена: ', validators = [DataRequired()])
	submit = SubmitField('Изменить')
	
class UploadProductsForm(FlaskForm):
	products = FileField (label = 'Продукты', validators=[FileRequired(), FileAllowed(['xlsx'], 'Разрешены только XLSX.')])
	submit = SubmitField('Загрузить')