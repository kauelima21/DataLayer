import os

# os.environ["DATA_LAYER_DRIVER"] = "mariadb"
# os.environ["DATA_LAYER_HOST"] = "localhost"
# os.environ["DATA_LAYER_PORT"] = "3306"
# os.environ["DATA_LAYER_DATABASE"] = "local_db"
# os.environ["DATA_LAYER_USER"] = "local_user"
# os.environ["DATA_LAYER_PASSWORD"] = "local_password"

os.environ["DATA_LAYER_DRIVER"] = "postgres"
os.environ["DATA_LAYER_HOST"] = "localhost"
os.environ["DATA_LAYER_PORT"] = "5432"
os.environ["DATA_LAYER_DATABASE"] = "local_db"
os.environ["DATA_LAYER_USER"] = "local_user"
os.environ["DATA_LAYER_PASSWORD"] = "local_password"
