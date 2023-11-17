import os
from app.models import model_names, download_model


def run_checks():
    try:
        if not check_models_exist():
            return False
        return True
    except Exception as exc:
        print("Error in run_checks: {}".format(str(exc)))
        return False


def check_models_exist():
    try:
        for key, value in model_names.items():
            if os.path.exists(os.path.join(os.getcwd(), "models", value)):
                print("Model {} exists".format(key))
            else:
                print("Model {} does not exist".format(key))
                download_model(key)
        return True
    except Exception as exc:
        print("Error in check_models_exist: {}".format(str(exc)))
        return False
