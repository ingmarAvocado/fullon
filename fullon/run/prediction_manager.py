"""
used for prediction plugin?
"""
import sys
import time
import importlib.util
from setproctitle import setproctitle  # pylint: disable=no-name-in-module
from libs import settings, cache, database_prediction as database, log

logger = log.fullon_logger(__name__)


class PredictionManager:
    """ description """

    def __init__(self):
        """ description """
        self.started = True

    def start(self, predictor_name):
        """ description """
        setproctitle(f"Fullon Predictor {predictor_name}")
        return self.run_predictor_loop(predictor_name=predictor_name)

    def run_predictor_loop(self, predictor_name):
        """ description """
        while True:
            print(f"looping for predictor ({predictor_name})")
            time.sleep(2)

    def load_module(self, predictor_name):
        """ description """
        try:
            module = importlib.import_module(
                'predictors.' + predictor_name + '.predictor',
                package='predictor')
            predictor = module.predictor(name=predictor_name)
            return predictor
        except (ModuleNotFoundError) as error:
            logger.warning(error)
            sys.exit()
            #return False

    def predict(self, predictor_name):
        """ description """
        predictor = self.load_module(predictor_name=predictor_name)
        if not predictor:
            return False
        res = predictor.validate()
        res = predictor.predict()
        del predictor
        return res

    def create_data_table(self, predictor_name):
        """ description """
        predictor = self.load_module(predictor_name=predictor_name)
        if not predictor:
            return False
        res = predictor.set_table()
        del predictor
        return res

    def prep_base_data(self, predictor_name):
        """ description """
        predictor = self.load_module(predictor_name=predictor_name)
        if not predictor:
            return False
        res = predictor.prep_base_data()
        del predictor
        return res

    def run_loop(self):
        """ description """
        dbase = database.Database_predictors()
        #predictor = self.db.get_predictors()
        cache_manager = cache.Cache()
        predictors = [{"name": "hola mundo"}]
        for predictor in predictors:
            self.start(predictor_name=predictor.name)
            time.sleep(0.5)
        # p.join()
        del cache_manager
