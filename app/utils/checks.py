import os
from app.models import model_names, download_model


def check_models_exist(name: str):
    try:
        if model_names[name] in os.listdir(os.path.join(os.getcwd(), "models")):
            print("Model {} exists".format(name))
        else:
            print("Model {} does not exist".format(name))
            download_model(key)
        return True
    except Exception as exc:
        print("Error in check_models_exist: {}".format(str(exc)))
        return False


def chack_file_exist(file_path):
    try:
        if os.path.exists(file_path):
            return True
        return False
    except Exception as exc:
        print("Error in chack_file_exist: {}".format(str(exc)))
        return False
