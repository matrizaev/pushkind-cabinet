from app.models import User
from rq import get_current_job
from app import create_app

app = create_app()
app.app_context().push()

def CreateUserCategoriesTask(uid):
	job = get_current_job()
	user = User.query.get(uid)
	if user:
		products_len = user.products.count()
		for idx, product in enumerate(user.products):
			job.meta['progress'] = 100.0 * idx / products_len
			job.save_meta()
			product.CreateCategories()
	job.meta['progress'] = 100.0
	job.save_meta()